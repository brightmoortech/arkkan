DO $migration$
BEGIN
    IF pg_catalog.to_regclass('arkkan.resource_definitions') IS NULL THEN
        CREATE TABLE arkkan.resource_definitions (
            resource_id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
            name text,
            slug text NOT NULL UNIQUE,
            description text,
            type_id uuid NOT NULL REFERENCES arkkan.resource_types (type_id),
            CONSTRAINT resource_definitions_slug_nonblank CHECK (slug ~ '[^[:space:]]')
        );
        REVOKE ALL ON TABLE arkkan.resource_definitions FROM PUBLIC;
    END IF;
END;
$migration$;
