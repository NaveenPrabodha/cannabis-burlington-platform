"""
Seed the database from the cleaned CSVs produced by the previous exercise.

Loads:
  - dim_stores       from raw stores.csv (has website column) + cleaned normalized name
  - dim_products     from clean_products.csv
  - fct_prices       from clean_prices.csv joined with product_matches_final.csv
  - fct_price_history  one row per (store, product, scraped_date) — same data as fct_prices,
                       but immutable; downstream pipeline runs will append more

Initial promo_first_seen / promo_last_seen are set to scraped_date for any row
with a sale_price — the daily refresh job will update them as it sees the same
sale persist or end.

Run:  uv run python scripts/seed_from_csvs.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "already_done" / "output"
CLEAN_DIR = RAW_DIR / "clean"

STORES_RAW = RAW_DIR / "stores.csv"
STORES_CLEAN = CLEAN_DIR / "clean_stores.csv"
PRODUCTS_FILE = CLEAN_DIR / "clean_products.csv"
PRICES_FILE = CLEAN_DIR / "clean_prices.csv"
MATCH_FILE = CLEAN_DIR / "product_matches_final.csv"


def _db_kwargs() -> dict:
    url = os.environ.get("SYNC_DATABASE_URL")
    if url:
        parsed = urlparse(url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "dbname": (parsed.path or "/cannabis_analysis").lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
        }
    return {
        "host": "localhost",
        "port": 5432,
        "dbname": "cannabis_analysis",
        "user": "postgres",
        "password": "admin",
    }


DB = _db_kwargs()


def safe_float(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        v = float(val)
        if v > 999_999:
            return None
        return v
    except Exception:
        return None


def truncate(cur) -> None:
    print("Truncating tables...")
    cur.execute(
        """
        TRUNCATE fct_ocs_launches RESTART IDENTITY CASCADE;
        TRUNCATE fct_price_history RESTART IDENTITY CASCADE;
        TRUNCATE fct_prices RESTART IDENTITY CASCADE;
        TRUNCATE dim_products RESTART IDENTITY CASCADE;
        TRUNCATE dim_stores RESTART IDENTITY CASCADE;
        """
    )


def load_stores(cur) -> dict[str, int]:
    """Merge raw stores (for website) with clean stores (for normalized_store_name)."""
    print("Loading stores...")
    raw = pd.read_csv(STORES_RAW)
    clean = pd.read_csv(STORES_CLEAN)

    merged = raw.merge(
        clean[["hibuddy_store_id", "normalized_store_name"]],
        on="hibuddy_store_id",
        how="left",
    )

    rows = [
        (
            r["name"],
            r["normalized_store_name"],
            r["address"],
            r["phone"],
            r["website"] if pd.notna(r["website"]) else None,
            r["hibuddy_store_id"],
            r["hibuddy_slug"],
        )
        for _, r in merged.iterrows()
    ]

    execute_values(
        cur,
        """
        INSERT INTO dim_stores (
            store_name, normalized_store_name, address, phone, website,
            hibuddy_store_id, hibuddy_slug
        ) VALUES %s
        """,
        rows,
    )

    cur.execute("SELECT store_id, hibuddy_store_id FROM dim_stores")
    lookup = {hsid: sid for sid, hsid in cur.fetchall()}
    print(f"  inserted {len(rows)} stores")
    return lookup


def load_products(cur) -> None:
    print("Loading products...")
    df = pd.read_csv(PRODUCTS_FILE)
    rows = [
        (
            int(r["ocs_product_id"]),
            r.get("name"),
            r.get("normalized_name"),
            r.get("brand"),
            r.get("normalized_brand"),
            r.get("category"),
            r.get("subcategory"),
            r.get("size") if pd.notna(r.get("size")) else None,
            r.get("description") if pd.notna(r.get("description")) else None,
            r.get("image_url") if pd.notna(r.get("image_url")) else None,
            safe_float(r.get("price")),
            safe_float(r.get("thc_min")),
            safe_float(r.get("thc_max")),
            safe_float(r.get("cbd_min")),
            safe_float(r.get("cbd_max")),
        )
        for _, r in df.iterrows()
    ]
    execute_values(
        cur,
        """
        INSERT INTO dim_products (
            product_id, name, normalized_name, brand, normalized_brand,
            category, subcategory, size, description, image_url,
            price, thc_min, thc_max, cbd_min, cbd_max
        ) VALUES %s
        """,
        rows,
    )
    print(f"  inserted {len(rows)} products")


def load_prices_and_history(cur, store_lookup: dict[str, int]) -> None:
    print("Loading prices + price history...")
    matches = pd.read_csv(MATCH_FILE)
    match_lookup = dict(zip(matches["hibuddy_product_id"], matches["product_id"]))

    prices = pd.read_csv(PRICES_FILE)

    fact_rows: dict[tuple[int, int], tuple] = {}
    history_rows: dict[tuple[int, int, str], tuple] = {}
    missing_store = 0
    missing_product = 0

    for _, r in prices.iterrows():
        sid = store_lookup.get(r.get("hibuddy_store_id"))
        if not sid:
            missing_store += 1
            continue

        pid = match_lookup.get(r.get("hibuddy_product_id"))
        if pid is None or pd.isna(pid):
            missing_product += 1
            continue

        pid = int(pid)
        scraped_date = r.get("scraped_date")
        regular_price = safe_float(r.get("regular_price"))
        sale_price = safe_float(r.get("sale_price"))
        discount_percent = safe_float(r.get("discount_percent"))
        typical_nearby = safe_float(r.get("typical_nearby"))
        in_stock = bool(r.get("in_stock"))

        # set initial promo window based on sale_price observation
        promo_first = scraped_date if sale_price is not None else None
        promo_last = scraped_date if sale_price is not None else None

        fact_key = (sid, pid)
        # keep latest scraped_date per (store, product) — overwrite if newer
        existing = fact_rows.get(fact_key)
        if existing is None or (scraped_date or "") >= (existing[2] or ""):
            fact_rows[fact_key] = (
                sid,
                pid,
                scraped_date,
                regular_price,
                sale_price,
                discount_percent,
                typical_nearby,
                in_stock,
                promo_first,
                promo_last,
            )

        # history is grain (store, product, date) — dedupe same-day rows
        history_rows[(sid, pid, scraped_date)] = (
            sid,
            pid,
            scraped_date,
            regular_price,
            sale_price,
            in_stock,
        )

    if fact_rows:
        execute_values(
            cur,
            """
            INSERT INTO fct_prices (
                store_id, product_id, scraped_date,
                regular_price, sale_price, discount_percent, typical_nearby,
                in_stock, promo_first_seen, promo_last_seen
            ) VALUES %s
            """,
            list(fact_rows.values()),
        )

    if history_rows:
        execute_values(
            cur,
            """
            INSERT INTO fct_price_history (
                store_id, product_id, scraped_date,
                regular_price, sale_price, in_stock
            ) VALUES %s
            """,
            list(history_rows.values()),
        )

    print(f"  inserted {len(fact_rows)} current prices")
    print(f"  inserted {len(history_rows)} history rows")
    print(f"  skipped {missing_store} rows missing store, {missing_product} missing product")


def print_stats(cur) -> None:
    print("\nFinal counts:")
    for tbl in ("dim_stores", "dim_products", "fct_prices", "fct_price_history"):
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl:20s} {cur.fetchone()[0]:>8d}")

    cur.execute(
        """
        SELECT COUNT(*) FROM fct_prices WHERE sale_price IS NOT NULL
        """
    )
    print(f"  on-sale rows         {cur.fetchone()[0]:>8d}")


def main() -> int:
    for path in (STORES_RAW, STORES_CLEAN, PRODUCTS_FILE, PRICES_FILE, MATCH_FILE):
        if not path.exists():
            print(f"ERROR: missing {path}", file=sys.stderr)
            return 1

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        truncate(cur)
        store_lookup = load_stores(cur)
        load_products(cur)
        load_prices_and_history(cur, store_lookup)
        conn.commit()
        print_stats(cur)
        print("\nSeed complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
