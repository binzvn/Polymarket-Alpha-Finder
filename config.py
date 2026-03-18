"""
Polymarket Alpha Finder - Configuration & Constants
"""

# ─── API Base URLs ───────────────────────────────────────────────
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DATA_API_BASE  = "https://data-api.polymarket.com"

# ─── Concurrency / Rate Limiting ─────────────────────────────────
MAX_CONCURRENT_REQUESTS = 20       # asyncio.Semaphore cap
REQUEST_TIMEOUT         = 30       # seconds per HTTP request
TRADES_PAGE_SIZE        = 500      # max rows per /trades page
ACTIVITY_PAGE_SIZE      = 500      # max rows per /activity page

# ─── Classification Thresholds ───────────────────────────────────
# Whale Gambler
WHALE_MIN_VOLUME         = 5000     # USD total volume
WHALE_MIN_CONCENTRATION  = 0.60     # 60 %+ in single outcome
WHALE_MAX_DIVERSIFICATION = 3       # ≤ 3 categories

# Scalper
SCALPER_MIN_TRADE_FREQ   = 5        # ≥ 5 trades / day
SCALPER_MAX_AVG_BET      = 200      # ≤ $200 avg bet

# Systematic (else branch, but also validated)
SYSTEMATIC_MIN_DIVERSIFICATION = 4  # ≥ 4 categories
SYSTEMATIC_MAX_CONCENTRATION   = 0.40  # ≤ 40 %
SYSTEMATIC_MIN_WIN_RATE        = 0.40  # ≥ 40 %

# ─── Scoring Weights (must sum to 100) ───────────────────────────
WEIGHT_WIN_RATE           = 35
WEIGHT_DIVERSIFICATION    = 20
WEIGHT_CONSISTENCY        = 15
WEIGHT_INV_CONCENTRATION  = 15
WEIGHT_TYPE_BONUS         = 15

# Type bonus raw values (will be normalised to 0-1 via /15)
TYPE_BONUS_SYSTEMATIC = 15
TYPE_BONUS_SCALPER    = 5
TYPE_BONUS_WHALE      = 0

# ─── Passing filter thresholds ───────────────────────────────────
PASSING_MIN_SCORE     = 50
PASSING_MIN_WIN_RATE  = 0.50
PASSING_MIN_MARKETS   = 5
