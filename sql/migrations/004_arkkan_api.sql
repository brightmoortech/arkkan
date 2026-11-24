DO $migration$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = 'arkkan_api') THEN
        CREATE SCHEMA arkkan_api;
        REVOKE ALL ON SCHEMA arkkan_api FROM PUBLIC;
    END IF;
END;
$migration$;
