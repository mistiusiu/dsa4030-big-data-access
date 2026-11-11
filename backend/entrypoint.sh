#!/bin/bash
# ─────────────────────────────────────────────────────────
#  Smart City Access Lab — backend entrypoint
#  Runs every time the container starts, before CMD.
# ─────────────────────────────────────────────────────────
set -e

if [ -n "$POSTGRES_HOST" ]; then
    echo "==> [1/5] Waiting for PostgreSQL at $POSTGRES_HOST..."
    until python -c "
import os, sys, psycopg
try:
    psycopg.connect(host=os.environ['POSTGRES_HOST'], port=os.environ.get('POSTGRES_PORT', '5432'),
                    dbname=os.environ.get('POSTGRES_DB'), user=os.environ.get('POSTGRES_USER'),
                    password=os.environ.get('POSTGRES_PASSWORD'), connect_timeout=3).close()
except Exception as e:
    print('   not ready:', e, file=sys.stderr); sys.exit(1)
"; do sleep 2; done
fi

echo "==> [2/5] Applying migrations..."
python manage.py migrate --noinput

echo "==> [3/5] Seeding roles, permission grid and demo users..."
python manage.py seed_lab

echo "==> [4/5] Building the synthetic data lake (first boot only)..."
python manage.py generate_lake

echo "==> [5/5] Collecting static files..."
python manage.py collectstatic --noinput >/dev/null

echo "==> Starting: $*"
exec "$@"
