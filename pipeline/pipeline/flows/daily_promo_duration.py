"""
Daily promo-duration recompute.

Re-derives promo_first_seen / promo_last_seen on every fct_prices row by
walking fct_price_history per (store_id, product_id). Should run after
each daily HiBuddy price refresh once we wire a HiBuddy prices flow.

Schedule: every day at 06:30 ET (after the OCS refresh).
"""

from prefect import flow, get_run_logger

from pipeline.jobs.compute_promo_duration import compute
from pipeline.utils.runs import run_logged


@flow(name="daily-promo-duration", log_prints=True)
def daily_promo_duration() -> dict:
    logger = get_run_logger()
    logger.info("Starting promo-duration recompute")
    with run_logged("compute_promo_duration") as ctx:
        result = compute()
        ctx.rows_processed = result["updated"]
        ctx.metadata = result
    logger.info(f"Promo-duration recompute done: {result}")
    return result


if __name__ == "__main__":
    daily_promo_duration()
