
import os, json, pathlib
import duckdb
from typing import Optional

DB_CONN = None

def get_conn():
    global DB_CONN
    if DB_CONN is not None:
        return DB_CONN

    token = os.getenv("MOTHERDUCK_TOKEN")
    dbname = os.getenv("MOTHERDUCK_DATABASE", "acp_demo")

    if token:
        os.environ["MOTHERDUCK_TOKEN"] = token
        conn = duckdb.connect(f"md:{dbname}")
    else:
        conn = duckdb.connect("local.duckdb")

    DB_CONN = conn
    return DB_CONN

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            price DOUBLE,
            currency TEXT,
            image TEXT,
            available BOOLEAN
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checkout_sessions (
            id TEXT PRIMARY KEY,
            status TEXT,
            payment_intent_id TEXT,
            buyer_email TEXT,
            currency TEXT,
            items_json TEXT,
            promo_code TEXT,
            totals_json TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            payment_intent_id TEXT,
            buyer_email TEXT,
            amount_minor BIGINT,
            currency TEXT,
            items_json TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idempotency (
            key TEXT PRIMARY KEY,
            endpoint TEXT,
            response_json TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outbound_events (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            type TEXT,
            payload_json TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
    """)

    # Seed products from JSON if empty
    count = conn.execute("SELECT count(*) FROM products").fetchone()[0]
    if count == 0:
        path = pathlib.Path(__file__).parent / "data" / "product_feed.json"
        with open(path, "r", encoding="utf-8") as f:
            feed = json.load(f)
        for p in feed.get("products", []):
            conn.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                [p["id"], p["title"], p.get("description",""), float(p["price"]), p.get("currency","eur"),
                 p.get("image"), bool(p.get("available", True))]
            )

def get_idempotent_response(key: Optional[str], endpoint: str):
    if not key:
        return None
    conn = get_conn()
    row = conn.execute("SELECT response_json FROM idempotency WHERE key = ? AND endpoint = ?", [key, endpoint]).fetchone()
    return row[0] if row else None

def save_idempotent_response(key: str, endpoint: str, response_json: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO idempotency (key, endpoint, response_json) VALUES (?, ?, ?)", [key, endpoint, response_json])
