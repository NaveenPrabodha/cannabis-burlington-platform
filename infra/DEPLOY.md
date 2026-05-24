# AWS Free Tier deployment — prebuilt-image edition

**Single EC2 host, but the host never compiles anything.** All Docker images
are built by GitHub Actions and pulled from GitHub Container Registry (ghcr.io).
This is the fix for the t3.micro OOM during `next build` — the host now only
runs `docker compose pull && docker compose up`.

If you already have the failing EC2 instance up, see
[AWS_CLEANUP.md](./AWS_CLEANUP.md) to terminate it first.

---

## Architecture

```
┌──────────────── GitHub ────────────────┐         ┌──────────── AWS ─────────────┐
│                                        │         │                              │
│  push to main                          │         │  EC2 t3.micro (1 GB RAM)     │
│        │                               │         │   ┌──────────────────────┐   │
│        ▼                               │         │   │  nginx :80           │   │
│  GitHub Actions builds Docker images   │ ──pull→ │   │   ↓                  │   │
│  → ghcr.io/<you>/cannabis-backend      │         │   │  backend:8000        │   │
│  → ghcr.io/<you>/cannabis-frontend     │         │   │  frontend:3000       │   │
│                                        │         │   └──────────────────────┘   │
│  Cron-scheduled scraper runs           │         │                              │
│  ssh into EC2 → docker compose pull    │         │  systemd timers              │
│                                        │         │   ↓ daily/weekly/monthly     │
└────────────────────────────────────────┘         │   ↓ run scrapers as oneshot  │
                                                   │                              │
                                                   │  RDS db.t3.micro (Postgres)  │
                                                   └──────────────────────────────┘
```

**Why this is stable on t3.micro:** the only memory-hungry step
(`next build`) now runs on GitHub's free 4-core / 16 GB Ubuntu runners.
Runtime on EC2 needs ~500 MB total — comfortable inside 1 GB.

---

## What stays in Free Tier (12 months from account creation)

| Service | Free allowance | We use | Cost after free tier |
|---|---|---|---|
| EC2 t3.micro | 750 hrs/mo (always-on covered) | always-on | ~$8/mo |
| RDS db.t3.micro | 750 hrs + 20 GB | < 1 GB | ~$15/mo |
| S3 | 5 GB + 20k GET + 2k PUT | scrape cache only (~50 MB) | ~$0.50/mo |
| EBS gp3 | 30 GB | 20 GB | ~$1.60/mo |
| Outbound data | 100 GB/mo | tiny | $0.09/GB |
| **GitHub Container Registry** | unlimited for public repos | always | $0 |
| **GitHub Actions** | 2,000 min/mo private, unlimited public | ~10 min/build | $0 |
| **Total inside free tier** | | | **$0/mo** |

**After 12 months**: ~$25–30/mo if you keep everything. Cut to ~$0 by moving
DB to **Neon** (free 0.5 GB Postgres) and the EC2 to a smaller spot — see the
"After free tier" section at the bottom.

---

## Prerequisites

- AWS account with Free Tier still active
- GitHub repo (this one — public so GHCR + Actions stay free)
- SSH client (you already have one — Mac terminal works fine)

---

## One-time setup

### 1. Provision RDS Postgres

AWS Console → Aurora & RDS → Create database → PostgreSQL

| Field | Value |
|---|---|
| Templates | Free tier |
| DB instance class | db.t3.micro |
| Storage | 20 GB gp3 |
| DB instance identifier | `cannabis-db` |
| Master username | `postgres` |
| Master password | *(generate, save in 1Password)* |
| Public access | **No** (keep private to the VPC) |
| VPC security group | new → `rds-cannabis` |
| Initial database name | `cannabis_analysis` |

Wait ~5 min for it to come up. Copy the **endpoint** (looks like
`cannabis-db.abc123.ca-central-1.rds.amazonaws.com`).

### 2. Provision EC2

AWS Console → EC2 → Launch instance

| Field | Value |
|---|---|
| Name | `cannabis-host` |
| AMI | Amazon Linux 2023 |
| Instance type | `t3.micro` |
| Key pair | new → `cannabis-key.pem` (download immediately) |
| Network | default VPC + public subnet, auto-assign public IPv4 |
| Security group | new → `ec2-cannabis` — inbound: SSH 22 from your IP, HTTP 80 from anywhere, HTTPS 443 from anywhere |
| Storage | 20 GB gp3 |
| Advanced details → User data | paste contents of [`user-data.sh`](./user-data.sh) |

