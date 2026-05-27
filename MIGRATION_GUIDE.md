# SQLite → PostgreSQL Migration Guide

This guide explains how to migrate the gadget-store from its ephemeral SQLite
database to the persistent PostgreSQL database provisioned on Railway.

---

## Why This Migration Is Needed

Railway's filesystem is ephemeral — every new deployment starts with a fresh
container, which means any data written to `db.sqlite3` is lost on the next
deploy. PostgreSQL is a separate, persistent service that survives redeployments.

---

## How Migrations Run Automatically on Deploy

`railway.json` is configured with a `preDeployCommand` that runs
`python manage.py migrate` before the new container starts serving traffic:

```json
{
  "deploy": {
    "preDeployCommand": "cd /app/gadget_store && python manage.py migrate --noinput",
    "startCommand": "gunicorn gadget_store.wsgi --bind 0.0.0.0:8000 --workers 2 --timeout 120"
  }
}
```

This means:
- Tables are created in PostgreSQL on the very first deploy.
- Any new Django migrations added in future commits are applied automatically
  before the app restarts — with zero downtime risk.
- You never need to SSH into the container to run `migrate` manually.

---

## Option A — Fresh Start (No Existing Data to Preserve)

If you have no data worth keeping in SQLite (or you plan to re-seed with
`python manage.py seed_data`), simply deploy to Railway. The `preDeployCommand`
will create all tables automatically.

After the deploy completes:

1. Open a Railway shell for the gadget-store service.
2. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
3. Optionally seed demo products:
   ```bash
   python manage.py seed_data
   ```

---

## Option B — Migrate Existing SQLite Data to PostgreSQL

Use this path if you have real orders, users, or products in your local
`db.sqlite3` that you want to carry over.

### Prerequisites

- Python environment with all dependencies installed (`pip install -r requirements.txt`)
- The `gadget_store/db.sqlite3` file present locally
- The `DATABASE_URL` for your Railway PostgreSQL service

### Step 1 — Get Your DATABASE_URL

In the Railway dashboard:
1. Click the **PostgreSQL** service.
2. Go to **Variables** → copy the `DATABASE_URL` value.

### Step 2 — Run the Migration Script

```bash
# From the repository root
export DATABASE_URL="postgresql://postgres:password@host.railway.internal:5432/railway"
export DEBUG=False
python scripts/migrate_to_postgres.py
```

The script will:
1. Dump all data from `db.sqlite3` into a temporary JSON fixture.
2. Apply all Django migrations to PostgreSQL (creates tables).
3. Load the fixture data into PostgreSQL.
4. Print a record-count summary to confirm success.
5. Clean up the temporary fixture file.

### Step 3 — Verify

The script prints a verification table at the end, for example:

```
Model                Count
----------------------------
Users                    3
Categories               6
Products                12
Profiles                 2
Reviews                  5
Orders                   8
Order Items             15
Payments                 7
Delivery Zones          16
```

Cross-check these numbers against your SQLite data to confirm everything
transferred correctly.

### Step 4 — Deploy

Push your code to Railway. The `preDeployCommand` will run `migrate` (a no-op
since tables already exist) and gunicorn will start against the populated
PostgreSQL database.

---

## Troubleshooting

### `DATABASE_URL is not set`

Export the variable before running the script:
```bash
export DATABASE_URL="postgresql://..."
```

### `django.db.utils.OperationalError: could not connect to server`

- Confirm the PostgreSQL service is running in Railway.
- If running locally, Railway's internal hostnames (`.railway.internal`) are
  only reachable from within Railway's network. Use the **public** connection
  string from the PostgreSQL service's **Connect** tab instead.

### `IntegrityError` during `loaddata`

This usually means the target database already has conflicting data. To start
fresh:
```bash
# In a Railway shell
python manage.py flush --noinput
python manage.py loaddata /path/to/fixture.json
```

### `No module named 'dj_database_url'`

Install dependencies:
```bash
pip install -r requirements.txt
```

### Migrations fail with `relation does not exist`

This can happen if a previous partial migration left the database in an
inconsistent state. Run:
```bash
python manage.py migrate --run-syncdb
```

### `profile_picture column missing`

This was caused by the SQLite database not having the `0004_profile_picture`
migration applied. PostgreSQL will have all migrations applied from scratch, so
this column will exist from the start.

---

## Checking Migration Status

To see which migrations have been applied to PostgreSQL:

```bash
# In a Railway shell or locally with DATABASE_URL set
python manage.py showmigrations
```

All migrations should show `[X]` (applied).

---

## Rolling Back

If something goes wrong after switching to PostgreSQL, you can temporarily
revert `settings.py` to use SQLite by setting `DEBUG=True` in Railway's
environment variables. This is a stopgap only — fix the root cause and
re-enable PostgreSQL as soon as possible.
