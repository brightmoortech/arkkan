DO $migration$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'arkkan_admin') THEN
        CREATE ROLE arkkan_admin LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOREPLICATION NOBYPASSRLS INHERIT;
    END IF;
END;
$migration$;
