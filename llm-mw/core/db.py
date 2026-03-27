"""
PostgreSQL database layer for LLM Middleware.

Manages connection pool, schema creation, and data migration from JSON files.
All middleware data (users, prices, config, logs) lives in the 'middleware' database
on the same PostgreSQL instance used by Open WebUI.
"""

import os
import json
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2 import sql

logger = logging.getLogger("llm_mw")

# ─── Connection pool ─────────────────────────────────────────

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def _parse_dsn(database_url: str) -> dict:
    """Parse DATABASE_URL into keyword args for psycopg2."""
    # postgresql://user:pass@host:port/dbname
    from urllib.parse import urlparse
    parsed = urlparse(database_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "openwebui_user",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "middleware",
    }


def _ensure_database(database_url: str):
    """
    Ensure the 'middleware' database exists on the PostgreSQL instance.
    Connects to 'postgres' default DB to create it if needed.
    """
    params = _parse_dsn(database_url)
    target_db = params["dbname"]

    # Connect to default 'postgres' database
    conn = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname="postgres",
    )
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        if not cur.fetchone():
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
            logger.info("Created database '%s'", target_db)
        cur.close()
    finally:
        conn.close()


def init_pool(database_url: str, minconn: int = 2, maxconn: int = 10):
    """
    Initialize the connection pool. Called once at startup.
    Creates the target database if it doesn't exist, then creates tables.
    """
    global _pool
    if _pool is not None:
        return

    _ensure_database(database_url)

    params = _parse_dsn(database_url)
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname=params["dbname"],
    )
    logger.info("DB pool initialized: %s@%s:%s/%s (min=%d, max=%d)",
                params["user"], params["host"], params["port"],
                params["dbname"], minconn, maxconn)

    # Create tables
    _create_tables()

    # Auto-migrate from JSON if tables are empty
    _auto_migrate_if_empty()


def get_conn():
    """Get a connection from the pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool.getconn()


def put_conn(conn):
    """Return a connection to the pool."""
    if _pool is not None:
        _pool.putconn(conn)


@contextmanager
def db_conn():
    """Context manager for database connections with auto-commit/rollback."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


# ─── Schema creation ─────────────────────────────────────────

_SCHEMA_SQL = """
-- Users table (replaces users.json)
CREATE TABLE IF NOT EXISTS mw_users (
    user_id        TEXT PRIMARY KEY,
    subkey         TEXT,
    subkey_hash    TEXT,
    active         BOOLEAN DEFAULT true,
    allowed_models JSONB DEFAULT '["*"]'::jsonb,
    used_tokens    BIGINT DEFAULT 0,
    used_cost_usd  DOUBLE PRECISION DEFAULT 0.0,
    quota          JSONB DEFAULT '{}'::jsonb,
    alerts_sent    JSONB DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- Prices table (replaces prices.json)
CREATE TABLE IF NOT EXISTS mw_prices (
    model_name TEXT PRIMARY KEY,
    pricing    JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Config table (replaces alert_config.json + system_alerts.json)
CREATE TABLE IF NOT EXISTS mw_config (
    config_key   TEXT PRIMARY KEY,
    config_value JSONB NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT now()
);

-- Pending requests (replaces pending.csv)
CREATE TABLE IF NOT EXISTS mw_pending (
    request_id TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    ts         BIGINT NOT NULL
);

-- Audit log (replaces audit.jsonl)
CREATE TABLE IF NOT EXISTS mw_audit_log (
    id            BIGSERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ DEFAULT now(),
    rid           TEXT,
    user_id       TEXT,
    endpoint      TEXT,
    model         TEXT,
    purpose       TEXT,
    status        TEXT,
    status_code   INTEGER,
    latency_ms    DOUBLE PRECISION,
    tokens_in     INTEGER DEFAULT 0,
    tokens_out    INTEGER DEFAULT 0,
    tokens_total  INTEGER DEFAULT 0,
    cost_usd      DOUBLE PRECISION DEFAULT 0.0,
    image_count   INTEGER,
    tts_chars     INTEGER,
    stt_seconds   DOUBLE PRECISION,
    video_count   INTEGER,
    error_type    TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON mw_audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_user ON mw_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_rid ON mw_audit_log(rid);

-- Request detail log (replaces middleware.requests.log)
CREATE TABLE IF NOT EXISTS mw_request_log (
    id      BIGSERIAL PRIMARY KEY,
    ts      TIMESTAMPTZ DEFAULT now(),
    payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reqlog_ts ON mw_request_log(ts);

-- Notifications table (alert history for dashboard + digest)
CREATE TABLE IF NOT EXISTS mw_notifications (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ DEFAULT now(),
    user_id     TEXT,
    type        TEXT NOT NULL,
    level       TEXT DEFAULT 'info',
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    read        BOOLEAN DEFAULT false,
    emailed     BOOLEAN DEFAULT false,
    metadata    JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON mw_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_read ON mw_notifications(read);
CREATE INDEX IF NOT EXISTS idx_notif_ts   ON mw_notifications(ts);
"""


