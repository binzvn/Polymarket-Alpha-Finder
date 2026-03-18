"""
Polymarket Alpha Finder - Async API Client
Uses httpx + asyncio.Semaphore to batch-fetch hundreds of wallets.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import (
    GAMMA_API_BASE,
    DATA_API_BASE,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_TIMEOUT,
    TRADES_PAGE_SIZE,
    ACTIVITY_PAGE_SIZE,
)

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Thin async wrapper around Gamma + Data APIs."""

    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(REQUEST_TIMEOUT),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=MAX_CONCURRENT_REQUESTS + 5,
                    max_keepalive_connections=MAX_CONCURRENT_REQUESTS,
                ),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ──────────────────────────────────────────────────────────────
    # Low-level GET with semaphore
    # ──────────────────────────────────────────────────────────────
    async def _get(self, url: str, params: dict | None = None) -> Any:
        client = await self._ensure_client()
        async with self._sem:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                logger.warning("HTTP %s for %s", exc.response.status_code, url)
                return None
            except Exception as exc:
                logger.warning("Request failed for %s: %s", url, exc)
                return None

    # ──────────────────────────────────────────────────────────────
    # Gamma API
    # ──────────────────────────────────────────────────────────────
    async def get_event_by_slug(self, slug: str) -> dict | None:
        """Fetch event (with nested markets) by URL slug."""
        data = await self._get(
            f"{GAMMA_API_BASE}/events", params={"slug": slug}
        )
        # Gamma API returns a list
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return None

    async def get_event_by_id(self, event_id: str) -> dict | None:
        data = await self._get(f"{GAMMA_API_BASE}/events/{event_id}")
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return None

    async def get_market_by_slug(self, slug: str) -> dict | None:
        data = await self._get(
            f"{GAMMA_API_BASE}/markets", params={"slug": slug}
        )
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return None

    async def get_markets_for_event(self, event_id: str) -> list[dict]:
        """Return all markets belonging to an event."""
        data = await self._get(
            f"{GAMMA_API_BASE}/markets", params={"event_id": event_id}
        )
        if isinstance(data, list):
            return data
        return []

    async def get_public_profile(self, address: str) -> dict | None:
        return await self._get(
            f"{GAMMA_API_BASE}/public-profile", params={"address": address}
        )

    # ──────────────────────────────────────────────────────────────
    # Data API - trades (paginated)
    # ──────────────────────────────────────────────────────────────
    async def get_trades_by_condition(
        self, condition_id: str, *, max_pages: int = 100
    ) -> list[dict]:
        """Fetch ALL trades for a conditionId, autopaginating."""
        all_trades: list[dict] = []
        offset = 0
        for _ in range(max_pages):
            data = await self._get(
                f"{DATA_API_BASE}/trades",
                params={
                    "conditionId": condition_id,
                    "limit": TRADES_PAGE_SIZE,
                    "offset": offset,
                },
            )
            if not data:
                break
            if isinstance(data, list):
                all_trades.extend(data)
                if len(data) < TRADES_PAGE_SIZE:
                    break
                offset += TRADES_PAGE_SIZE
            else:
                break
        return all_trades

    # ──────────────────────────────────────────────────────────────
    # Data API - per-wallet endpoints
    # ──────────────────────────────────────────────────────────────
    async def get_user_activity(
        self, address: str, *, max_pages: int = 50
    ) -> list[dict]:
        all_items: list[dict] = []
        offset = 0
        for _ in range(max_pages):
            data = await self._get(
                f"{DATA_API_BASE}/activity",
                params={
                    "user": address,
                    "limit": ACTIVITY_PAGE_SIZE,
                    "offset": offset,
                },
            )
            if not data:
                break
            if isinstance(data, list):
                all_items.extend(data)
                if len(data) < ACTIVITY_PAGE_SIZE:
                    break
                offset += ACTIVITY_PAGE_SIZE
            else:
                break
        return all_items

    async def get_user_positions(self, address: str) -> list[dict]:
        data = await self._get(
            f"{DATA_API_BASE}/positions", params={"user": address}
        )
        return data if isinstance(data, list) else []

    async def get_user_closed_positions(self, address: str) -> list[dict]:
        data = await self._get(
            f"{DATA_API_BASE}/closed-positions", params={"user": address}
        )
        return data if isinstance(data, list) else []

    # ──────────────────────────────────────────────────────────────
    # Batch helpers
    # ──────────────────────────────────────────────────────────────
    async def batch_fetch_wallet_data(
        self,
        addresses: list[str],
        *,
        progress_cb=None,
    ) -> dict[str, dict]:
        """
        For each address, fetch activity + positions + closed positions
        + profile concurrently.  Returns {address: {activity, positions,
        closed_positions, profile}}.
        """
        results: dict[str, dict] = {}
        total = len(addresses)

        async def _fetch_one(idx: int, addr: str) -> None:
            activity, positions, closed, profile = await asyncio.gather(
                self.get_user_activity(addr),
                self.get_user_positions(addr),
                self.get_user_closed_positions(addr),
                self.get_public_profile(addr),
            )
            results[addr] = {
                "activity": activity,
                "positions": positions,
                "closed_positions": closed,
                "profile": profile,
            }
            if progress_cb:
                await progress_cb(idx + 1, total, addr)

        tasks = [_fetch_one(i, a) for i, a in enumerate(addresses)]
        await asyncio.gather(*tasks)
        return results
