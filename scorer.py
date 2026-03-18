"""
Polymarket Alpha Finder - Scoring Engine
Weighted formula producing a 0-100 score for each wallet.
"""

from __future__ import annotations

from config import (
    WEIGHT_WIN_RATE,
    WEIGHT_DIVERSIFICATION,
    WEIGHT_CONSISTENCY,
    WEIGHT_INV_CONCENTRATION,
    WEIGHT_TYPE_BONUS,
    TYPE_BONUS_SYSTEMATIC,
    TYPE_BONUS_SCALPER,
    TYPE_BONUS_WHALE,
    PASSING_MIN_SCORE,
    PASSING_MIN_WIN_RATE,
    PASSING_MIN_MARKETS,
)


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


def score_wallet(metrics: dict, wallet_type: str) -> dict:
    """
    Compute a 0-100 score and a pass/fail filter result.

    Components (normalised 0-1 before weighting):
      1. Win Rate         (×35)  — direct 0-1
      2. Diversification  (×20)  — capped at 10 categories
      3. Consistency      (×15)  — low CV = high consistency
      4. Inv Concentration(×15)  — 1 - concentration
      5. Type Bonus       (×15)  — Systematic 15, Scalper 5, Whale 0
    """
    win_rate = _clamp(metrics.get("win_rate", 0))

    div_raw = metrics.get("diversification", 1)
    div_norm = _clamp(div_raw / 10.0)          # 10 categories = max

    cv = metrics.get("cv", 0)
    consistency = _clamp(1.0 - cv / 5.0)       # CV of 5+ = 0 consistency

    concentration = metrics.get("concentration", 1.0)
    inv_concentration = _clamp(1.0 - concentration)

    type_bonus_map = {
        "systematic": TYPE_BONUS_SYSTEMATIC,
        "scalper": TYPE_BONUS_SCALPER,
        "whale_gambler": TYPE_BONUS_WHALE,
    }
    type_bonus = _clamp(type_bonus_map.get(wallet_type, 0) / 15.0)

    raw_score = (
        win_rate * WEIGHT_WIN_RATE
        + div_norm * WEIGHT_DIVERSIFICATION
        + consistency * WEIGHT_CONSISTENCY
        + inv_concentration * WEIGHT_INV_CONCENTRATION
        + type_bonus * WEIGHT_TYPE_BONUS
    )
    score = int(round(_clamp(raw_score / 100, 0, 1) * 100))

    # ── Pass / Fail filter ───────────────────────────────────────
    passes = (
        score >= PASSING_MIN_SCORE
        and metrics.get("win_rate", 0) >= PASSING_MIN_WIN_RATE
        and metrics.get("num_markets", 0) >= PASSING_MIN_MARKETS
    )

    return {
        "score": score,
        "passes_filter": passes,
        "breakdown": {
            "win_rate_component": round(win_rate * WEIGHT_WIN_RATE, 2),
            "diversification_component": round(div_norm * WEIGHT_DIVERSIFICATION, 2),
            "consistency_component": round(consistency * WEIGHT_CONSISTENCY, 2),
            "inv_concentration_component": round(inv_concentration * WEIGHT_INV_CONCENTRATION, 2),
            "type_bonus_component": round(type_bonus * WEIGHT_TYPE_BONUS, 2),
        },
    }