The user-data installs Docker + Compose plugin + 2 GB swap on first boot — no
manual setup needed when the instance starts.

### 3. Allow EC2 → RDS Postgres traffic

RDS security group `rds-cannabis` → Inbound rules → Add rule:

| Type | Port | Source |
|---|---|---|
| PostgreSQL | 5432 | `ec2-cannabis` (the SG itself, not an IP) |

### 4. Push images to GHCR

These build automatically on the next push to `main` via
[.github/workflows/docker-images.yml](../.github/workflows/docker-images.yml).
Trigger the first build now:

```bash
# From your laptop, after the GitHub repo Settings → Actions → Variables
# add PUBLIC_API_BASE_URL = http://<EC2-PUBLIC-IP>  (baked into frontend at build)
git commit --allow-empty -m "trigger image build"
git push
```

Watch it in the Actions tab — first build ~5 min, subsequent ~1 min (cached).

Visibility check:
GitHub → your repo → Packages → you'll see `cannabis-backend` and
`cannabis-frontend`. **Make them public** (Settings → Change visibility →
Public) so EC2 can pull without auth.

### 5. SSH in and bootstrap

```bash
chmod 400 ~/Downloads/cannabis-key.pem
ssh -i ~/Downloads/cannabis-key.pem ec2-user@<EC2-PUBLIC-IP>
```

Inside EC2:

```bash
# Clone (only for config files — code lives in the images)
git clone https://github.com/DKLOCHANA/cannabis-burlington-platform.git
cd cannabis-burlington-platform/infra

# Configure
cp .env.example .env
nano .env       # fill BACKEND_DATABASE_URL with the RDS endpoint
                # fill PUBLIC_API_BASE_URL with http://<EC2-PUBLIC-IP>
                # fill CORS_ORIGINS with http://<EC2-PUBLIC-IP>
                # fill GITHUB_USER with dklochana
```

### 6. Apply schema + seed data (one-time)

```bash
# Schema migrations — run inside a throwaway python container
docker run --rm --network host \
  -e DATABASE_URL="postgresql+asyncpg://postgres:<PASSWORD>@<RDS-HOST>:5432/cannabis_analysis" \
  -v ~/cannabis-burlington-platform/backend:/app -w /app \
  python:3.12-slim \
  bash -c "pip install -q uv && uv sync && uv run alembic upgrade head"

# Seed bundled CSVs (one-time, ~30 s)
PGHOST=<RDS-HOST> PGUSER=postgres PGPASSWORD=<PASSWORD> PGDATABASE=cannabis_analysis \
docker run --rm --network host \
  -e PGHOST -e PGUSER -e PGPASSWORD -e PGDATABASE \
  -v ~/cannabis-burlington-platform:/app -w /app/already_done/scripts \
  python:3.12-slim \
  bash -c "pip install -q psycopg2-binary pandas && python load_to_db.py"
```

### 7. Start the stack

```bash
cd ~/cannabis-burlington-platform/infra

# Pull prebuilt images (no compilation — just docker pull)
docker compose -f docker-compose.prod.yml pull

# Run
docker compose -f docker-compose.prod.yml up -d

# Verify
docker compose ps
curl -sf http://localhost/health        # 200 OK
```

Visit `http://<EC2-PUBLIC-IP>/` — homepage.
Visit `http://<EC2-PUBLIC-IP>/docs` — Swagger.

### 8. Install scraper timers (no Prefect, no extra containers)

Scrapers run **natively** via `uv`, scheduled by systemd timers — the lightest
possible footprint. Backend + frontend already use ~500 MB; we don't want to
add Prefect server + worker to that.

```bash
# Install uv on the host (one-time, ~10 MB)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Sync pipeline deps + Playwright (the Chromium browser is ~150 MB)
cd ~/cannabis-burlington-platform/pipeline
~/.local/bin/uv sync
~/.local/bin/uv run playwright install --with-deps chromium
cp .env.example .env
nano .env       # DATABASE_URL pointing at RDS (same host as backend)

# Install + enable timers
sudo cp ~/cannabis-burlington-platform/infra/systemd/*.{service,timer} /etc/systemd/system/
sudo touch /var/log/cannabis-pipeline.log
sudo chown ec2-user /var/log/cannabis-pipeline.log
sudo systemctl daemon-reload
sudo systemctl enable --now scrape-ocs.timer scrape-hibuddy.timer scrape-agco.timer promo-duration.timer
```

