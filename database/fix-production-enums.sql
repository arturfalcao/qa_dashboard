-- ============================================================
-- FIX PRODUCTION ENUMS FOR REPORTS
-- Date: 2025-10-01
-- Description: Adds missing enum values for report types and statuses
-- ============================================================

-- Start transaction
BEGIN;

-- ============================================================
-- 1. Fix reports_type_enum - Add missing types
-- ============================================================

-- Check if enum exists, if not create it
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reports_type_enum') THEN
    CREATE TYPE "public"."reports_type_enum" AS ENUM (
      'MONTHLY_SCORECARD',
      'LOT',
      'EXECUTIVE_QUALITY_SUMMARY',
      'LOT_INSPECTION_REPORT',
      'MEASUREMENT_COMPLIANCE_SHEET',
      'PACKAGING_READINESS_REPORT',
      'SUPPLIER_PERFORMANCE_SNAPSHOT',
      'CAPA_REPORT',
      'INLINE_QC_CHECKPOINTS',
      'DPP_SUMMARY'
    );
    RAISE NOTICE 'Created reports_type_enum with all values';
  ELSE
    -- Add missing values if enum exists
    -- Add INLINE_QC_CHECKPOINTS if missing
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum
      WHERE enumlabel = 'INLINE_QC_CHECKPOINTS'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
    ) THEN
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'INLINE_QC_CHECKPOINTS';
      RAISE NOTICE 'Added INLINE_QC_CHECKPOINTS to reports_type_enum';
    END IF;

    -- Add DPP_SUMMARY if missing
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum
      WHERE enumlabel = 'DPP_SUMMARY'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
    ) THEN
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'DPP_SUMMARY';
      RAISE NOTICE 'Added DPP_SUMMARY to reports_type_enum';
    END IF;
  END IF;
END$$;

-- ============================================================
-- 2. Fix reports_status_enum - Create or update with all statuses
-- ============================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reports_status_enum') THEN
    CREATE TYPE "public"."reports_status_enum" AS ENUM (
      'PENDING',
      'READY',
      'FAILED',
      'GENERATING',
      'COMPLETED',
      'EXPIRED'
    );
    RAISE NOTICE 'Created reports_status_enum with all values';
  ELSE
    -- Add missing values if enum exists
    -- Add GENERATING if missing (this is the one causing the error)
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum
      WHERE enumlabel = 'GENERATING'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
    ) THEN
      ALTER TYPE "public"."reports_status_enum" ADD VALUE IF NOT EXISTS 'GENERATING';
      RAISE NOTICE 'Added GENERATING to reports_status_enum';
    END IF;

    -- Add COMPLETED if missing
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum
      WHERE enumlabel = 'COMPLETED'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
    ) THEN
      ALTER TYPE "public"."reports_status_enum" ADD VALUE IF NOT EXISTS 'COMPLETED';
      RAISE NOTICE 'Added COMPLETED to reports_status_enum';
    END IF;

    -- Add EXPIRED if missing
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum
      WHERE enumlabel = 'EXPIRED'
      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
    ) THEN
      ALTER TYPE "public"."reports_status_enum" ADD VALUE IF NOT EXISTS 'EXPIRED';
      RAISE NOTICE 'Added EXPIRED to reports_status_enum';
    END IF;
  END IF;
END$$;

-- ============================================================
-- 3. Fix reports_language_enum - Create if doesn't exist
-- ============================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reports_language_enum') THEN
    CREATE TYPE "public"."reports_language_enum" AS ENUM (
      'PT',
      'EN',
      'ES',
      'FR',
      'IT',
      'DE'
    );
    RAISE NOTICE 'Created reports_language_enum with all values';
  END IF;
END$$;

-- ============================================================
-- 4. Verify all enums are correct
-- ============================================================

-- Show report type enum values
SELECT 'Report Types:' as info;
SELECT enumlabel as report_type
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
ORDER BY enumsortorder;

-- Show report status enum values
SELECT 'Report Statuses:' as info;
SELECT enumlabel as report_status
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
ORDER BY enumsortorder;

-- Show report language enum values
SELECT 'Report Languages:' as info;
SELECT enumlabel as report_language
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_language_enum')
ORDER BY enumsortorder;

-- ============================================================
-- 5. Add migration record (if migrations table exists)
-- ============================================================

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'migrations') THEN
    -- Add migration records if not already present
    INSERT INTO migrations(timestamp, name)
    VALUES
      (1759300000000, 'AddDppSummaryReportType1759300000000'),
      (1759400000000, 'AddReportStatusEnum1759400000000')
    ON CONFLICT (timestamp) DO NOTHING;
    RAISE NOTICE 'Updated migrations table';
  END IF;
END$$;

-- Commit transaction
COMMIT;

-- ============================================================
-- Final verification message
-- ============================================================

SELECT
  '✅ Enums fixed successfully! Summary:' as message
UNION ALL
SELECT
  '- reports_type_enum: ' || count(*) || ' values (should be 10)' as message
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
UNION ALL
SELECT
  '- reports_status_enum: ' || count(*) || ' values (should be 6)' as message
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
UNION ALL
SELECT
  '- reports_language_enum: ' || count(*) || ' values (should be 6)' as message
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_language_enum');