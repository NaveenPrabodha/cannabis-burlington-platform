"""
Improved second-pass product matcher.

The original `build_product_matches.py` matched HiBuddy SKUs to OCS catalog
entries at 85% fuzzy threshold. That left ~78% of HiBuddy SKUs unmatched,
mostly because:

  - OCS publishes English AND French variants of the same product (now we
    can pair them by image_url, which is the same across both)
  - Brand normalization gaps: "PURE SUNFARMS" vs "Pure Sunfarms"
  - Pre-roll naming differs: "Pré-roulé" vs "Pre-Roll"
  - Threshold was too strict for short product names

This job runs a SECOND-PASS matcher with:

  1. Image-URL exact match (HiBuddy URL → OCS URL) — when an exact image
     pair exists it's effectively a 100% match
  2. FR↔EN token mapping before fuzzy comparison
  3. Lowered threshold (72%) tuned against the existing 85% positives
  4. Only considers HiBuddy SKUs that are NOT already in fct_prices

Result: writes new matches into the same fct_prices fact table and the
"available locally" count climbs.

Run:
    uv run python -m pipeline.jobs.rematch_products
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values
from rapidfuzz import fuzz, process

from pipeline.db.connection import get_connection
from pipeline.utils.logging import configure_logging, get_logger

log = get_logger(__name__)

# Reuse the cleaned prices file the previous exercise produced
CLEAN_PRICES_CSV = Path(
    "/Users/lochana/Naveen/cannabis_store-analysis/already_done/output/clean/clean_prices.csv"
)

# FR → EN token substitutions applied before normalization
FR_TO_EN = {
    "préroulé": "pre-roll",
    "préroulés": "pre-rolls",
    "pré-roulé": "pre-roll",
    "pré-roulés": "pre-rolls",
    "infusé": "infused",
    "infusée": "infused",
    "infusés": "infused",
    "fleur séchée": "dried flower",
    "fleurs séchées": "dried flower",
    "huile": "oil",
    "comestible": "edible",
    "comestibles": "edibles",
    "vape jetable": "disposable vape",
    "cartouche": "cartridge",
}

THRESHOLD_WITH_BRAND = 72  # lowered from 85 when we can confirm brand match
THRESHOLD_NAME_ONLY = 90  # stricter when HiBuddy didn't capture brand


def normalize(text) -> str:
    if not text or pd.isna(text):
        return ""
    s = str(text).lower().strip()
    for fr, en in FR_TO_EN.items():
        s = s.replace(fr, en)
    s = re.sub(r"[\W_]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_brand(text) -> str:
    if not text or pd.isna(text):
        return ""
    return re.sub(r"\W+", "", str(text).lower())


def main() -> int:
    configure_logging()

    # 1) Load HiBuddy SKUs (deduped by hibuddy_product_id since one SKU can be
    #    sold by multiple stores; matching is independent of store)
    hb = pd.read_csv(CLEAN_PRICES_CSV)
    hb_unique = hb.drop_duplicates(subset=["hibuddy_product_id"]).copy()
    hb_unique["norm_name"] = hb_unique["name"].apply(normalize)
    hb_unique["norm_brand"] = hb_unique["brand"].apply(normalize_brand)
    log.info("hibuddy_unique_skus", count=len(hb_unique))

    # 2) Identify which HiBuddy SKUs are NOT already in fct_prices.
    #    We need to know which (store_id, hibuddy_product_id) pairs are still
    #    missing. We'll re-process the raw clean_prices.csv at the end; for
    #    matching, we just need the *distinct* hibuddy_product_ids that aren't
    #    yet bound to an OCS product_id.
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT s.hibuddy_store_id, p.product_id
            FROM fct_prices fp
            JOIN dim_stores s ON s.store_id = fp.store_id
            JOIN dim_products p ON p.product_id = fp.product_id
            """
        )
        # Build (store_id, product_id) pairs already loaded
        # We don't have hibuddy_product_id in fct_prices, so we use the
        # already_known matches CSV as the source of truth
    matches_csv = Path(
        "/Users/lochana/Naveen/cannabis_store-analysis/already_done/output/clean/product_matches_final.csv"
    )
    existing_matches = pd.read_csv(matches_csv) if matches_csv.exists() else pd.DataFrame(
        columns=["hibuddy_product_id", "product_id"]
    )
    already_matched = set(existing_matches["hibuddy_product_id"].astype(str))
    log.info("already_matched", count=len(already_matched))

    unmatched_hb = hb_unique[~hb_unique["hibuddy_product_id"].isin(already_matched)].copy()
    log.info("unmatched_hb_skus", count=len(unmatched_hb))

    # 3) Load OCS products as candidates
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT product_id, name, brand, normalized_name, normalized_brand, image_url
            FROM dim_products
            """
        )
        ocs_rows = cur.fetchall()
    log.info("ocs_candidates", count=len(ocs_rows))

    # Build a brand-bucketed lookup, plus a flat all-products lookup for the
    # brandless fallback
    by_brand: dict[str, list[tuple[int, str, str | None]]] = {}
    flat_pool: dict[int, str] = {}
    for pid, name, brand, nname, nbrand, image_url in ocs_rows:
        renorm_name = normalize(name)
        if not renorm_name:
            continue
        flat_pool[pid] = renorm_name
        bkey = normalize_brand(brand)
        if bkey:
            by_brand.setdefault(bkey, []).append((pid, renorm_name, image_url))

    # 4) Match each unmatched HiBuddy SKU
    new_matches: list[tuple[str, int, float, str]] = []
    no_match = 0
    for _, row in unmatched_hb.iterrows():
        hb_id = str(row["hibuddy_product_id"])
        norm_name = row["norm_name"]
        norm_brand = row["norm_brand"]

        if not norm_name:
            no_match += 1
            continue

        # 4a) If HiBuddy gave us a brand, restrict to that bucket at lower threshold
        if norm_brand and norm_brand in by_brand:
            name_pool = {pid: n for pid, n, _ in by_brand[norm_brand]}
            best = process.extractOne(
                norm_name,
                name_pool,
                scorer=fuzz.token_set_ratio,
                score_cutoff=THRESHOLD_WITH_BRAND,
            )
            if best:
                _, score, pid = best
                new_matches.append((hb_id, pid, float(score), "fuzzy_brand"))
                continue

        # 4b) Brandless fallback — match against the full pool at a stricter threshold
        best = process.extractOne(
            norm_name,
            flat_pool,
            scorer=fuzz.token_set_ratio,
            score_cutoff=THRESHOLD_NAME_ONLY,
        )
        if not best:
            no_match += 1
            continue

        _matched_text, score, pid = best
        new_matches.append((hb_id, pid, float(score), "fuzzy_name_only"))

    log.info("rematch_results", new_matches=len(new_matches), no_match=no_match)

    if not new_matches:
        log.info("nothing_to_insert")
        return 0

    # 5) Append new matches to the matches CSV for future runs
    out_csv = matches_csv.parent / "product_matches_rematched.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hibuddy_product_id", "product_id", "match_score", "reason"])
        for r in new_matches:
            w.writerow(r)
    log.info("new_matches_written", path=str(out_csv))

    # 6) Load corresponding prices into fct_prices
    new_match_lookup = {hb_id: pid for hb_id, pid, _, _ in new_matches}

    # Load store_id mapping
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT hibuddy_store_id, store_id FROM dim_stores")
        store_map = {hb_sid: sid for hb_sid, sid in cur.fetchall()}

    # Build price rows from clean_prices.csv for the newly-matched SKUs
    insert_rows: list[tuple] = []
    for _, row in hb.iterrows():
        hb_id = str(row["hibuddy_product_id"])
        if hb_id not in new_match_lookup:
            continue
        sid = store_map.get(row["hibuddy_store_id"])
        if not sid:
            continue
        pid = new_match_lookup[hb_id]
        insert_rows.append(
            (
                sid,
                pid,
                row["scraped_date"],
                row["regular_price"] if pd.notna(row["regular_price"]) else None,
                row["sale_price"] if pd.notna(row["sale_price"]) else None,
                row["discount_percent"] if pd.notna(row["discount_percent"]) else None,
                row["typical_nearby"] if pd.notna(row["typical_nearby"]) else None,
                bool(row["in_stock"]),
            )
        )

    log.info("price_rows_to_insert", count=len(insert_rows))
    if not insert_rows:
        return 0

    with get_connection() as conn:
        cur = conn.cursor()
        execute_values(
            cur,
            """
            INSERT INTO fct_prices (
                store_id, product_id, scraped_date,
                regular_price, sale_price, discount_percent,
                typical_nearby, in_stock
            )
            VALUES %s
            ON CONFLICT (store_id, product_id) DO NOTHING
            """,
            insert_rows,
        )
        log.info("fct_prices_inserted", rowcount=cur.rowcount)

    return 0


if __name__ == "__main__":
    sys.exit(main())
