import os
from dotenv import load_dotenv

load_dotenv()

USE_OPENROUTER             = os.getenv("USE_OPENROUTER", "false").lower() == "true"
OPENROUTER_API_KEY         = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE            = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
OPENROUTER_REFERER         = os.getenv("OPENROUTER_REFERER", "https://aiqbiq.com")
OPENROUTER_TITLE           = os.getenv("OPENROUTER_TITLE", "AIQBIQ Biosimilar Arena")
ANTHROPIC_API_KEY          = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_DEMO_MODEL       = os.getenv("ANTHROPIC_DEMO_MODEL", "claude-sonnet-4-20250514")
ACCESS_KEY                 = os.getenv("ACCESS_KEY", "")
DATABASE_URL               = os.getenv("DATABASE_URL", "")
try:
    ARENA_COST_DAILY_LIMIT_USD = float(os.getenv("ARENA_COST_DAILY_LIMIT_USD", "20"))
except (TypeError, ValueError):
    ARENA_COST_DAILY_LIMIT_USD = 20.0

try:
    ARENA_CACHE_TTL_HOURS = int(os.getenv("ARENA_CACHE_TTL_HOURS", "168"))
except (TypeError, ValueError):
    ARENA_CACHE_TTL_HOURS = 168
