CREATE FUNCTION arkkan_api.add_resource(
    slug text, version text, type_slug text DEFAULT NULL,
    name text DEFAULT NULL, description text DEFAULT NULL,
    content text DEFAULT '', version_info text DEFAULT NULL,
    state text DEFAULT 'disabled'
)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    target_type_id uuid;
    selected_type_id uuid;
    new_version_id uuid;
    new_created_at timestamptz;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) OR NOT arkkan.api_identifier_valid($2) THEN
        RETURN arkkan.api_response(
            'add_resource', 'error', NULL,
            'Resource slug and version must be nonblank.'
        );
    END IF;
    IF $3 IS NOT NULL AND NOT arkkan.api_identifier_valid($3) THEN
        RETURN arkkan.api_response(
            'add_resource', 'error', NULL,
            'Resource type slug must be nonblank.'
        );
    END IF;
    IF $6 IS NULL THEN
        RETURN arkkan.api_response(
            'add_resource', 'error', NULL,
            'Content must not be null; use an empty string for empty content.'
        );
    END IF;
    IF NOT arkkan.api_state_valid($8) OR $8 = 'obsolete' THEN
        RETURN arkkan.api_response(
            'add_resource', 'error', NULL,
            'Initial state must be disabled, enabled or enabled_default.'
        );
    END IF;
    SELECT d.resource_id, d.type_id INTO target_id, target_type_id
    FROM arkkan.resource_definitions AS d WHERE d.slug = $1 FOR UPDATE;
    IF NOT FOUND THEN
        IF $3 IS NULL THEN
            RETURN arkkan.api_response(
                'add_resource', 'error', NULL,
                'Resource type is required for a new resource.'
            );
        END IF;
        SELECT t.type_id INTO selected_type_id
        FROM arkkan.resource_types AS t WHERE t.slug = $3 FOR KEY SHARE;
        IF NOT FOUND THEN
            RETURN arkkan.api_response('add_resource', 'error', NULL, 'Resource type does not exist.');
        END IF;
        -- A competing creator may win the unique slug. Re-read and lock its
        -- definition; never replace its metadata or immutable type.
        INSERT INTO arkkan.resource_definitions (slug, type_id, name, description)
        VALUES ($1, selected_type_id, $4, $5) ON CONFLICT ON CONSTRAINT resource_definitions_slug_key DO NOTHING;
        SELECT d.resource_id, d.type_id INTO target_id, target_type_id
        FROM arkkan.resource_definitions AS d WHERE d.slug = $1 FOR UPDATE;
        IF NOT FOUND THEN
            RETURN arkkan.api_response(
                'add_resource', 'error', NULL,
                'Resource changed concurrently; retry the transaction.'
            );
        END IF;
    END IF;
    IF $3 IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM arkkan.resource_types AS t WHERE t.type_id = target_type_id AND t.slug = $3
    ) THEN
        RETURN arkkan.api_response(
            'add_resource', 'error', NULL,
            'Resource type does not match the existing resource.'
        );
    END IF;
    IF EXISTS (SELECT 1 FROM arkkan.resource_versions AS v
               WHERE v.resource_id = target_id AND v.version = $2) THEN
        RETURN arkkan.api_response('add_resource', 'error', NULL, 'Resource version already exists.');
    END IF;
    IF $8 = 'enabled_default' THEN
        UPDATE arkkan.resource_versions AS v SET state = 'enabled'
        WHERE v.resource_id = target_id AND v.state = 'enabled_default';
    END IF;
    INSERT INTO arkkan.resource_versions (resource_id, version, state, content, version_info)
    VALUES (target_id, $2, $8, $6, $7)
    RETURNING version_id, created_at INTO new_version_id, new_created_at;
    RETURN arkkan.api_response('add_resource', 'success', pg_catalog.jsonb_build_object(
        'resource_id', target_id, 'version_id', new_version_id, 'slug', $1,
        'version', $2, 'state', $8,
        'created_at', pg_catalog.to_char(new_created_at AT TIME ZONE 'UTC',
                                       'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')), NULL);
EXCEPTION WHEN unique_violation THEN
    -- The exception block rolls back the definition and any default demotion.
    RETURN arkkan.api_response(
        'add_resource', 'error', NULL,
        'Resource version or default conflicts with an existing record.'
    );
WHEN foreign_key_violation THEN
    RETURN arkkan.api_response(
        'add_resource', 'error', NULL,
        'Referenced resource or type changed concurrently; retry the transaction.'
    );
WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response(
        'add_resource', 'error', NULL,
        'Concurrent change prevented the operation; retry the transaction.'
    );
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.add_resource(text, text, text, text, text, text, text, text) FROM PUBLIC;
