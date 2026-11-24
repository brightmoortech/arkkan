DO $migration$
BEGIN
    IF pg_catalog.to_regclass('arkkan.resource_versions') IS NULL THEN
        CREATE TABLE arkkan.resource_versions (
            version_id uuid PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
            resource_id uuid NOT NULL REFERENCES arkkan.resource_definitions (resource_id),
            version text NOT NULL,
            state text NOT NULL,
            content text NOT NULL DEFAULT '',
            version_info text,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (resource_id, version),
            CONSTRAINT resource_versions_version_nonblank CHECK (version ~ '[^[:space:]]'),
            CONSTRAINT resource_versions_valid_state CHECK (
                state IN ('enabled', 'enabled_default', 'disabled', 'obsolete')
            )
        );
        REVOKE ALL ON TABLE arkkan.resource_versions FROM PUBLIC;
    END IF;
END;
$migration$;
