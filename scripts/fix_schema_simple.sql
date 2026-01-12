-- Simple schema fix for production database
-- This applies the missing columns/tables without touching django_migrations
-- Run on production: docker compose -f docker-compose.small.yml exec db psql -U diveops -d diveops -f /path/to/this/file.sql

BEGIN;

-- ============================================
-- Fix 1: Add missing columns to diveops_excursion
-- ============================================

-- Add is_override column if missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'diveops_excursion' AND column_name = 'is_override') THEN
        ALTER TABLE diveops_excursion ADD COLUMN is_override boolean DEFAULT false NOT NULL;
        ALTER TABLE diveops_excursion ALTER COLUMN is_override DROP DEFAULT;
        RAISE NOTICE 'Added is_override column';
    END IF;
END $$;

-- Add occurrence_start column if missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'diveops_excursion' AND column_name = 'occurrence_start') THEN
        ALTER TABLE diveops_excursion ADD COLUMN occurrence_start timestamp with time zone NULL;
        RAISE NOTICE 'Added occurrence_start column';
    END IF;
END $$;

-- Add override_fields column if missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'diveops_excursion' AND column_name = 'override_fields') THEN
        ALTER TABLE diveops_excursion ADD COLUMN override_fields jsonb DEFAULT '{}'::jsonb NOT NULL;
        ALTER TABLE diveops_excursion ALTER COLUMN override_fields DROP DEFAULT;
        RAISE NOTICE 'Added override_fields column';
    END IF;
END $$;

-- ============================================
-- Fix 2: Create RecurrenceRule table if missing
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'diveops_recurrencerule') THEN
        CREATE TABLE diveops_recurrencerule (
            created_at timestamp with time zone NOT NULL,
            updated_at timestamp with time zone NOT NULL,
            id uuid NOT NULL PRIMARY KEY,
            deleted_at timestamp with time zone NULL,
            rrule_text varchar(500) NOT NULL,
            dtstart timestamp with time zone NOT NULL,
            dtend timestamp with time zone NULL,
            timezone varchar(50) NOT NULL,
            description varchar(200) NOT NULL
        );
        CREATE INDEX diveops_rec_dtstart_d3161e_idx ON diveops_recurrencerule (dtstart);
        RAISE NOTICE 'Created diveops_recurrencerule table';
    END IF;
END $$;

-- ============================================
-- Fix 3: Create ExcursionSeries table if missing
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'diveops_excursionseries') THEN
        CREATE TABLE diveops_excursionseries (
            created_at timestamp with time zone NOT NULL,
            updated_at timestamp with time zone NOT NULL,
            id uuid NOT NULL PRIMARY KEY,
            deleted_at timestamp with time zone NULL,
            name varchar(200) NOT NULL,
            duration_minutes integer NOT NULL CHECK (duration_minutes >= 0),
            capacity_default integer NOT NULL CHECK (capacity_default >= 0),
            price_default numeric(10, 2) NULL,
            currency varchar(3) NOT NULL,
            meeting_place text NOT NULL,
            notes text NOT NULL,
            status varchar(20) NOT NULL,
            window_days integer NOT NULL CHECK (window_days >= 0),
            last_synced_at timestamp with time zone NULL,
            created_by_id bigint NULL REFERENCES core_user(id) DEFERRABLE INITIALLY DEFERRED,
            dive_shop_id uuid NOT NULL REFERENCES django_parties_organization(id) DEFERRABLE INITIALLY DEFERRED,
            dive_site_id uuid NULL REFERENCES diveops_divesite(id) DEFERRABLE INITIALLY DEFERRED,
            excursion_type_id uuid NOT NULL REFERENCES diveops_excursiontype(id) DEFERRABLE INITIALLY DEFERRED,
            recurrence_rule_id uuid NOT NULL UNIQUE REFERENCES diveops_recurrencerule(id) DEFERRABLE INITIALLY DEFERRED
        );

        CREATE INDEX diveops_exc_dive_sh_a09a44_idx ON diveops_excursionseries (dive_shop_id, status);
        CREATE INDEX diveops_exc_status_314e97_idx ON diveops_excursionseries (status);
        CREATE INDEX diveops_excursionseries_created_by_id_d41d2e1e ON diveops_excursionseries (created_by_id);
        CREATE INDEX diveops_excursionseries_dive_shop_id_e8d269af ON diveops_excursionseries (dive_shop_id);
        CREATE INDEX diveops_excursionseries_dive_site_id_49068d5a ON diveops_excursionseries (dive_site_id);
        CREATE INDEX diveops_excursionseries_excursion_type_id_96cff90a ON diveops_excursionseries (excursion_type_id);
        RAISE NOTICE 'Created diveops_excursionseries table';
    END IF;
