"""
Weekly HiBuddy store-details refresh.

Visits each store page on HiBuddy and re-extracts the JSON-LD block to
keep dim_stores.latitude / longitude / phone / address current.

Schedule: every Sunday at 03:00 ET.
"""

from prefect import flow, get_run_logger

from pipeline.scrapers.hibuddy_store_details import main as hibuddy_main


@flow(name="weekly-hibuddy-store-details", log_prints=True)
def weekly_hibuddy_details() -> dict:
    logger = get_run_logger()
    logger.info("Starting weekly HiBuddy store-details refresh")
    hibuddy_main()
    logger.info("HiBuddy refresh complete")
    return {"status": "ok"}


if __name__ == "__main__":
    weekly_hibuddy_details()
