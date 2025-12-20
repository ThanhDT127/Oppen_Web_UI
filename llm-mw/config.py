"""
Configuration module for LLM Middleware.
Contains all constants, environment variables, and logging setup.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# ============================================================================
# BASE PATHS
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables from .env file
_env_candidates = [
    os.path.join(BASE_DIR, ".env"),
    os.path.abspath(os.path.join(BASE_DIR, "..", ".env")),
]
for _env_path in _env_candidates:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        break
else:
    load_dotenv()

# ============================================================================
# DATA FILES (in data/ subdirectory)
# ============================================================================

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
PRICES_FILE = os.path.join(DATA_DIR, "prices.json")
PENDING_CSV = os.path.join(DATA_DIR, "pending.csv")

# ============================================================================
# LOG FILES (in ../logs/ directory)
# ============================================================================

LOG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

MW_LOG_FILE = os.path.join(LOG_DIR, "middleware.log")
MW_DETAIL_LOG_FILE = os.path.join(LOG_DIR, "middleware.requests.log")
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit.jsonl")
LITELLM_LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "litellm", "litellm.log"))

# Media storage (in logs/mw_media/)
MW_MEDIA_DIR = os.path.join(LOG_DIR, "mw_media")
os.makedirs(MW_MEDIA_DIR, exist_ok=True)

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

LITELLM_BASE = os.getenv("LITELLM_BASE", "http://127.0.0.1:4000/v1").strip()
LITELLM_KEY = os.getenv("LITELLM_KEY", "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()
MW_SECRET = os.getenv("MW_SECRET", "default-secret-CHANGE-IN-PRODUCTION").strip()

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Main logger (middleware.log)
logger = logging.getLogger("llm_mw")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = RotatingFileHandler(MW_LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_h)

# Detail logger (middleware.requests.log - JSON format)
detail_logger = logging.getLogger("llm_mw_detail")
if not detail_logger.handlers:
    detail_logger.setLevel(logging.INFO)
    _dh = RotatingFileHandler(MW_DETAIL_LOG_FILE, maxBytes=20_000_000, backupCount=5, encoding="utf-8")
    _dh.setFormatter(logging.Formatter("%(message)s"))
    detail_logger.addHandler(_dh)

# Audit logger (audit.jsonl)
audit_logger = logging.getLogger("llm_mw_audit")
if not audit_logger.handlers:
    audit_logger.setLevel(logging.INFO)
    _ah = RotatingFileHandler(AUDIT_LOG_FILE, maxBytes=50_000_000, backupCount=5, encoding="utf-8")
    _ah.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(_ah)

# ============================================================================
# CONSTANTS
# ============================================================================

# Restricted models (special handling)
RESTRICTED_MODELS = {"gpt-image-1", "sora-2", "sora-2-pro"}

# Sensitive keys for redaction in logs
SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "token",
    "secret",
    "password",
    "openai_api_key",
    "gemini_api_key",
    "litellm_key",
    "subkey",
    "subkey_hash",
}
