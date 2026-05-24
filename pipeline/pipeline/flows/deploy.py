"""
Register every flow with the local Prefect server, attaching a cron schedule.

Run once after installing the Prefect work-pool:

    prefect work-pool create --type process default-process
    uv run python -m pipeline.flows.deploy

Each call to flow.deploy() upserts the deployment — re-running is idempotent.
All schedules use the America/Toronto timezone since OCS / HiBuddy / AGCO
publish on Eastern Time.
"""

from __future__ import annotations

from prefect.client.schemas.schedules import CronSchedule

from pipeline.flows.daily_ocs import daily_ocs_refresh
from pipeline.flows.daily_promo_duration import daily_promo_duration
from pipeline.flows.monthly_agco import monthly_agco_sync
from pipeline.flows.weekly_hibuddy_details import weekly_hibuddy_details

TZ = "America/Toronto"
WORK_POOL = "default-process"


def main():
    daily_ocs_refresh.deploy(
        name="daily-ocs-refresh",
        work_pool_name=WORK_POOL,
        schedules=[CronSchedule(cron="0 6 * * *", timezone=TZ)],
        tags=["scraper", "daily"],
        description="Pull new OCS Shopify products published in the last 7 days.",
    )

    daily_promo_duration.deploy(
        name="daily-promo-duration",
        work_pool_name=WORK_POOL,
        schedules=[CronSchedule(cron="30 6 * * *", timezone=TZ)],
        tags=["transform", "daily"],
        description="Re-derive promo_first_seen / promo_last_seen for every fct_prices row.",
    )

    weekly_hibuddy_details.deploy(
        name="weekly-hibuddy-store-details",
        work_pool_name=WORK_POOL,
        schedules=[CronSchedule(cron="0 3 * * 0", timezone=TZ)],
        tags=["scraper", "weekly"],
        description="Refresh dim_stores.latitude/longitude/phone via HiBuddy JSON-LD.",
    )

    monthly_agco_sync.deploy(
        name="monthly-agco-sync",
        work_pool_name=WORK_POOL,
        schedules=[CronSchedule(cron="0 2 1 * *", timezone=TZ)],
        tags=["scraper", "monthly"],
        description="Sync AGCO authorization status + licence numbers + websites.",
    )

    print("✓ all flows deployed")


if __name__ == "__main__":
    main()
