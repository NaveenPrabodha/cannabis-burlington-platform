# Burlington Cannabis — Price Comparison & Store Discovery Platform

A full-stack price comparison and store discovery platform for the cannabis
retail market in Burlington, Ontario (35 km radius). Covers 26 licensed
retailers, 7,500+ OCS catalog products, daily price snapshots, and
licence-verified store profiles.

**Live demo:** http://51.21.167.48 · **API docs:** http://51.21.167.48/docs

---

## Table of contents

- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Data sources](#data-sources)
- [Database schema](#database-schema)
- [Quick start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Setup — macOS / Linux](#setup--macos--linux)
  - [Setup — Windows (PowerShell)](#setup--windows-powershell)
  - [Setup — Windows (WSL2, recommended)](#setup--windows-wsl2-recommended)
  - [Running the stack locally](#running-the-stack-locally)
  - [Local Docker workflow](#local-docker-workflow-all-platforms)
- [Refreshing the data](#refreshing-the-data)
- [Environment variables](#environment-variables)
- [Testing](#testing)
- [Production deployment](#production-deployment)
- [Pipeline schedule](#pipeline-schedule)
- [Observability](#observability)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)
- [License](#license)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Daily / Weekly / Monthly                                                │
│  ───────────────────────                                                 │
│  HiBuddy.ca  →  Playwright scraper  →  store menus + JSON-LD geo         │
│  OCS Shopify →  httpx              →  product catalog + new arrivals     │
│  AGCO        →  Playwright table   →  licence numbers + active status    │
│                                                                          │
│                            │                                             │
│                            ▼                                             │
│             ┌─────────────────────────────┐                              │
│             │   PostgreSQL (star schema)  │                              │
│             │   dim_stores · dim_products │                              │
│             │   fct_prices · fct_price_   │                              │
│             │   history · fct_ocs_        │                              │
│             │   launches · pipeline_runs  │                              │
│             └──────────────┬──────────────┘                              │
│                            │                                             │
│                            ▼                                             │
│             ┌─────────────────────────────┐                              │
│             │   FastAPI  (async, OpenAPI) │                              │
│             │   /stores  /products /deals │                              │
│             │   /search  /featured        │                              │
│             │   /pipeline/freshness       │                              │
│             └──────────────┬──────────────┘                              │
│                            │                                             │
│                            ▼                                             │
│             ┌─────────────────────────────┐                              │
│             │  Next.js 15 + Tailwind +    │                              │
│             │  shadcn/ui + TanStack Query │                              │
│             └─────────────────────────────┘                              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 15 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query |
| Backend | FastAPI · async SQLAlchemy 2.0 · asyncpg · Pydantic v2 · Alembic |
| Database | PostgreSQL 16 (star schema, generated columns, `JSONB`) |
| Pipelines | Python 3.12 · Playwright · httpx · rapidfuzz · structlog |
| Orchestration | systemd timers (production) · manual `uv run` (development) |
| Infra | Docker · docker-compose · nginx · AWS EC2 + RDS Free Tier |
| CI/CD | GitHub Actions · GitHub Container Registry |

---

## Repository layout

```
/
├── backend/             FastAPI service (async SQLAlchemy + Pydantic)
│   ├── app/
│   │   ├── main.py      App entrypoint, CORS, exception handlers
│   │   ├── config.py    Pydantic Settings, reads .env
│   │   ├── database.py  Async engine, session factory
│   │   ├── models/      ORM (Store, Product, Price, PriceHistory, OCSLaunch)
│   │   ├── schemas/     Pydantic response models, drives Swagger
│   │   ├── routers/     Endpoint groupings (stores, products, deals, ...)
│   │   ├── crud/        Query logic, keeps routers thin
│   │   └── utils/       Pagination helper
│   ├── alembic/         Database migrations
│   ├── scripts/         seed_from_csvs.py (one-time bootstrap)
│   └── tests/           pytest smoke tests, 14 endpoint coverage
│
├── frontend/            Next.js 15 (App Router) + TS + Tailwind + shadcn/ui
│   ├── src/app/         Pages: /, /products, /stores, /deals, /search
│   ├── src/components/  Reusable cards, layout, theme, data-freshness footer
│   └── src/lib/         Typed API client, formatting helpers
│
├── pipeline/            Data ingestion + transform jobs
│   ├── pipeline/
│   │   ├── scrapers/    HiBuddy details, OCS new arrivals, AGCO retailers
│   │   ├── jobs/        compute_promo_duration, backfill_description_lang,
│   │   │                rematch_products
│   │   └── utils/       run_logged audit wrapper, structlog config
│   └── data/            Local raw-scrape cache (gitignored)
│
├── infra/               Deployment glue
│   ├── docker-compose.prod.yml   Production compose (pulls prebuilt images)
│   ├── docker-compose.yml        Local dev compose (builds locally)
│   ├── nginx.conf                Reverse proxy config
│   ├── systemd/                  Linux timer + service unit files
│   ├── DEPLOY.md                 AWS deployment guide
│   └── AWS_CLEANUP.md            Teardown guide
│
├── already_done/        Legacy scrapers and the cleaned CSV seed dataset
│   ├── scrapers/        Original step1/step2/step3 scrapers
│   ├── scripts/         Original ETL: clean_data, build_product_matches, ...
│   └── output/          Cleaned CSVs used as the bootstrap dataset
│
├── .github/workflows/   CI (lint + tests) and CD (build images, deploy)
└── task/                Original brief + earlier exercise submission
```

---

## Data sources

| Source | What we extract | Cadence |
|---|---|---|
| **HiBuddy.ca** | Store list, daily product menus + prices, JSON-LD lat/lng, phone, address | Daily |
| **Ontario Cannabis Store** (Shopify API) | Canonical product catalog (~7,500 SKUs), THC/CBD, images, descriptions, new arrivals via `published_at` | Daily |
| **AGCO Authorization Holders** (HTML table) | Licence numbers, "Authorized to Open" status, official store address | Monthly |
| **Leafly / Weedmaps** | Hours of operation *(deferred — see [Known limitations](#known-limitations))* | TBD |

---

## Database schema

Star schema. Two dimension tables, three fact tables, one audit table.

```
dim_stores         dim_products             fct_prices              fct_price_history
───────────        ─────────────            ─────────────────       ─────────────────
store_id (PK)      product_id (PK)          fact_id (PK)            history_id (PK)
store_name         name                     store_id (FK) ─┐        store_id (FK)
normalized_name    normalized_name          product_id (FK)─┐       product_id (FK)
address            brand                    scraped_date    │       scraped_date
phone              category, subcategory    regular_price   │       regular_price
website            size                     sale_price      │       sale_price
hibuddy_slug       description              discount_percent│       in_stock
hibuddy_store_id   description_lang         typical_nearby  │
agco_licence_no    image_url                in_stock        │       fct_ocs_launches
is_active          price (OCS MSRP)         promo_first_seen│       ─────────────────
hours_json         thc_min/max              promo_last_seen │       launch_id (PK)
owner_name         cbd_min/max              promo_duration_ │       product_id (FK)
owner_company      last_scraped_at             days  (generated)    launch_date
latitude           created_at                                       name, brand, ...
longitude                                                            ocs_price, url
last_scraped_at

pipeline_runs
─────────────
run_id (PK)
job_name
status              (running | success | failed)
started_at
finished_at
duration_s
rows_processed
error_message
metadata_json
```

Notes:

- **`fct_prices`** holds the latest snapshot per `(store, product)`.
- **`fct_price_history`** is append-only — every scrape adds new rows.
- **`promo_duration_days`** is a `GENERATED ALWAYS AS (promo_last_seen -
  promo_first_seen) STORED` column. The pipeline only updates the two
  timestamp columns; the duration is computed automatically.
- **`pipeline_runs`** is the observability table — every scrape and job
  writes a row here. The `/api/pipeline/freshness` endpoint reads from it
  so the UI footer can show "Last refreshed N hours ago."

---

## Quick start

### Prerequisites

You need three things installed locally regardless of OS:

| Tool | Purpose | Version |
|---|---|---|
| **Python** | Backend + pipelines | 3.12 |
| **Node.js** | Frontend | 20+ |
| **PostgreSQL** | Database | 16 |
| **uv** | Python package manager | latest |
| **Git** | Source control | any |

Docker is **optional** for local dev but recommended if you don't want
to install Postgres directly.

---

### Setup — macOS / Linux

Install prerequisites via Homebrew (macOS) or your distro's package
manager:

```bash
# macOS
brew install python@3.12 node postgresql@16 uv git
brew services start postgresql@16

# Ubuntu / Debian
sudo apt update && sudo apt install -y python3.12 python3.12-venv \
  nodejs npm postgresql-16 git
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone and bootstrap the database:

```bash
git clone https://github.com/<your-org>/cannabis-burlington-platform.git
cd cannabis-burlington-platform

# Create the database
psql postgres -c "CREATE DATABASE cannabis_analysis;"

# Backend deps + schema
cd backend
cp .env.example .env       # edit DATABASE_URL if your local creds differ
uv sync
uv run alembic upgrade head

# Seed from bundled CSVs
uv run python scripts/seed_from_csvs.py

# Pipeline deps + Playwright browser
cd ../pipeline
cp .env.example .env
uv sync
uv run playwright install chromium

# Frontend deps
cd ../frontend
cp .env.example .env.local
npm install
```

---

### Setup — Windows (PowerShell)

Install prerequisites. Open **PowerShell as Administrator** for the first
two commands, then a normal PowerShell window for the rest.

```powershell
# Install winget packages
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
winget install PostgreSQL.PostgreSQL.16
winget install Git.Git
winget install astral-sh.uv
```

After installing, close and reopen PowerShell so `PATH` updates take
effect. Verify:

```powershell
python --version    # Python 3.12.x
node --version      # v20.x.x
psql --version      # psql (PostgreSQL) 16.x
uv --version
git --version
```

If `psql` is not on `PATH`, add `C:\Program Files\PostgreSQL\16\bin` to
your **System Environment Variables → Path**.

Clone and bootstrap:

```powershell
git clone https://github.com/<your-org>/cannabis-burlington-platform.git
cd cannabis-burlington-platform

# Create the database (uses the default 'postgres' superuser — you set the
# password during PostgreSQL install). It will prompt for that password.
psql -U postgres -c "CREATE DATABASE cannabis_analysis;"

# Backend deps + schema
cd backend
copy .env.example .env
notepad .env       # edit DATABASE_URL to include your postgres password
uv sync
uv run alembic upgrade head

# Seed from bundled CSVs
uv run python scripts\seed_from_csvs.py

# Pipeline deps + Playwright browser
cd ..\pipeline
copy .env.example .env
uv sync
uv run playwright install chromium

# Frontend deps
cd ..\frontend
copy .env.example .env.local
npm install
```

**Windows .env path:** When editing `backend/.env`, the format is the same
as on macOS / Linux. Example with a Windows-installed Postgres:

```
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/cannabis_analysis
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/cannabis_analysis
CORS_ORIGINS=http://localhost:3000
ENV=local
APP_VERSION=0.1.0
```

---

### Setup — Windows (WSL2, recommended)

If you'd rather use a Linux environment on Windows (recommended for
parity with production), install **WSL2** with Ubuntu:

```powershell
# In an elevated PowerShell:
wsl --install -d Ubuntu
# Reboot when prompted, then follow Ubuntu's first-run setup
```

Once inside the Ubuntu shell, follow the [macOS / Linux setup](#setup--macos--linux)
instructions. Open the project in VS Code via the **Remote - WSL**
extension for the best DX.

---

### Running the stack locally

After setup, you need three terminals:

**Terminal 1 — Backend** (`http://localhost:8000`, Swagger at `/docs`):

```bash
# macOS / Linux / WSL
cd backend && uv run uvicorn app.main:app --reload
```

```powershell
# Windows PowerShell
cd backend
uv run uvicorn app.main:app --reload
```

**Terminal 2 — Frontend** (`http://localhost:3000`):

```bash
cd frontend && npm run dev
```

**Terminal 3 — Pipelines** (only when you want to refresh data):

```bash
cd pipeline
# Daily — fetch latest OCS catalog
uv run python -m pipeline.scrapers.ocs_new_arrivals --days 7
```

Open `http://localhost:3000` in your browser. You should see the homepage
with featured products and hottest deals.

---

### Local Docker workflow (all platforms)

If you prefer not to install Postgres locally, use Docker. This is
identical on macOS, Linux, and Windows (with Docker Desktop installed).

```bash
cd infra
cp .env.example .env       # edit if needed; defaults work for local Docker
docker compose up -d
```

That brings up Postgres, the backend, the frontend, and nginx. Browse to
`http://localhost`.

To run pipelines against the Dockerized Postgres, set:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cannabis_analysis
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cannabis_analysis
```

in `pipeline/.env`, then run scrapers normally via `uv run`.

---

## Refreshing the data

All scrapers are idempotent — re-running won't duplicate data. Each
records a row in `pipeline_runs` for audit.

```bash
cd pipeline

# Daily — new OCS launches + dim_products refresh
uv run python -m pipeline.scrapers.ocs_new_arrivals --days 30

# Weekly — HiBuddy lat/lng, phone, address (uses Playwright)
uv run python -m pipeline.scrapers.hibuddy_store_details

# Monthly — AGCO licence status (uses Playwright)
uv run python -m pipeline.scrapers.agco_retailers

# After any HiBuddy price refresh — recompute promo durations
uv run python -m pipeline.jobs.compute_promo_duration

# One-time — improve product matching after fresh OCS pulls
uv run python -m pipeline.jobs.rematch_products

# One-time — tag products as English vs French (run after large OCS imports)
uv run python -m pipeline.jobs.backfill_description_lang
```

In production, these run automatically via systemd timers — see
[Pipeline schedule](#pipeline-schedule).

---

## Environment variables

### `backend/.env`

| Variable | Required | Example | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | `postgresql+asyncpg://postgres:pass@localhost:5432/cannabis_analysis` | Async URL for the app |
| `SYNC_DATABASE_URL` | yes | `postgresql+psycopg2://postgres:pass@localhost:5432/cannabis_analysis` | Sync URL for Alembic |
| `CORS_ORIGINS` | yes | `http://localhost:3000` | Comma-separated allowed origins |
| `ENV` | no | `local` / `prod` | Surfaced in `/health` |
| `APP_VERSION` | no | `0.1.0` | Surfaced in `/health` |
| `LOG_LEVEL` | no | `INFO` | structlog level |

### `pipeline/.env`

Same `DATABASE_URL` + `SYNC_DATABASE_URL` as the backend. The pipeline
modules read these to write directly into Postgres.

### `frontend/.env.local`

| Variable | Required | Example | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | yes | `http://localhost:8000` | Where the browser fetches API data |

In production this is `http://<EC2_IP>/api` because nginx strips the
`/api/` prefix and forwards to the backend.

---

## Testing

```bash
# Backend smoke tests (14 endpoints, hits a test database)
cd backend
uv run pytest

# Frontend lint + type-check
cd frontend
npm run lint
npx tsc --noEmit
```

On Windows, the same commands work in PowerShell or via WSL2.

---

## Production deployment

The platform runs on AWS Free Tier ($0/month for the first 12 months):

| Component | AWS service | Tier |
|---|---|---|
| Web host | EC2 t3.micro (Amazon Linux 2023) | 750 hrs/mo free |
| Database | RDS db.t3.micro Postgres 16 | 750 hrs/mo + 20 GB free |
| Container images | GitHub Container Registry | free for public repos |
| CI | GitHub Actions | 2,000 min/mo free |

The EC2 host runs three containers via `docker compose`:

1. **nginx** — reverse proxy on port 80
2. **frontend** — Next.js (port 3000, internal)
3. **backend** — FastAPI (port 8000, internal)

Plus four **systemd timers** that fire the data scrapers on a schedule.

Images are built by GitHub Actions on every push to `main` (see
`.github/workflows/docker-images.yml`) and pushed to GHCR. The EC2 host
only pulls — it never builds, because Next.js builds require 2–3 GB RAM
and t3.micro has 1 GB.

**Full step-by-step deployment guide:** [infra/DEPLOY.md](infra/DEPLOY.md)

**Teardown guide:** [infra/AWS_CLEANUP.md](infra/AWS_CLEANUP.md)

---

## Pipeline schedule

In production, these unit files in `infra/systemd/` run on the EC2 host:

| Timer | Schedule | What it does |
|---|---|---|
| `scrape-ocs.timer` | Daily 06:00 UTC | Fetches OCS catalog, upserts `dim_products`, inserts new `fct_ocs_launches` |
| `promo-duration.timer` | Daily 06:30 UTC | Recomputes `promo_first_seen` / `promo_last_seen` on `fct_prices` |
| `scrape-hibuddy.timer` | Sundays 03:00 UTC | Refreshes `dim_stores.latitude`, `longitude`, `phone`, `address` |
| `scrape-agco.timer` | Monthly 1st 02:00 UTC | Syncs AGCO licence numbers + active status |

Check next run times on the EC2 host:

```bash
systemctl list-timers --all | grep -E 'scrape|promo'
```

---

## Observability

Every pipeline run inserts a row into `pipeline_runs` with status,
duration, and rows processed:

```sql
SELECT run_id, job_name, status, started_at, finished_at, rows_processed
FROM pipeline_runs
ORDER BY run_id DESC
LIMIT 10;
```

The frontend reads `/api/pipeline/freshness` and shows the last
successful run for each job in the page footer.

For container-level logs (production):

```bash
cd infra
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

For pipeline-level logs (production):

```bash
sudo journalctl -u scrape-ocs.service --since "24 hours ago"
tail -f /var/log/cannabis-pipeline.log
```

---

## Troubleshooting

| Symptom | Where to look |
|---|---|
| `/api/health` returns `{"db_ok": false}` | RDS credentials or security group — check `DATABASE_URL` in `.env`, confirm EC2's SG is allow-listed on the RDS security group |
| Frontend shows empty product grid | `curl http://localhost/api/products` — if it returns `[]`, the seed didn't run; if it 404s, nginx routing is broken |
| Scraper hasn't run on schedule | `systemctl list-timers \| grep <name>` — is it enabled? Then `journalctl -u <service-name>` for the last failure |
| `next build` runs out of memory | Don't build on t3.micro — that's why we use GHCR. Trigger the `docker-images.yml` workflow on GitHub instead |
| Windows: `uv` not found after install | Close PowerShell completely and reopen. The installer updates `PATH` for new sessions only |
| Windows: `psql` not found | Add `C:\Program Files\PostgreSQL\16\bin` to System `Path` |
| Windows: `playwright install` fails | Run PowerShell **as Administrator** for the install step (Playwright needs to register browsers) |
| WSL2: Docker Desktop integration broken | In Docker Desktop → Settings → Resources → WSL Integration → enable your distro |

---

## Known limitations

1. **Store hours** are not yet populated. AGCO doesn't publish hours,
   HiBuddy store pages don't expose them, and the OCS API has no concept
   of stores. A Leafly + Weedmaps Playwright scraper is the planned next
   step. Until then, `dim_stores.hours_json` is NULL and the frontend
   shows "—" for hours.

2. **Owner names** (`dim_stores.owner_name`) are NULL. AGCO marks
   operator identity as "Restricted" for privacy — no programmatic source
   exists. `owner_company` (the licence holder) can be added later via
   per-store AGCO records requests.

3. **~5,800 OCS products are not stocked locally.** This isn't a bug —
   it's the real coverage. The OCS catalog includes 7,500+ SKUs, but
   Burlington's 26 stores only carry ~1,800 of them. By default
   `/products` hides these (the "Available locally only" filter is on by
   default).

4. **OCS publishes products bilingually.** Each SKU appears twice in the
   Shopify API — one row with English `body_html`, one with French. We
   detect the language (`backfill_description_lang` job) and let the user
   filter. By default we show only English-described products.

5. **Promo duration** = 0 days for everything until we accumulate multiple
   daily snapshots. The mechanism is wired (`fct_price_history` +
   `compute_promo_duration`); it just needs time to populate.

6. **Production frontend bakes the API URL at build time** because
   `NEXT_PUBLIC_*` variables are embedded into the JavaScript bundle by
   Next.js. If the EC2 public IP changes, the frontend image must be
   rebuilt. Workaround: allocate an AWS Elastic IP (free while attached).

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

Built on the technical-exercise foundation in `task/`. Data is publicly
scraped from HiBuddy.ca, the Ontario Cannabis Store, and AGCO. This
project is not affiliated with any of those organizations.
