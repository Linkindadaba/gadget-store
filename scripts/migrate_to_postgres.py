#!/usr/bin/env python
"""
SQLite → PostgreSQL Migration Script for gadget-store
======================================================
Exports all data from the local SQLite database and imports it into
the PostgreSQL database pointed to by DATABASE_URL.

Usage
-----
Run locally (requires DATABASE_URL to point at the target Postgres DB):

    # From the repo root
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    export DEBUG=False
    python scripts/migrate_to_postgres.py

Or as a one-off Railway job:
    railway run python scripts/migrate_to_postgres.py

Requirements
------------
- Both databases must be reachable from the machine running this script.
- The SQLite file (gadget_store/db.sqlite3) must exist and contain data.
- All Python dependencies from requirements.txt must be installed.
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — ensure manage.py is on the path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DJANGO_ROOT = REPO_ROOT / "gadget_store"

sys.path.insert(0, str(DJANGO_ROOT))
os.chdir(DJANGO_ROOT)

# Point Django at the project settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gadget_store.settings")


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess command, streaming output to stdout."""
    print(f"\n▶  {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, **kwargs)
    return result


def check_prerequisites() -> None:
    """Validate that DATABASE_URL is set and points at PostgreSQL."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("❌  DATABASE_URL is not set.")
        print("    Export it before running this script:")
        print("    export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
        sys.exit(1)

    if not db_url.startswith(("postgres://", "postgresql://")):
        print(f"❌  DATABASE_URL does not look like a PostgreSQL URL: {db_url!r}")
        print("    This script is intended to migrate INTO PostgreSQL.")
        sys.exit(1)

    sqlite_path = DJANGO_ROOT / "db.sqlite3"
    if not sqlite_path.exists():
        print(f"❌  SQLite database not found at {sqlite_path}")
        print("    Make sure you are running this from a machine that has the SQLite file.")
        sys.exit(1)

    print("✅  Prerequisites OK")
    print(f"    SQLite source : {sqlite_path}")
    print(f"    Postgres target: {db_url.split('@')[-1]}")  # hide credentials


def export_sqlite_data(fixture_path: Path) -> None:
    """Dump all data from SQLite into a JSON fixture file."""
    print("\n📤  Exporting data from SQLite …")

    # Temporarily force DEBUG=True so settings.py uses the SQLite backend
    os.environ["DEBUG"] = "True"

    # Exclude contenttypes and auth.permission — Django recreates these
    # automatically and they cause conflicts on import.
    excluded = [
        "--exclude=contenttypes",
        "--exclude=auth.permission",
        "--exclude=sessions",
    ]

    run(
        [sys.executable, "manage.py", "dumpdata", "--natural-foreign",
         "--natural-primary", "--indent=2"] + excluded + ["--output", str(fixture_path)],
    )

    # Count exported records
    with open(fixture_path) as fh:
        records = json.load(fh)
    print(f"✅  Exported {len(records)} records to {fixture_path}")


def apply_migrations_postgres() -> None:
    """Run migrate against PostgreSQL to create all tables."""
    print("\n🗄️   Applying migrations to PostgreSQL …")

    # Switch back to production mode so dj_database_url picks up DATABASE_URL
    os.environ["DEBUG"] = "False"

    run([sys.executable, "manage.py", "migrate", "--noinput"])
    print("✅  Migrations applied")


def load_data_postgres(fixture_path: Path) -> None:
    """Load the exported fixture into PostgreSQL."""
    print("\n📥  Loading data into PostgreSQL …")

    os.environ["DEBUG"] = "False"

    run([sys.executable, "manage.py", "loaddata", str(fixture_path)])
    print("✅  Data loaded")


def verify_migration() -> None:
    """Print record counts for key models to confirm the migration succeeded."""
    print("\n🔍  Verifying migration …")

    os.environ["DEBUG"] = "False"

    # Import Django here, after env vars are set
    import django
    django.setup()

    from django.contrib.auth.models import User
    from store.models import Category, Product, Profile, Review
    from orders.models import Order, OrderItem
    from payments.models import Payment
    from logistics.models import DeliveryZone

    checks = [
        ("Users",         User.objects.count()),
        ("Categories",    Category.objects.count()),
        ("Products",      Product.objects.count()),
        ("Profiles",      Profile.objects.count()),
        ("Reviews",       Review.objects.count()),
        ("Orders",        Order.objects.count()),
        ("Order Items",   OrderItem.objects.count()),
        ("Payments",      Payment.objects.count()),
        ("Delivery Zones", DeliveryZone.objects.count()),
    ]

    print(f"\n{'Model':<20} {'Count':>6}")
    print("-" * 28)
    for label, count in checks:
        print(f"{label:<20} {count:>6}")

    print("\n✅  Verification complete")


def main() -> None:
    print("=" * 60)
    print("  gadget-store  SQLite → PostgreSQL Migration")
    print("=" * 60)

    check_prerequisites()

    with tempfile.NamedTemporaryFile(
        suffix=".json", prefix="gadget_store_fixture_", delete=False
    ) as tmp:
        fixture_path = Path(tmp.name)

    try:
        export_sqlite_data(fixture_path)
        apply_migrations_postgres()
        load_data_postgres(fixture_path)
        verify_migration()

        print("\n🎉  Migration complete!")
        print("    Your PostgreSQL database is ready.")
        print("    You can now deploy to Railway and data will persist.")

    except subprocess.CalledProcessError as exc:
        print(f"\n❌  Command failed with exit code {exc.returncode}")
        print("    See output above for details.")
        sys.exit(exc.returncode)
    finally:
        if fixture_path.exists():
            fixture_path.unlink()
            print(f"\n🧹  Cleaned up temporary fixture file: {fixture_path}")


if __name__ == "__main__":
    main()