def _create_tables():
    """Create all middleware tables if they don't exist."""
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(_SCHEMA_SQL)
        cur.close()
    logger.info("Database schema verified/created")


# ─── JSON → DB migration ─────────────────────────────────────

def _auto_migrate_if_empty():
    """If tables are empty, import data from JSON files (one-time migration)."""
    from config import DATA_DIR, BACKUP_DATA_DIR

    with db_conn() as conn:
        cur = conn.cursor()

        # Check if mw_users is empty
        cur.execute("SELECT count(*) FROM mw_users")
        user_count = cur.fetchone()[0]

        if user_count == 0:
            logger.info("mw_users is empty — importing from JSON files...")
            # Search in backup/ dir first, then fall back to old data/ dir
            _import_users(conn, cur, BACKUP_DATA_DIR, DATA_DIR)
            _import_prices(conn, cur, BACKUP_DATA_DIR, DATA_DIR)
            _import_config(conn, cur, BACKUP_DATA_DIR, DATA_DIR)
            _import_pending(conn, cur, BACKUP_DATA_DIR, DATA_DIR)
            logger.info("JSON → DB migration complete")
        else:
            logger.info("DB already has %d users — skipping auto-migration", user_count)

        cur.close()


def _import_users(conn, cur, data_dir: str, fallback_dir: str = None):
    """Import users from users.json into mw_users table."""
    users_file = os.path.join(data_dir, "users.json")
    if not os.path.exists(users_file) and fallback_dir:
        users_file = os.path.join(fallback_dir, "users.json")
    if not os.path.exists(users_file):
        logger.warning("users.json not found — skipping")
        return

    with open(users_file, "r", encoding="utf-8-sig") as f:
        users = json.load(f)

    for u in users:
        cur.execute("""
            INSERT INTO mw_users (user_id, subkey, subkey_hash, active, allowed_models,
                                  used_tokens, used_cost_usd, quota, alerts_sent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (
            u.get("user_id"),
            u.get("subkey"),
            u.get("subkey_hash"),
            u.get("active", True),
            json.dumps(u.get("allowed_models", ["*"])),
            u.get("used_tokens", 0),
            u.get("used_cost_usd", 0.0),
            json.dumps(u.get("quota", {})),
            json.dumps(u.get("alerts_sent", {})),
        ))

    logger.info("Imported %d users from users.json", len(users))


def _import_prices(conn, cur, data_dir: str, fallback_dir: str = None):
    """Import prices from prices.json into mw_prices table."""
    prices_file = os.path.join(data_dir, "prices.json")
    if not os.path.exists(prices_file) and fallback_dir:
        prices_file = os.path.join(fallback_dir, "prices.json")
    if not os.path.exists(prices_file):
        logger.warning("prices.json not found — skipping")
        return

    with open(prices_file, "r", encoding="utf-8") as f:
        prices = json.load(f)

    # Store _schema as a special row
    schema_info = prices.pop("_schema", None)
    if schema_info:
        cur.execute("""
            INSERT INTO mw_prices (model_name, pricing)
            VALUES ('_schema', %s)
            ON CONFLICT (model_name) DO NOTHING
        """, (json.dumps(schema_info),))

    for model_name, pricing in prices.items():
        cur.execute("""
            INSERT INTO mw_prices (model_name, pricing)
            VALUES (%s, %s)
            ON CONFLICT (model_name) DO NOTHING
        """, (model_name, json.dumps(pricing)))

    logger.info("Imported %d price entries from prices.json", len(prices))


def _import_config(conn, cur, data_dir: str, fallback_dir: str = None):
    """Import alert_config.json and system_alerts.json into mw_config."""
    # Alert config
    alert_file = os.path.join(data_dir, "alert_config.json")
    if not os.path.exists(alert_file) and fallback_dir:
        alert_file = os.path.join(fallback_dir, "alert_config.json")
    if os.path.exists(alert_file):
        with open(alert_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        cur.execute("""
            INSERT INTO mw_config (config_key, config_value)
            VALUES ('alert_config', %s)
            ON CONFLICT (config_key) DO NOTHING
        """, (json.dumps(config),))
        logger.info("Imported alert_config.json")

    alerts_file = os.path.join(data_dir, "system_alerts.json")
    if not os.path.exists(alerts_file) and fallback_dir:
        alerts_file = os.path.join(fallback_dir, "system_alerts.json")
    if os.path.exists(alerts_file):
        with open(alerts_file, "r", encoding="utf-8") as f:
            try:
                alerts = json.load(f)
            except json.JSONDecodeError:
                alerts = {}
        cur.execute("""
            INSERT INTO mw_config (config_key, config_value)
            VALUES ('system_alerts', %s)
            ON CONFLICT (config_key) DO NOTHING
        """, (json.dumps(alerts),))
        logger.info("Imported system_alerts.json")


def _import_pending(conn, cur, data_dir: str, fallback_dir: str = None):
    """Import pending.csv into mw_pending table."""
    import csv
    pending_file = os.path.join(data_dir, "pending.csv")
    if not os.path.exists(pending_file) and fallback_dir:
        pending_file = os.path.join(fallback_dir, "pending.csv")
    if not os.path.exists(pending_file):
        return

    with open(pending_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) <= 1:
        return  # Empty or header-only

    count = 0
    for row in rows[1:]:
        if len(row) >= 3:
            cur.execute("""
                INSERT INTO mw_pending (request_id, user_id, ts)
                VALUES (%s, %s, %s)
                ON CONFLICT (request_id) DO NOTHING
            """, (row[0], row[1], int(row[2])))
            count += 1

    if count:
        logger.info("Imported %d pending requests from pending.csv", count)


# ─── Helper: write to audit/request log tables ───────────────

def insert_audit_log(data: dict):
    """Insert a row into mw_audit_log. Non-blocking best-effort."""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO mw_audit_log
                    (ts, rid, user_id, endpoint, model, purpose, status,
                     status_code, latency_ms, tokens_in, tokens_out, tokens_total,
                     cost_usd, image_count, tts_chars, stt_seconds, video_count,
                     error_type, error_message)
                VALUES (
                    COALESCE(%s::timestamptz, now()), %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                data.get("ts"),
                data.get("rid"),
                data.get("user_id"),
                data.get("endpoint"),
                data.get("model"),
                data.get("purpose"),
                data.get("status"),
                data.get("status_code"),
                data.get("latency_ms"),
                data.get("tokens_in", 0),
                data.get("tokens_out", 0),
                data.get("tokens_total", 0),
                data.get("cost_usd", 0.0),
                data.get("image_count"),
                data.get("tts_chars"),
                data.get("stt_seconds"),
                data.get("video_count"),
                data.get("error_type"),
                data.get("error_message"),
            ))
            cur.close()
    except Exception as e:
        logger.error("insert_audit_log failed: %s", str(e))


def insert_request_log(payload: dict):
    """Insert a row into mw_request_log. Non-blocking best-effort."""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO mw_request_log (payload) VALUES (%s)",
                (json.dumps(payload, ensure_ascii=False),)
            )
            cur.close()
    except Exception as e:
        logger.error("insert_request_log failed: %s", str(e))
