#!/bin/bash
# Fix production database schema by unfaking and re-running migrations
# Run this on the production server

set -e

echo "=== Production Schema Fix ==="
echo "This will fix the database schema by properly running migrations"
echo ""

# Step 1: Check current state
echo "Step 1: Checking current migration state..."
docker compose -f docker-compose.small.yml exec web python manage.py showmigrations diveops django_parties | tail -20

# Step 2: Remove faked migration records for problematic migrations
echo ""
echo "Step 2: Removing faked migration records..."

# Remove the faked migration records (they're in django_migrations table but SQL wasn't run)
docker compose -f docker-compose.small.yml exec db psql -U diveops -d diveops << 'EOSQL'
-- First, let's check what's in the migrations table
SELECT app, name FROM django_migrations WHERE app IN ('diveops', 'django_parties') ORDER BY app, id;

-- Remove faked migrations that need to be re-run
-- 0064_recurring_excursions adds series_id and related tables
DELETE FROM django_migrations WHERE app = 'diveops' AND name = '0064_recurring_excursions';

-- 0065 onwards might depend on 0064
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0065_signed_agreement_immutable_trigger';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0066_add_diver_relationship_meta';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0067_migrate_relationships_to_party_relationship';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0068_add_email_settings';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0069_add_email_template';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0070_divebuddygroup';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0071_flow_types';
DELETE FROM django_migrations WHERE app = 'diveops' AND name >= '0072_performance_indexes';

-- Remove faked django_parties migrations
DELETE FROM django_migrations WHERE app = 'django_parties' AND name = '0005_add_visitor_id';

-- Also clean up any manually added columns that might interfere
ALTER TABLE diveops_excursion DROP COLUMN IF EXISTS series_id CASCADE;
ALTER TABLE django_parties_person DROP COLUMN IF EXISTS visitor_id CASCADE;

EOSQL

# Step 3: Run migrations properly
echo ""
echo "Step 3: Running migrations properly..."
docker compose -f docker-compose.small.yml exec web python manage.py migrate --run-syncdb

# Step 4: Verify
echo ""
echo "Step 4: Verifying schema..."
docker compose -f docker-compose.small.yml exec db psql -U diveops -d diveops << 'EOSQL'
-- Check series_id column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'diveops_excursion' AND column_name = 'series_id';

-- Check visitor_id column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'django_parties_person' AND column_name = 'visitor_id';

-- Check migration records
SELECT app, name FROM django_migrations WHERE app IN ('diveops', 'django_parties') ORDER BY app, name DESC LIMIT 10;
EOSQL

echo ""
echo "=== Schema fix complete! ==="
echo "Now restart the web container:"
echo "docker compose -f docker-compose.small.yml restart web"
