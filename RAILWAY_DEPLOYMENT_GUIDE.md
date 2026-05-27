# Railway PostgreSQL Deployment Guide

## Overview
This guide explains how to properly deploy the gadget-store Django app to Railway with PostgreSQL.

## Changes Made for PostgreSQL Support

### 1. **Dockerfile** (`Dockerfile`)
- Removed `RUN python manage.py collectstatic --noinput --clear` from build phase
- **Reason**: `collectstatic` needs `DATABASE_URL` which isn't available during Docker build
- Static files are now collected during the deploy phase (see railway.json)

### 2. **railway.json** Configuration
Updated deployment commands:
```json
"preDeployCommand": "python manage.py collectstatic --noinput --clear && python manage.py migrate --noinput"
```
- Runs **after** environment variables are injected by Railway
- Sequence:
  1. Collect static files (with DATABASE_URL available)
  2. Run database migrations (creates/updates tables)

### 3. **settings.py** Database Configuration
- Added explicit `DATABASE_URL` handling for production
- When `DEBUG=False` (production):
  - Requires `DATABASE_URL` to be set (raises `ImproperlyConfigured` if missing)
  - Uses PostgreSQL via `dj_database_url.parse()`
- When `DEBUG=True` (development):
  - Uses SQLite (`db.sqlite3`)
- Added diagnostic logging to Railway logs showing which database is connected

### 4. **ALLOWED_HOSTS** Normalization
- Trimmed whitespace from host entries to prevent invalid values

## Railway Setup Steps

### Step 1: Add PostgreSQL Plugin
1. Go to your Railway project dashboard
2. Click **+ Create** or **Add Service**
3. Select **Database → PostgreSQL**
4. Railway automatically creates a `Postgres` service

### Step 2: Link PostgreSQL to Django App
1. Go to your Django app service settings
2. In the **Variables** section, add reference to PostgreSQL:
   - Railway should auto-detect this, but if not:
   - Add variable: `DATABASE_URL` = `${{ Postgres.DATABASE_URL }}`

### Step 3: Set Production Environment Variables
Add these variables to your Django service in Railway:
- `DEBUG` = `False` (required for production)
- `SECRET_KEY` = `<your-django-secret-key>` (required)
- `ALLOWED_HOSTS` = `your-domain.up.railway.app,www.your-domain.com` (if custom domain)
- Other optional variables:
  - `PAYSTACK_SECRET_KEY`
  - `PAYSTACK_PUBLIC_KEY`
  - `CLOUDINARY_CLOUD_NAME`
  - etc.

### Step 4: Deploy
```bash
git push origin main  # or your branch
```

Railway will:
1. Build Docker image
2. Create PostgreSQL database
3. Inject `DATABASE_URL` environment variable
4. Run preDeployCommand: collect static files + migrate
5. Start gunicorn server

### Step 5: Migrate Existing Data (SQLite to Postgres)
If you have products or users in your local `db.sqlite3` that you want to move to Railway:
1. Copy your **Public Database URL** from the Railway PostgreSQL service variables.
2. Run the migration script from your local terminal:
   ```powershell
   $env:DATABASE_URL="your-postgres-connection-string"
   python scripts/migrate_to_postgres.py
   ```

## Troubleshooting

### Error: "DATABASE_URL must be set when DEBUG=False"
- **Cause**: PostgreSQL addon not linked, or `DATABASE_URL` variable not injected
- **Fix**: 
  1. Verify PostgreSQL service exists in your Railway project
  2. Check service variables include `DATABASE_URL = ${{ Postgres.DATABASE_URL }}`
  3. View deployment logs in Railway to confirm environment variables

### Error: "ImproperlyConfigured" During Deploy
- **Cause**: `DATABASE_URL` not available during build/deploy phases
- **Fix**: This should not occur with current setup. If it does, check:
  - Railway PostgreSQL addon is running
  - Service variables are linked correctly

### Static Files Not Loading
- **Cause**: `collectstatic` failed during preDeployCommand
- **Fix**: Check Railway deploy logs for collectstatic errors
- Ensure WhiteNoise middleware is enabled (it is in settings.py)

### Migration Failures
- **Cause**: Database schema issues or data conflicts
- **Fix**: 
  1. Check preDeployCommand logs in Railway
  2. If first deploy, ensure all migrations exist locally
  3. Consider running: `python manage.py makemigrations` locally before pushing

## Local Development

To test production configuration locally:
```bash
# Set production environment
export DEBUG=False
export DATABASE_URL="postgresql://user:password@localhost:5432/gadget_store"

# From gadget_store directory
python manage.py check  # Should show PostgreSQL connection
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py runserver
```

## Environment Variables Reference

| Variable | Value | Required | Notes |
|----------|-------|----------|-------|
| `DEBUG` | `False` | Yes (production) | Railway logs DB connection info |
| `DATABASE_URL` | `${{ Postgres.DATABASE_URL }}` | Yes (production) | Auto-injected by Railway PostgreSQL addon |
| `SECRET_KEY` | `<your-secret>` | Yes | Use a strong random value |
| `ALLOWED_HOSTS` | `your-app.up.railway.app` | Yes | Add custom domains if applicable |
| `PORT` | `8000` | No | Auto-set by Railway (default: 8000) |

## Verification

Once deployed:
1. Visit your Railway app URL
2. Check admin panel at `/admin`
3. View Railway logs for database connection confirmation
4. Database should show PostgreSQL connection in logs

## Files Modified
- ✅ `Dockerfile` - Removed build-time collectstatic
- ✅ `railway.json` - Added collectstatic + migrate to preDeployCommand
- ✅ `gadget_store/settings.py` - Explicit DATABASE_URL handling + diagnostics
- ✅ `gadget_store/settings.py` - ALLOWED_HOSTS whitespace normalization
