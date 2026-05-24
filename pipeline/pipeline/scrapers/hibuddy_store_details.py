"""
HiBuddy store-detail enrichment scraper.

Every HiBuddy store page (https://hibuddy.ca/store/{id}/{slug}) embeds a
schema.org JSON-LD LocalBusiness block containing:
  - streetAddress, addressLocality, addressRegion
  - geo.latitude, geo.longitude       ← we want these
  - telephone                          ← cross-check against existing
  - url                                ← page url

HOURS ARE NOT included in HiBuddy's JSON-LD — we still need Leafly/Weedmaps
for hours_json (separate scraper, next iteration).

This scraper iterates every store in dim_stores with a hibuddy_store_id +
hibuddy_slug, visits the page (Playwright headless), parses the JSON-LD,
and updates latitude / longitude / last_scraped_at.

Cadence: weekly is plenty — stores don't move often.

Run:
    uv run python -m pipeline.scrapers.hibuddy_store_details
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import Page, sync_playwright

from pipeline.config import get_settings
from pipeline.db.connection import get_connection
from pipeline.utils.logging import configure_logging, get_logger
from pipeline.utils.runs import run_logged

HIBUDDY_BASE = "https://hibuddy.ca"
PER_STORE_DELAY_S = 1.5

log = get_logger(__name__)


def _extract_local_business(page: Page) -> dict | None:
    """Walk every json-ld script block, return the first LocalBusiness/Store object."""
    blocks = page.locator('script[type="application/ld+json"]').all()
    for el in blocks:
        try:
            data = json.loads(el.inner_html())
        except Exception:
            continue
        candidates = []
        if isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                candidates.extend(data["@graph"])
            candidates.append(data)
        elif isinstance(data, list):
            candidates.extend(data)
        for c in candidates:
            if not isinstance(c, dict):
                continue
            t = c.get("@type") or ""
            if isinstance(t, list):
                t_lc = " ".join(t).lower()
            else:
                t_lc = str(t).lower()
            if any(k in t_lc for k in ("store", "localbusiness", "organization")):
                # Must have at least geo or address to be useful
                if c.get("geo") or c.get("address") or c.get("telephone"):
                    return c
    return None


def scrape_one_store(page: Page, store_id: int, hb_id: str, slug: str) -> dict | None:
    url = f"{HIBUDDY_BASE}/store/{hb_id}/{slug}"
    log.info("hibuddy_visit_store", store_id=store_id, slug=slug)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3000)
    except Exception as e:
        log.warning("hibuddy_load_failed", store_id=store_id, slug=slug, error=str(e))
        return None

    block = _extract_local_business(page)
    if not block:
        log.warning("no_localbusiness_jsonld", store_id=store_id, slug=slug)
        return None

    geo = block.get("geo") or {}
    address = block.get("address") or {}

    return {
        "store_id": store_id,
        "latitude": geo.get("latitude"),
        "longitude": geo.get("longitude"),
        "telephone": block.get("telephone"),
        "street_address": address.get("streetAddress") if isinstance(address, dict) else None,
        "url": block.get("url"),
    }


def update_store(record: dict) -> None:
    """Update dim_stores with whatever fields we extracted (only if not null)."""
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dim_stores SET
                latitude = COALESCE(%s, latitude),
                longitude = COALESCE(%s, longitude),
                last_scraped_at = %s
            WHERE store_id = %s
            """,
            (
                record.get("latitude"),
                record.get("longitude"),
                now,
                record["store_id"],
            ),
        )


def fetch_target_stores() -> list[tuple[int, str, str]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT store_id, hibuddy_store_id, hibuddy_slug
            FROM dim_stores
            WHERE hibuddy_store_id IS NOT NULL AND hibuddy_slug IS NOT NULL
            ORDER BY store_id
            """
        )
        return cur.fetchall()


def main() -> int:
    configure_logging()
    with run_logged("hibuddy_store_details") as ctx:
        return _scrape_all(ctx)


def _scrape_all(ctx) -> int:
    targets = fetch_target_stores()
    log.info("hibuddy_targets", count=len(targets))

    settings = get_settings()
    success = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.playwright_headless)
        ctx = browser.new_context(
            user_agent=settings.scrape_user_agent,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        for store_id, hb_id, slug in targets:
            record = scrape_one_store(page, store_id, hb_id, slug)
            if record:
                update_store(record)
                success += 1
                log.info(
                    "store_updated",
                    store_id=store_id,
                    lat=record["latitude"],
                    lng=record["longitude"],
                )
            time.sleep(PER_STORE_DELAY_S)

        ctx.close()
        browser.close()

    log.info("hibuddy_store_details_done", attempted=len(targets), updated=success)
    ctx.rows_processed = success
    ctx.metadata = {"stores_attempted": len(targets), "stores_updated": success}
    return 0


if __name__ == "__main__":
    sys.exit(main())
