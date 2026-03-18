"""
Polymarket Alpha Finder - Wallet Classifier
Classifies each wallet as Whale Gambler, Scalper, or Systematic.
"""

from __future__ import annotations

from config import (
    WHALE_MIN_VOLUME,
    WHALE_MIN_CONCENTRATION,
    WHALE_MAX_DIVERSIFICATION,
    SCALPER_MIN_TRADE_FREQ,
    SCALPER_MAX_AVG_BET,
    SYSTEMATIC_MIN_DIVERSIFICATION,
    SYSTEMATIC_MAX_CONCENTRATION,
    SYSTEMATIC_MIN_WIN_RATE,
)


def classify_wallet(metrics: dict) -> str:
    """
    Classify a wallet into one of three categories based on behaviour:
      - "whale_gambler"
      - "scalper"
      - "systematic"

    Uses a priority-based rule system:
      1. Check Whale first (volume + concentration + low diversification)
      2. Check Scalper (high freq + small bets)
      3. Else → Systematic (if criteria met) or default to whale_gambler
    """
    total_volume = metrics.get("avg_bet_size", 0) * metrics.get("total_positions", 0)
    concentration = metrics.get("concentration", 1.0)
    diversification = metrics.get("diversification", 1)
    trade_freq = metrics.get("trade_frequency", 0)
    avg_bet = metrics.get("avg_bet_size", 0)
    win_rate = metrics.get("win_rate", 0)

    # ── Scalper ──────────────────────────────────────────────────
    if trade_freq >= SCALPER_MIN_TRADE_FREQ and avg_bet <= SCALPER_MAX_AVG_BET:
        return "scalper"

    # ── Systematic ───────────────────────────────────────────────
    if (
        diversification >= SYSTEMATIC_MIN_DIVERSIFICATION
        and concentration <= SYSTEMATIC_MAX_CONCENTRATION
        and win_rate >= SYSTEMATIC_MIN_WIN_RATE
    ):
        return "systematic"

    # ── Whale Gambler (high volume + concentrated) ───────────────
    if (
        total_volume >= WHALE_MIN_VOLUME
        and concentration >= WHALE_MIN_CONCENTRATION
    ):
        return "whale_gambler"

    # ── Loose Systematic check ───────────────────────────────────
    if diversification >= SYSTEMATIC_MIN_DIVERSIFICATION and win_rate >= SYSTEMATIC_MIN_WIN_RATE:
        return "systematic"

    # ── Default fallback ─────────────────────────────────────────
    return "whale_gambler"