END $$;

-- ============================================
-- Fix 4: Add series_id to excursion if missing
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'diveops_excursion' AND column_name = 'series_id') THEN
        ALTER TABLE diveops_excursion ADD COLUMN series_id uuid NULL
            REFERENCES diveops_excursionseries(id) DEFERRABLE INITIALLY DEFERRED;
        CREATE INDEX diveops_excursion_series_id_74d1adc4 ON diveops_excursion (series_id);
        RAISE NOTICE 'Added series_id column';
    END IF;
END $$;

-- ============================================
-- Fix 5: Create RecurrenceException table if missing
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'diveops_recurrenceexception') THEN
        CREATE TABLE diveops_recurrenceexception (
            created_at timestamp with time zone NOT NULL,
            updated_at timestamp with time zone NOT NULL,
            id uuid NOT NULL PRIMARY KEY,
            deleted_at timestamp with time zone NULL,
            original_start timestamp with time zone NOT NULL,
            exception_type varchar(20) NOT NULL,
            new_start timestamp with time zone NULL,
            reason text NOT NULL,
            rule_id uuid NOT NULL REFERENCES diveops_recurrencerule(id) DEFERRABLE INITIALLY DEFERRED
        );
        CREATE UNIQUE INDEX diveops_unique_recurrence_exception ON diveops_recurrenceexception (rule_id, original_start) WHERE deleted_at IS NULL;
        CREATE INDEX diveops_recurrenceexception_rule_id_fd0f3022 ON diveops_recurrenceexception (rule_id);
        CREATE INDEX diveops_rec_rule_id_4ee136_idx ON diveops_recurrenceexception (rule_id, original_start);
        RAISE NOTICE 'Created diveops_recurrenceexception table';
    END IF;
END $$;

-- ============================================
-- Fix 6: Add visitor_id to django_parties_person if missing
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'django_parties_person' AND column_name = 'visitor_id') THEN
        ALTER TABLE django_parties_person ADD COLUMN visitor_id varchar(36) DEFAULT '' NOT NULL;
        ALTER TABLE django_parties_person ALTER COLUMN visitor_id DROP DEFAULT;
        CREATE INDEX django_parties_person_visitor_id_60cfbd3d ON django_parties_person (visitor_id);
        CREATE INDEX django_parties_person_visitor_id_60cfbd3d_like ON django_parties_person (visitor_id varchar_pattern_ops);
        RAISE NOTICE 'Added visitor_id column';
    ELSE
        -- Fix visitor_id if it was added incorrectly (as uuid NULL instead of varchar NOT NULL)
        ALTER TABLE django_parties_person ALTER COLUMN visitor_id TYPE varchar(36);
        ALTER TABLE django_parties_person ALTER COLUMN visitor_id SET DEFAULT '';
        UPDATE django_parties_person SET visitor_id = '' WHERE visitor_id IS NULL;
        ALTER TABLE django_parties_person ALTER COLUMN visitor_id SET NOT NULL;
        ALTER TABLE django_parties_person ALTER COLUMN visitor_id DROP DEFAULT;
        RAISE NOTICE 'Fixed visitor_id column type/nullability';
    END IF;
END $$;

-- ============================================
-- Verification
-- ============================================

SELECT 'Schema verification:' as message;

SELECT 'diveops_excursion columns:' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'diveops_excursion'
AND column_name IN ('series_id', 'is_override', 'occurrence_start', 'override_fields');

SELECT 'django_parties_person visitor_id:' as table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'django_parties_person' AND column_name = 'visitor_id';

SELECT 'New tables:' as check_type, table_name
FROM information_schema.tables
WHERE table_name IN ('diveops_excursionseries', 'diveops_recurrencerule', 'diveops_recurrenceexception');

COMMIT;

SELECT 'Schema fix complete!' as status;
