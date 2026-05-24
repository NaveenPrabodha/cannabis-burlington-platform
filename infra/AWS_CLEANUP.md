# AWS cleanup — terminate the failing deployment

Run this before redeploying with the new prebuilt-image flow in
[DEPLOY.md](./DEPLOY.md). Takes ~5 minutes in the AWS Console. Stops all
charges immediately.

## Pre-flight

Open your AWS Console. Confirm you're in the **same region** as your existing
resources (top-right region selector). Your instance IP was `56.228.35.247`,
which based on its `eu-north-1`-style address space is **likely
`eu-north-1` (Stockholm)** — verify before clicking around.

```bash
# Quick check from your laptop — this reveals the region
nslookup ec2-56-228-35-247.<region>.compute.amazonaws.com 2>/dev/null
# or check the EC2 dashboard — your instance appears only in its region
```

---

## 1. Terminate the EC2 instance

EC2 dashboard → Instances:

1. Tick the row for `cannabis-host` (or whatever name your t3.micro has)
2. Top right → **Instance state** → **Terminate (delete) instance**
3. Confirm

State changes to `Shutting-down` → `Terminated` over ~1 minute. After it's
terminated:

- Compute charges stop **immediately**
- The instance is unrecoverable (its disk is wiped)
- The attached EBS volume is auto-deleted if `delete on termination` was set
  (default for instance-store-backed AMIs like Amazon Linux 2023)

Verify EBS:
EC2 → Elastic Block Store → Volumes → ensure no `available` (unattached)
volumes remain. If any do → tick → Actions → **Delete volume**.

## 2. Delete the RDS instance

RDS dashboard → Databases:

1. Tick `cannabis-db`
2. Actions → **Delete**
3. In the confirmation dialog:
   - **Untick** "Create final snapshot" (we have CSV seed data — no need to pay for snapshot storage)
   - **Untick** "Retain automated backups"
   - **Tick** "I acknowledge that…"
   - Type `delete me` to confirm
4. Confirm

Status changes to `Deleting` → instance disappears over ~5 minutes.

## 3. Clean up the orphans

After EC2 + RDS are gone, these may still exist and may bill (small but >$0):

**Elastic IPs**: EC2 → Network & Security → Elastic IPs
- Any **unassociated** Elastic IPs are billed $0.005/hr (~$3.60/mo)
- Tick any → Actions → **Release Elastic IP address**

**Snapshots**: EC2 → Snapshots and RDS → Snapshots
- Delete any leftover ones (~$0.05/GB/mo)

**Security groups**: EC2 → Security Groups
- Delete `rds-cannabis` and `ec2-cannabis` (free, just for cleanliness)
- Drop any references they had to each other first (Edit inbound rules)

**Key pairs**: EC2 → Key Pairs
- Delete `cannabis-key.pem` (free, but a stale key on AWS is a small attack surface)
- Don't forget to delete your local copy: `rm ~/Downloads/cannabis-key.pem`

**VPC, subnets, IGW**: leave them. They're the AWS default VPC and are free.

## 4. Verify the bill is back to $0

Billing dashboard → **Cost Explorer** → group by Service.

- May still show small charges for the current day (proration). Those will
  not recur.
- Set a billing alert at $1/mo: Billing → Budgets → Create budget.

## 5. (Optional) Delete leftover S3 buckets

If you created `cannabis-raw` for scrape lake:

S3 → tick the bucket → Empty → confirm → tick → Delete → confirm.

---

## You're done

Now follow [DEPLOY.md](./DEPLOY.md) from step 1 with the new prebuilt-image
flow. The new deployment won't build anything on the host — `next build`
runs in GitHub Actions where it has 16 GB RAM to work with.

## Quick sanity check before re-deploying

```bash
# From your laptop — should fail (no resources)
ssh -i ~/Downloads/cannabis-key.pem ec2-user@56.228.35.247
# → Connection refused / timeout / no route → confirms termination worked
```
