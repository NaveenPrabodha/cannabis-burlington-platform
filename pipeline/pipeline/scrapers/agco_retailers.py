"""
AGCO Cannabis Retail Store Authorization scraper.

The AGCO publishes a public list of all cannabis retail store applications
(license number, store name, city, address, postal code, status, website) at
https://www.agco.ca/en/cannabis/status-current-cannabis-retail-store-applications

The page's "Download CSV" button triggers a Drupal batch export that doesn't
deliver a file via a normal download event — the batch finishes and the page
just redirects to the homepage. So instead we scrape the rendered HTML table
directly, walking all pagination pages.

The table does NOT include operator/owner personal names — that data is marked
Restricted by AGCO. What we get per row:
  - License Number  → agco_licence_number      (canonical join key)
  - City or Town    → matching filter
  - Store Name      → cross-check store_name
  - Address         → fuzzy-match key to dim_stores.address
  - Postal Code     → useful for geo
  - Status          → is_active (only "Authorized to Open" / "Open" → true)
  - Website         → backfill for stores missing it

Run:
    uv run python -m pipeline.scrapers.agco_retailers
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from playwright.sync_api import Page, sync_playwright
from rapidfuzz import fuzz, process

from pipeline.config import get_settings
from pipeline.db.connection import get_connection
from pipeline.utils.logging import configure_logging, get_logger
from pipeline.utils.runs import run_logged

LANDING_URL = (
    "https://www.agco.ca/en/cannabis/status-current-cannabis-retail-store-applications"
)

# 35 km radius cities mentioned in the PDF as our market
MARKET_CITIES = {
    "burlington",
    "oakville",
    "hamilton",
    "waterdown",
    "milton",
    "grimsby",
    "stoney creek",
    "mississauga",
}

ACTIVE_STATUSES = {
    "authorized to open",
    "open",
    "issued",
}

log = get_logger(__name__)


_CITY_SUFFIX_RE = re.compile(
    r"\b(burlington|oakville|hamilton|waterdown|milton|grimsby|stoney creek|mississauga)\b.*$",
    re.I,
)


def _normalize_address(addr: str | None) -> str:
    if not addr:
        return ""
    s = addr.lower()
    s = re.sub(r"[,#.]", " ", s)
    s = re.sub(r"\b(unit|suite|ste|#)\s*[\w-]+\b", " ", s)
    s = _CITY_SUFFIX_RE.sub("", s)  # drop city / province tail
    s = re.sub(r"\bon\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _scrape_current_page(page: Page) -> list[dict]:
    """Extract all data rows from the table on the current page."""
    table = page.locator("table").first
    rows = table.locator("tbody tr").all()
    out = []
    for row in rows:
        cells = row.locator("td").all_inner_texts()
        if len(cells) < 7:
            continue
        licence, city, name, address, postal, status, website = [c.strip() for c in cells[:7]]
        out.append(
            {
                "licence_number": licence or None,
                "city": city,
                "store_name": name,
                "address": address,
                "postal_code": postal,
                "status": status,
                "website": website or None,
            }
        )
    return out


def scrape_all_rows() -> list[dict]:
    """Walk Drupal pagination via ?page=N URL param (0-indexed)."""
    settings = get_settings()
    all_rows: list[dict] = []
    seen_first_per_page: dict[int, str | None] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.playwright_headless)
        context = browser.new_context(user_agent=settings.scrape_user_agent)
        page = context.new_page()

        for page_num in range(0, 50):
            url = f"{LANDING_URL}?page={page_num}"
            log.info("agco_load_page", page=page_num)
            page.goto(url, wait_until="networkidle", timeout=60_000)
            try:
                page.wait_for_selector("table tbody tr", timeout=15_000)
            except Exception:
                log.info("no_table_on_page_stopping", page=page_num)
                break

            rows = _scrape_current_page(page)
            if not rows:
                log.info("empty_page_stopping", page=page_num)
                break

            first_licence = rows[0]["licence_number"]
            if page_num > 0 and first_licence == seen_first_per_page.get(page_num - 1):
                log.info("same_first_row_as_prev_stopping", page=page_num)
                break
            seen_first_per_page[page_num] = first_licence

            log.info("agco_page_scraped", page=page_num, rows=len(rows))
            all_rows.extend(rows)

        context.close()
        browser.close()

    log.info("agco_scrape_complete", total_rows=len(all_rows))
    return all_rows


def save_snapshot(rows: list[dict]) -> Path:
    out_dir = get_settings().data_path / "agco"
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / f"agco_applications_{datetime.now().strftime('%Y%m%d')}.csv"
    pd.DataFrame(rows).to_csv(fname, index=False)
    log.info("agco_snapshot_saved", path=str(fname))
    return fname


def filter_market(rows: list[dict]) -> list[dict]:
    out = [
        r
        for r in rows
        if (r.get("city") or "").strip().lower() in MARKET_CITIES
        and (r.get("status") or "").strip().lower() in ACTIVE_STATUSES
    ]
    log.info("agco_filtered_to_market_active", before=len(rows), after=len(out))
    return out


def match_to_stores(agco_rows: list[dict]) -> list[dict]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT store_id, store_name, address FROM dim_stores")
        ours = cur.fetchall()

    our_addrs = {row[0]: _normalize_address(row[2]) for row in ours}
    our_names = {row[0]: row[1] for row in ours}

    matches: list[dict] = []
    used_store_ids: set[int] = set()

    for row in agco_rows:
        agco_addr_norm = _normalize_address(row["address"])
        if not agco_addr_norm:
            continue

        best = process.extractOne(
            agco_addr_norm,
            our_addrs,
            scorer=fuzz.token_set_ratio,
            score_cutoff=85,
        )
        if not best:
            continue

        _matched_addr, score, sid = best
        if sid in used_store_ids:
            continue
        used_store_ids.add(sid)

        matches.append(
            {
                "store_id": sid,
                "our_name": our_names[sid],
                "score": score,
                **row,
            }
        )

    log.info("agco_matched", count=len(matches), available=len(ours))
    return matches


def update_stores(matches: list[dict]) -> int:
    if not matches:
        return 0

    now = datetime.now(timezone.utc)
    updated = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for m in matches:
            is_active = (m["status"] or "").strip().lower() in ACTIVE_STATUSES
            cur.execute(
                """
                UPDATE dim_stores SET
                    agco_licence_number = COALESCE(NULLIF(%s, ''), agco_licence_number),
                    is_active = COALESCE(%s, is_active),
                    website = COALESCE(NULLIF(%s, ''), website),
                    last_scraped_at = %s
                WHERE store_id = %s
                """,
                (
                    m["licence_number"] or "",
                    is_active,
                    m.get("website") or "",
                    now,
                    m["store_id"],
                ),
            )
            updated += cur.rowcount
    log.info("dim_stores_updated", count=updated)
    return updated


def main() -> int:
    configure_logging()
    with run_logged("agco_retailers") as ctx:
        rows = scrape_all_rows()
        save_snapshot(rows)
        market = filter_market(rows)
        matches = match_to_stores(market)
        updated = update_stores(matches)

        ctx.rows_processed = updated
        ctx.metadata = {
            "total_scraped": len(rows),
            "in_market": len(market),
            "matched_to_our_stores": len(matches),
        }

        log.info(
            "agco_run_done",
            total_scraped=len(rows),
            market_rows=len(market),
            matched_to_our_stores=len(matches),
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
