#!/usr/bin/env bash
# Restore dvdrental into the dvd_rental Postgres container (Linux-friendly).
# Run from dvd_rental after: docker compose up -d

set -e
cd "$(dirname "$0")/.."

echo "==> Copying dvdrental files into container..."
docker cp pgadmin/storage/admin_example.com/dvdrental dvd_rental_postgres:/backups/dvdrental

echo "==> Creating database (UTF-8, Linux locale)..."
docker exec dvd_rental_postgres psql -U postgres -c "DROP DATABASE IF EXISTS dvdrental;"
docker exec dvd_rental_postgres psql -U postgres -c \
  "CREATE DATABASE dvdrental ENCODING 'UTF8' LC_COLLATE='en_US.utf8' LC_CTYPE='en_US.utf8';"

echo "==> Restoring from dvdrental.tar (ignore DROP warnings on empty DB)..."
docker exec dvd_rental_postgres pg_restore -U postgres -d dvdrental --no-owner /backups/dvdrental.tar 2>&1 | tail -5 || true

echo "==> Quick check..."
docker exec dvd_rental_postgres psql -U postgres -d dvdrental -c "SELECT COUNT(*) AS films FROM film;"

echo "Done. dvdrental is ready for script 01."
