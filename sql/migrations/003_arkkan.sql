DO $migration$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = 'arkkan') THEN
        CREATE SCHEMA arkkan;
        REVOKE ALL ON SCHEMA arkkan FROM PUBLIC;
    END IF;
END;
$migration$;
