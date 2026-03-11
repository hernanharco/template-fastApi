# ── 1. app/agents/routing/intent.py ──────────────────────────────────

from enum import Enum


class Intent(str, Enum):
    GREETING          = "GREETING"
    CATALOG           = "CATALOG"
    BOOKING           = "BOOKING"
    CONFIRMATION      = "CONFIRMATION"
    TIME_FILTER       = "TIME_FILTER"
    TIME_PARSER       = "TIME_PARSER"
    FAVORITE_FALLBACK = "FAVORITE_FALLBACK"   # ← nuevo
    FINISH            = "FINISH"
