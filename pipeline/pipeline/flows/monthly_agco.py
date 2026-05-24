"""
Monthly AGCO authorization-holders sync.

Walks the AGCO retail-store-applications table (Drupal pagination), filters
to the 35 km Burlington market, fuzzy-matches addresses to dim_stores, and
updates licence numbers / active status / canonical website URLs.

Schedule: first day of each month at 02:00 ET.
"""

from prefect import flow, get_run_logger

from pipeline.scrapers.agco_retailers import main as agco_main


@flow(name="monthly-agco-sync", log_prints=True)
def monthly_agco_sync() -> dict:
    logger = get_run_logger()
    logger.info("Starting monthly AGCO sync")
    agco_main()
    logger.info("AGCO sync complete")
    return {"status": "ok"}


if __name__ == "__main__":
    monthly_agco_sync()
