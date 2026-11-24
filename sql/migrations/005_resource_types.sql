DO $migration$
BEGIN
    IF pg_catalog.to_regclass('arkkan.resource_types') IS NULL THEN
        CREATE TABLE arkkan.resource_types (
            type_id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
            slug text NOT NULL UNIQUE,
            description text,
            is_system boolean NOT NULL,
            CONSTRAINT resource_types_slug_nonblank CHECK (slug ~ '[^[:space:]]')
        );
        REVOKE ALL ON TABLE arkkan.resource_types FROM PUBLIC;
    END IF;
END;
$migration$;
