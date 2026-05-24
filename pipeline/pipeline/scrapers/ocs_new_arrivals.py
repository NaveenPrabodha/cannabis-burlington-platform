"""
OCS new-arrivals scraper.

Polls the public OCS Shopify products.json feed, finds any product whose
`published_at` is within the last N days, and:

  1. UPSERTs the product into dim_products (so the website can show it
     even if no Burlington store carries it yet).
  2. INSERTs a row into fct_ocs_launches keyed by (product_id, launch_date).

This delivers the brief's "new and upcoming items appearing through the
Ontario Cannabis Store" requirement.

Run:
    uv run python -m pipeline.scrapers.ocs_new_arrivals --days 30
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from psycopg2.extras import execute_values
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline.config import get_settings
from pipeline.db.connection import get_connection
from pipeline.utils.lang import detect_language
from pipeline.utils.logging import configure_logging, get_logger
from pipeline.utils.runs import run_logged

OCS_BASE = "https://ocs.ca"
PAGE_DELAY_S = 0.5
PAGE_SIZE = 250

log = get_logger(__name__)

THC_TAG_RE = re.compile(r"^THC:(\d+(?:\.\d+)?)$", re.I)
CBD_TAG_RE = re.compile(r"^CBD:(\d+(?:\.\d+)?)$", re.I)
THC_HTML_RE = re.compile(r"THC[:\s]*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?", re.I)
CBD_HTML_RE = re.compile(r"CBD[:\s]*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?", re.I)


def _strip_html(html: str | None) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _parse_cannabinoids(body_html: str, tags: list[str]) -> tuple:
    thc_min = thc_max = cbd_min = cbd_max = None
    for tag in tags or []:
        t = str(tag).strip()
        if (m := THC_TAG_RE.match(t)):
            thc_min = thc_max = float(m.group(1))
        if (m := CBD_TAG_RE.match(t)):
            cbd_min = cbd_max = float(m.group(1))

    text = _strip_html(body_html)
    if thc_min is None and (m := THC_HTML_RE.search(text)):
        thc_min = float(m.group(1))
        thc_max = float(m.group(2)) if m.group(2) else thc_min
    if cbd_min is None and (m := CBD_HTML_RE.search(text)):
        cbd_min = float(m.group(1))
        cbd_max = float(m.group(2)) if m.group(2) else cbd_min
    return thc_min, thc_max, cbd_min, cbd_max


def _normalize(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"\s+", " ", s).strip().upper()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _fetch_page(client: httpx.Client, page: int) -> list[dict]:
    r = client.get(f"{OCS_BASE}/products.json", params={"limit": PAGE_SIZE, "page": page})
    r.raise_for_status()
    return r.json().get("products", [])


def fetch_recent_products(days: int) -> list[dict]:
    """Return only products whose published_at falls within the last `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []

    headers = {
        "User-Agent": get_settings().scrape_user_agent,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://ocs.ca/",
    }
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
        page = 1
        # OCS is reverse-chronological by default for many storefronts but not guaranteed,
        # so we paginate all and filter. Cheap because we only need recent items.
        while True:
            batch = _fetch_page(client, page)
            if not batch:
                break

            for p in batch:
                published_at = p.get("published_at") or p.get("created_at")
                if not published_at:
                    continue
                try:
                    ts = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if ts >= cutoff:
                    p["__published_at"] = ts
                    out.append(p)

            log.info("ocs_page_fetched", page=page, products=len(batch), kept=len(out))
            page += 1
            time.sleep(PAGE_DELAY_S)

            if page > 200:  # safety guard — OCS catalog ~10k products / 250 page size = 40 pages
                break

    return out


def upsert_products(rows: list[dict]) -> int:
    """Upsert each new SKU into dim_products. Returns the number of rows touched."""
    if not rows:
        return 0

    payload = []
    for p in rows:
        try:
            pid = int(p.get("id"))
        except (TypeError, ValueError):
            continue

        thc_min, thc_max, cbd_min, cbd_max = _parse_cannabinoids(p.get("body_html"), p.get("tags") or [])

        variants = p.get("variants") or []
        price = None
        size = None
        if variants:
            v = variants[0]
            try:
                price = float(v.get("price")) if v.get("price") is not None else None
            except (TypeError, ValueError):
                price = None
            size = v.get("title")

        images = p.get("images") or []
        image_url = images[0].get("src") if images else None

        description_text = _strip_html(p.get("body_html")) or None
        description_lang = detect_language(description_text)

        payload.append(
            (
                pid,
                p.get("title"),
                _normalize(p.get("title")),
                p.get("vendor"),
                _normalize(p.get("vendor")),
                p.get("product_type"),
                None,  # subcategory
                size,
                description_text,
                description_lang,
                image_url,
                price,
                thc_min,
                thc_max,
                cbd_min,
                cbd_max,
                datetime.now(timezone.utc),
            )
        )

    with get_connection() as conn:
        cur = conn.cursor()
        execute_values(
            cur,
            """
            INSERT INTO dim_products (
                product_id, name, normalized_name, brand, normalized_brand,
                category, subcategory, size, description, description_lang,
                image_url, price, thc_min, thc_max, cbd_min, cbd_max,
                last_scraped_at
            )
            VALUES %s
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                normalized_name = EXCLUDED.normalized_name,
                brand = EXCLUDED.brand,
                normalized_brand = EXCLUDED.normalized_brand,
                category = EXCLUDED.category,
                size = EXCLUDED.size,
                description = EXCLUDED.description,
                description_lang = EXCLUDED.description_lang,
                image_url = EXCLUDED.image_url,
                price = EXCLUDED.price,
                thc_min = EXCLUDED.thc_min,
                thc_max = EXCLUDED.thc_max,
                cbd_min = EXCLUDED.cbd_min,
                cbd_max = EXCLUDED.cbd_max,
                last_scraped_at = EXCLUDED.last_scraped_at
            """,
            payload,
        )
        log.info("dim_products_upserted", count=len(payload))
        return len(payload)


def insert_launches(rows: list[dict]) -> int:
    """Insert a fct_ocs_launches row for each (product_id, launch_date) seen for the first time."""
    if not rows:
        return 0

    payload = []
    for p in rows:
        try:
            pid = int(p.get("id"))
        except (TypeError, ValueError):
            continue
        ts: datetime = p.get("__published_at")  # type: ignore[assignment]
        launch_date = ts.date()

        variants = p.get("variants") or []
        ocs_price = None
        if variants:
            try:
                ocs_price = float(variants[0].get("price"))
            except (TypeError, ValueError):
                ocs_price = None

        url = None
        if handle := p.get("handle"):
            url = f"{OCS_BASE}/products/{handle}"

        payload.append(
            (pid, launch_date, p.get("title"), p.get("vendor"), p.get("product_type"), ocs_price, url)
        )

    with get_connection() as conn:
        cur = conn.cursor()
        # We don't have a natural unique constraint on (product_id, launch_date) yet,
        # so guard against re-inserts with NOT EXISTS.
        execute_values(
            cur,
            """
            INSERT INTO fct_ocs_launches (
                product_id, launch_date, name, brand, category, ocs_price, url
            )
            SELECT v.product_id, v.launch_date, v.name, v.brand, v.category, v.ocs_price, v.url
            FROM (VALUES %s) AS v(product_id, launch_date, name, brand, category, ocs_price, url)
            WHERE NOT EXISTS (
                SELECT 1 FROM fct_ocs_launches l
                WHERE l.product_id = v.product_id AND l.launch_date = v.launch_date
            )
            """,
            payload,
        )
        log.info("fct_ocs_launches_inserted", count=len(payload))
        return len(payload)


def main(days: int) -> int:
    configure_logging()
    with run_logged("ocs_new_arrivals") as ctx:
        log.info("ocs_new_arrivals_start", days=days)
        products = fetch_recent_products(days)
        log.info("recent_products_total", count=len(products))

        if not products:
            log.warning("no_recent_products")
            ctx.rows_processed = 0
            ctx.metadata = {"days_window": days, "products_found": 0}
            return 0

        upserted = upsert_products(products)
        inserted = insert_launches(products)
        ctx.rows_processed = inserted
        ctx.metadata = {
            "days_window": days,
            "products_found": len(products),
            "products_upserted": upserted,
            "launches_inserted": inserted,
        }
        log.info("ocs_new_arrivals_done", upserted=upserted, inserted_launches=inserted)
        return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30, help="Window for 'recent' products")
    args = parser.parse_args()
    sys.exit(0 if main(args.days) >= 0 else 1)
