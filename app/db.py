
import os, json, pathlib
import duckdb

DB_CONN = None

def get_conn():
    global DB_CONN
    if DB_CONN is not None:
        return DB_CONN

    token = os.getenv("MOTHERDUCK_TOKEN")
    dbname = os.getenv("MOTHERDUCK_DATABASE", "acp_demo")

    if token:
        # MotherDuck cloud
        os.environ["MOTHERDUCK_TOKEN"] = token
        conn = duckdb.connect(f"md:{dbname}")
    else:
        # Local DuckDB fallback
        conn = duckdb.connect("local.duckdb")

    DB_CONN = conn
    return DB_CONN

def init_db():
    conn = get_conn()
    # Create tables if not exist
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
            product_id TEXT,
            quantity INTEGER,
            created_at TIMESTAMP DEFAULT now()
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            payment_intent_id TEXT,
            buyer_email TEXT,
            amount_minor BIGINT,
            currency TEXT,
            product_id TEXT,
            quantity INTEGER,
            created_at TIMESTAMP DEFAULT now()
        );
    """)

    # Seed products from JSON if table empty
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
