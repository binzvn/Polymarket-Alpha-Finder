"""
Polymarket Alpha Finder - URL Parser
Extracts event slug from a Polymarket URL and resolves it to event/market data.
"""

from __future__ import annotations

import re
import logging

from api_client import PolymarketClient

logger = logging.getLogger(__name__)

# Matches:  /event/<slug>  or  /event/<slug>/sub-market-slug
_EVENT_SLUG_RE = re.compile(r"/event/([^/?#]+)")


def extract_slug(url: str) -> str | None:
    """Pull the event slug out of a Polymarket URL."""
    m = _EVENT_SLUG_RE.search(url)
    return m.group(1) if m else None


async def resolve_market(
    client: PolymarketClient, url: str
) -> dict:
    """
    Given a polymarket URL, return:
      {
        "event": { ... },
        "markets": [ {conditionId, slug, question, ...}, ... ],
        "condition_ids": ["0xabc...", ...],
      }
    """
    slug = extract_slug(url)
    if not slug:
        raise ValueError(f"Cannot extract event slug from URL: {url}")

    # Try event slug first
    event = await client.get_event_by_slug(slug)

    # If event lookup fails, try as market slug
    if not event:
        market = await client.get_market_by_slug(slug)
        if market:
            event_id = market.get("event_id") or market.get("eventId")
            if event_id:
                event = await client.get_event_by_id(event_id)

    if not event:
        raise ValueError(f"Could not resolve event for slug: {slug}")

    # Extract markets from the event
    markets = event.get("markets", [])
    if not markets:
        event_id = event.get("id")
        if event_id:
            markets = await client.get_markets_for_event(str(event_id))

    condition_ids = []
    for mkt in markets:
        cid = mkt.get("conditionId") or mkt.get("condition_id")
        if cid:
            condition_ids.append(cid)

    return {
        "event": event,
        "markets": markets,
        "condition_ids": condition_ids,
    }
