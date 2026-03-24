#!/bin/sh
set -e

wait_for_db() {
  echo "[entrypoint] Waiting for database..."
  until python -c "
import os, psycopg2
try:
    psycopg2.connect(
        host=os.environ.get('DB_HOST','db'),
        port=os.environ.get('DB_PORT',5432),
        dbname=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
    )
except Exception:
    exit(1)
" 2>/dev/null; do
    sleep 2
  done
  echo "[entrypoint] Database is ready."
}

wait_for_db

echo "[entrypoint] Migrations..."
python manage.py makemigrations users --noinput
python manage.py makemigrations blog --noinput
python manage.py migrate --noinput

echo "[entrypoint] Static files..."
python manage.py collectstatic --noinput

echo "[entrypoint] Done."
exec "$@"
