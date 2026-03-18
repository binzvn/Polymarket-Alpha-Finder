"""
Polymarket Alpha Finder - FastAPI Application Server
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api_client import PolymarketClient
from url_parser import resolve_market
from analyzer import analyze_wallet
from classifier import classify_wallet
from scorer import score_wallet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Polymarket Alpha Finder")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory store for last analysis results
_last_results: list[dict] = []


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/analyze")
async def analyze(request: Request):
    """
    Run the full pipeline: URL → trades → wallets → metrics → classify → score.
    Returns JSON array of wallet results.
    """
    global _last_results

    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        return JSONResponse({"error": "Missing 'url' field"}, status_code=400)

    client = PolymarketClient()
    try:
        # ── Stage 1: Parse URL & gather market data ──────────────
        logger.info("Resolving market from URL: %s", url)
        market_data = await resolve_market(client, url)
        condition_ids = market_data["condition_ids"]

        if not condition_ids:
            return JSONResponse({"error": "No markets found for this event"}, status_code=404)

        # ── Stage 1b: Fetch all trades and extract unique wallets ─
        logger.info("Fetching trades for %d condition(s)...", len(condition_ids))
        all_trades: list[dict] = []
        trade_tasks = [client.get_trades_by_condition(cid) for cid in condition_ids]
        trade_results = await asyncio.gather(*trade_tasks)
        for tr in trade_results:
            all_trades.extend(tr)

        # Extract unique wallet addresses
        wallets: set[str] = set()
        for trade in all_trades:
            addr = trade.get("proxyWallet") or trade.get("maker") or trade.get("taker")
            if addr:
                wallets.add(addr)

        wallets_list = list(wallets)
        logger.info("Found %d unique wallets from %d trades", len(wallets_list), len(all_trades))

        if not wallets_list:
            return JSONResponse({"error": "No wallets found in this market"}, status_code=404)

        # ── Stage 2: Batch-fetch wallet histories ────────────────
        logger.info("Fetching history for %d wallets...", len(wallets_list))
        wallet_data = await client.batch_fetch_wallet_data(wallets_list)

        # ── Stage 3 & 4: Analyze, classify, score ────────────────
        results = []
        for addr in wallets_list:
            wd = wallet_data.get(addr, {})
            metrics = analyze_wallet(addr, wd)
            wtype = classify_wallet(metrics)
            scoring = score_wallet(metrics, wtype)

            results.append({
                **metrics,
                "type": wtype,
                "score": scoring["score"],
                "passes_filter": scoring["passes_filter"],
            })

        # Sort by score descending
        results.sort(key=lambda r: r["score"], reverse=True)

        _last_results = results

        # Build summary
        summary = {
            "total_analyzed": len(results),
            "systematic_count": sum(1 for r in results if r["type"] == "systematic"),
            "whale_count": sum(1 for r in results if r["type"] == "whale_gambler"),
            "scalper_count": sum(1 for r in results if r["type"] == "scalper"),
            "event_title": market_data["event"].get("title", "Unknown"),
        }

        return JSONResponse({"summary": summary, "wallets": results})

    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        logger.exception("Analysis failed")
        return JSONResponse({"error": f"Analysis failed: {exc}"}, status_code=500)
    finally:
        await client.close()


@app.get("/api/export-csv")
async def export_csv():
    """Export last analysis results as CSV download."""
    if not _last_results:
        return JSONResponse({"error": "No results to export. Run an analysis first."}, status_code=404)

    output = io.StringIO()
    fieldnames = [
        "address", "name", "type", "score", "passes_filter",
        "total_pnl", "pnl_pct", "win_rate", "total_positions",
        "num_markets", "avg_bet_size", "cv", "concentration",
        "diversification", "trade_frequency", "num_trades",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in _last_results:
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=polymarket_alpha.csv"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
