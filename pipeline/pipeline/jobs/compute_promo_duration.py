"""
Promo-duration computation job.

Runs after every HiBuddy daily refresh. For each (store_id, product_id) in
fct_price_history, finds the most recent **contiguous run** of dates where
sale_price IS NOT NULL, then writes:

  fct_prices.promo_first_seen = earliest date in that run
  fct_prices.promo_last_seen  = latest date in that run

The generated column promo_duration_days = last - first kicks in automatically.

Notes:
  - "Contiguous" allows up to MAX_GAP_DAYS days of missing observations (a
    site/scrape glitch shouldn't end a promo).
  - If the product has never been on sale, both fields stay NULL.
  - If the product is on sale today, the run extends to today's date.
  - If the most recent run ended in the past, we still record that historical
    promo (a "Cancelled promo" view could surface it on the frontend later).

Run:
    uv run python -m pipeline.jobs.compute_promo_duration
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, timedelta

from psycopg2.extras import execute_values

from pipeline.db.connection import get_connection
from pipeline.utils.logging import configure_logging, get_logger
from pipeline.utils.runs import run_logged

MAX_GAP_DAYS = 2  # tolerate scrape gaps within a promo run

log = get_logger(__name__)


def _compute_latest_run(observations: list[tuple[date, bool]]) -> tuple[date, date] | None:
    """
    `observations` is a chronologically sorted list of (scraped_date, on_sale).
    Returns (first_seen, last_seen) of the most recent on-sale run, or None.
    """
    runs: list[tuple[date, date]] = []
    cur_start: date | None = None
    cur_end: date | None = None
    last_seen: date | None = None

    for d, on_sale in observations:
        if on_sale:
            if cur_start is None:
                cur_start = d
                cur_end = d
            else:
                # Extend if within MAX_GAP_DAYS, else close run + start new
                if (d - cur_end).days <= MAX_GAP_DAYS + 1:
                    cur_end = d
                else:
                    runs.append((cur_start, cur_end))
                    cur_start = d
                    cur_end = d
        else:
            if cur_start is not None:
                runs.append((cur_start, cur_end))
                cur_start = None
                cur_end = None
        last_seen = d

    if cur_start is not None:
        runs.append((cur_start, cur_end))

    if not runs:
        return None
    return runs[-1]


def compute() -> dict[str, int]:
    log.info("promo_duration_start")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT store_id, product_id, scraped_date,
                   (sale_price IS NOT NULL) AS on_sale
            FROM fct_price_history
            ORDER BY store_id, product_id, scraped_date
            """
        )
        history = cur.fetchall()

    log.info("history_rows_loaded", count=len(history))

    grouped: dict[tuple[int, int], list[tuple[date, bool]]] = defaultdict(list)
    for store_id, product_id, scraped_date, on_sale in history:
        grouped[(store_id, product_id)].append((scraped_date, bool(on_sale)))

    updates: list[tuple] = []
    no_sale = 0
    for (sid, pid), obs in grouped.items():
        run = _compute_latest_run(obs)
        if run is None:
            no_sale += 1
            continue
        updates.append((sid, pid, run[0], run[1]))

    if not updates:
        log.info("no_promos_to_update")
        return {"groups": len(grouped), "no_sale": no_sale, "updated": 0}

    with get_connection() as conn:
        cur = conn.cursor()
        # Bulk update via VALUES join — efficient for 1000s of rows
        execute_values(
            cur,
            """
            UPDATE fct_prices AS fp SET
                promo_first_seen = v.first_seen,
                promo_last_seen = v.last_seen
            FROM (VALUES %s) AS v(store_id, product_id, first_seen, last_seen)
            WHERE fp.store_id = v.store_id AND fp.product_id = v.product_id
            """,
            updates,
            template="(%s, %s, %s, %s)",
        )
        rowcount = cur.rowcount

    log.info(
        "promo_duration_done",
        groups=len(grouped),
        groups_with_sale=len(updates),
        no_sale=no_sale,
        fct_prices_rows_updated=rowcount,
    )
    return {
        "groups": len(grouped),
        "no_sale": no_sale,
        "updated": rowcount,
    }


if __name__ == "__main__":
    configure_logging()
    with run_logged("compute_promo_duration") as ctx:
        result = compute()
        ctx.rows_processed = result["updated"]
        ctx.metadata = result
        print(result)
    sys.exit(0)
