"""
Daily OCS refresh flow.

Steps:
  1. Scrape OCS Shopify products.json (last 7 days of new arrivals).
  2. Upsert into dim_products.
  3. Insert into fct_ocs_launches.

Schedule: every day at 06:00 ET.
"""

from prefect import flow, get_run_logger

from pipeline.scrapers.ocs_new_arrivals import main as ocs_main


@flow(name="daily-ocs-refresh", log_prints=True)
def daily_ocs_refresh(days: int = 7) -> dict:
    logger = get_run_logger()
    logger.info(f"Starting daily OCS refresh, days={days}")
    inserted = ocs_main(days)
    logger.info(f"OCS refresh complete; new launches inserted: {inserted}")
    return {"new_launches": inserted, "days_window": days}


if __name__ == "__main__":
    daily_ocs_refresh()
