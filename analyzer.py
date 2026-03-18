"""
Polymarket Alpha Finder - Metrics Analyzer
Computes per-wallet trading metrics from raw API data.
"""

from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def analyze_wallet(address: str, wallet_data: dict) -> dict:
    """
    Compute metrics for a single wallet.

    wallet_data = {
      "activity": [...],
      "positions": [...],
      "closed_positions": [...],
      "profile": {...} | None,
    }

    Returns a dict of computed metrics.
    """
    activity = wallet_data.get("activity") or []
    positions = wallet_data.get("positions") or []
    closed_positions = wallet_data.get("closed_positions") or []
    profile = wallet_data.get("profile") or {}

    # ── Display name ─────────────────────────────────────────────
    name = (
        profile.get("name")
        or profile.get("username")
        or f"{address[:6]}...{address[-4:]}"
    )
    profile_url = profile.get("profileUrl") or profile.get("url") or ""

    # ── Aggregate all positions (open + closed) ──────────────────
    all_positions = list(positions) + list(closed_positions)
    total_positions = len(all_positions)

    # ── Unique markets / events ──────────────────────────────────
    market_slugs: set[str] = set()
    event_slugs: set[str] = set()
    categories: set[str] = set()
    outcome_exposure: dict[str, float] = defaultdict(float)
    total_invested: float = 0.0
    total_pnl: float = 0.0

    for pos in all_positions:
        slug = pos.get("marketSlug") or pos.get("market_slug") or ""
        if slug:
            market_slugs.add(slug)

        ev_slug = pos.get("eventSlug") or pos.get("event_slug") or ""
        if ev_slug:
            event_slugs.add(ev_slug)

        # Category / tag
        tags = pos.get("tags") or pos.get("eventTags") or pos.get("tag") or ""
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict):
                    categories.add(t.get("label", "Other"))
                elif isinstance(t, str) and t:
                    categories.add(t)
        elif isinstance(tags, str) and tags:
            categories.add(tags)

        # Outcome exposure
        outcome_key = f"{slug}_{pos.get('outcome', pos.get('title', ''))}"
        size = _safe_float(pos.get("currentValue") or pos.get("initialValue") or pos.get("size"))
        outcome_exposure[outcome_key] += abs(size)
        total_invested += abs(_safe_float(pos.get("initialValue") or pos.get("size")))

        # PNL
        pnl = _safe_float(pos.get("pnl") or pos.get("realized_pnl") or pos.get("realizedPnl"))
        total_pnl += pnl

    # ── Win Rate (from closed positions) ─────────────────────────
    resolved_markets: dict[str, float] = {}
    for cp in closed_positions:
        slug = cp.get("marketSlug") or cp.get("market_slug") or cp.get("conditionId") or str(id(cp))
        pnl = _safe_float(cp.get("pnl") or cp.get("realized_pnl") or cp.get("realizedPnl"))
        resolved_markets[slug] = resolved_markets.get(slug, 0.0) + pnl

    total_resolved = len(resolved_markets)
    wins = sum(1 for p in resolved_markets.values() if p > 0)
    win_rate = wins / total_resolved if total_resolved > 0 else 0.0

    # ── Average Bet Size ─────────────────────────────────────────
    avg_bet_size = total_invested / total_positions if total_positions > 0 else 0.0

    # ── Diversification ──────────────────────────────────────────
    if not categories:
        categories = {"General"}
    diversification = len(categories)

    # ── Concentration ────────────────────────────────────────────
    max_exposure = max(outcome_exposure.values()) if outcome_exposure else 0.0
    total_exposure = sum(outcome_exposure.values()) if outcome_exposure else 1.0
    concentration = max_exposure / total_exposure if total_exposure > 0 else 1.0

    # ── Trade frequency (from activity) ──────────────────────────
    num_trades = len(activity)
    timestamps = []
    for a in activity:
        ts = a.get("timestamp") or a.get("createdAt") or a.get("created_at")
        if ts:
            timestamps.append(ts)

    if len(timestamps) >= 2:
        try:
            sorted_ts = sorted(timestamps)
            from datetime import datetime, timezone

            def _parse_ts(t):
                if isinstance(t, (int, float)):
                    return datetime.fromtimestamp(t, tz=timezone.utc)
                if isinstance(t, str):
                    # Try ISO format
                    t = t.replace("Z", "+00:00")
                    return datetime.fromisoformat(t)
                return None

            first = _parse_ts(sorted_ts[0])
            last = _parse_ts(sorted_ts[-1])
            if first and last:
                span_days = max((last - first).total_seconds() / 86400, 1)
                trade_frequency = num_trades / span_days
            else:
                trade_frequency = 0.0
        except Exception:
            trade_frequency = 0.0
    else:
        trade_frequency = 0.0

    # ── PNL % ────────────────────────────────────────────────────
    pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    # ── Coefficient of Variation (CV) of bet sizes ───────────────
    bet_sizes = [
        abs(_safe_float(p.get("initialValue") or p.get("size")))
        for p in all_positions
        if _safe_float(p.get("initialValue") or p.get("size")) > 0
    ]
    if len(bet_sizes) >= 2:
        import statistics
        mean_bs = statistics.mean(bet_sizes)
        std_bs = statistics.stdev(bet_sizes)
        cv = std_bs / mean_bs if mean_bs > 0 else 0.0
    else:
        cv = 0.0

    num_markets = len(market_slugs) or len(event_slugs) or 1

    return {
        "address": address,
        "name": name,
        "profile_url": profile_url,
        "win_rate": round(win_rate, 4),
        "avg_bet_size": round(avg_bet_size, 2),
        "diversification": diversification,
        "concentration": round(concentration, 4),
        "trade_frequency": round(trade_frequency, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "total_positions": total_positions,
        "num_markets": num_markets,
        "num_trades": num_trades,
        "cv": round(cv, 2),
        "categories": list(categories),
    }
