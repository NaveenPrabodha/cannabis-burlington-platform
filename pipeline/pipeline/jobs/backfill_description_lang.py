"""
One-time backfill: detect language of every dim_products.description
and write the result to dim_products.description_lang.

Usage:
    uv run python -m pipeline.jobs.backfill_description_lang
"""

from __future__ import annotations

import sys

from psycopg2.extras import execute_values

from pipeline.db.connection import get_connection
from pipeline.utils.lang import detect_language
from pipeline.utils.logging import configure_logging, get_logger

log = get_logger(__name__)


def main() -> int:
    configure_logging()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT product_id, description FROM dim_products WHERE description IS NOT NULL"
        )
        rows = cur.fetchall()

    log.info("backfill_start", rows=len(rows))

    updates: list[tuple[int, str | None]] = []
    counts = {"en": 0, "fr": 0, "unknown": 0}
    for pid, desc in rows:
        lang = detect_language(desc)
        counts[lang or "unknown"] += 1
        updates.append((pid, lang))

    with get_connection() as conn:
        cur = conn.cursor()
        execute_values(
            cur,
            """
            UPDATE dim_products AS d SET description_lang = v.lang
            FROM (VALUES %s) AS v(product_id, lang)
            WHERE d.product_id = v.product_id
            """,
            updates,
            template="(%s, %s)",
        )

    log.info(
        "backfill_done",
        en=counts["en"],
        fr=counts["fr"],
        unknown=counts["unknown"],
        total=len(rows),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