Verify:

```bash
# Show next firing time for each timer
systemctl list-timers --no-pager | grep -E "scrape-|promo-"

# Manually fire one to confirm it works (the lightest one)
sudo systemctl start promo-duration.service
journalctl -u promo-duration.service -n 30
tail -50 /var/log/cannabis-pipeline.log
```

### 9. (Optional) HTTPS with a domain

If you have a domain pointed at the EC2 IP:

```bash
sudo dnf install -y certbot
sudo certbot certonly --standalone -d your-domain.com -m you@email.com --agree-tos -n
# Then edit infra/nginx.conf to add a 443 server block — restart compose.
```

Without a domain, http://&lt;EC2-IP&gt; works for a portfolio demo.

---

## Validating "the pipeline is running"

Three independent surfaces:

### a) systemctl
```bash
ssh -i ~/Downloads/cannabis-key.pem ec2-user@<EC2-IP> '
  systemctl list-timers | grep -E "scrape-|promo-";
  tail -40 /var/log/cannabis-pipeline.log;
'
```

### b) Backend API
```bash
curl http://<EC2-IP>/pipeline/freshness | jq
# [{"job_name":"ocs_new_arrivals","last_success_at":"...","minutes_since_success":12.5},...]

curl "http://<EC2-IP>/pipeline/runs?limit=10" | jq '.[] | {job_name, status, duration_s, rows_processed}'
```

### c) In-app footer
The "Data freshness" footer on http://&lt;EC2-IP&gt;/ shows colour-coded chips per
job (green &lt; 36 h, amber &lt; 8 d, red beyond).

---

## Updating the deployed code

On every push to `main`, GitHub Actions rebuilds + pushes new image tags.
To pick them up on EC2:

```bash
ssh ec2-user@<EC2-IP> '
  cd cannabis-burlington-platform/infra &&
  docker compose -f docker-compose.prod.yml pull &&
  docker compose -f docker-compose.prod.yml up -d
'
```

Or use the manual [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) (you'll need
to set `EC2_HOST` + `EC2_SSH_KEY` secrets in the repo).

---

## Cost guardrails

1. **Budget alarm**: Billing → Budgets → Create at $1/mo with email alert.
2. **S3 lifecycle**: `cannabis-raw` bucket → Lifecycle → move objects > 90 d
   to Glacier ($0.004/GB).
3. **Tag everything** with `Project=cannabis-platform` for cost-explorer attribution.
4. **Stop EC2** when not demoing: AWS Console → EC2 → Stop. No more compute
   charges; EBS still bills ~$1.60/mo for 20 GB storage.

---

## After your 12-month free tier expires

If demo traffic stays low and you want to drop the bill to $0, migrate piece
by piece:

1. **DB → Neon** (free 0.5 GB Postgres). Run `pg_dump` from RDS, restore to
   Neon, update `BACKEND_DATABASE_URL` in your `.env`, restart compose.
2. **Frontend → Vercel** (free for hobby). Push the repo, Vercel auto-detects
   Next.js. Drop the EC2 frontend container.
3. **Backend stays on EC2** (smallest cost remaining) **or** migrate to
   **Fly.io** (3 free 256 MB VMs).

This split-stack is what most portfolio projects use long-term. AWS is great
for the first 12 months and the resume bullet ("deployed on AWS"), then move.

---

## When something breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker compose up` fails: image pull error | GHCR package is private | GitHub → Packages → make public |
| Browser shows API errors / CORS blocked | `CORS_ORIGINS` doesn't include the EC2 IP | edit `infra/.env`, restart compose |
| `/health` returns `db_ok: false` | RDS SG doesn't allow EC2 | Add inbound rule in RDS SG (step 3 above) |
| Timer doesn't fire | Service file syntax error | `journalctl -u scrape-ocs.service -n 50` |
| Frontend shows "—" everywhere | Backend not reachable from browser | check nginx logs, EC2 port 80 SG rule |
