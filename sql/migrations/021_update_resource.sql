CREATE FUNCTION arkkan_api.update_resource(slug text, changes jsonb, version text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    target_version_id uuid;
    fields jsonb;
    response_data jsonb;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response('update_resource', 'error', NULL, 'Resource slug must be nonblank.');
    END IF;
    IF $2 IS NULL OR pg_catalog.jsonb_typeof($2) <> 'object' OR $2 = '{}'::jsonb THEN
        RETURN arkkan.api_response(
            'update_resource', 'error', NULL,
            'Changes must be a nonempty JSON object.'
        );
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_catalog.jsonb_each($2) AS entry
        WHERE entry.key NOT IN ('name', 'description', 'version_info')
           OR pg_catalog.jsonb_typeof(entry.value) NOT IN ('string', 'null')
    ) THEN
        RETURN arkkan.api_response(
            'update_resource', 'error', NULL,
            'Only name, description and version_info with string or null values are editable.'
        );
    END IF;
    IF ($2 ? 'version_info' AND NOT arkkan.api_identifier_valid($3))
       OR (NOT ($2 ? 'version_info') AND $3 IS NOT NULL) THEN
        RETURN arkkan.api_response(
            'update_resource', 'error', NULL,
            'Supply a nonblank version exactly when updating version_info.'
        );
    END IF;
    SELECT d.resource_id INTO target_id FROM arkkan.resource_definitions AS d
    WHERE d.slug = $1 FOR UPDATE;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('update_resource', 'error', NULL, 'Resource does not exist.');
    END IF;
    IF $2 ? 'version_info' THEN
        SELECT v.version_id INTO target_version_id FROM arkkan.resource_versions AS v
        WHERE v.resource_id = target_id AND v.version = $3 FOR UPDATE;
        IF NOT FOUND THEN
            RETURN arkkan.api_response(
                'update_resource', 'error', NULL,
                'Resource version does not exist.'
            );
        END IF;
    END IF;
    -- Validate every target before the first write so mixed updates are atomic.
    UPDATE arkkan.resource_definitions AS d
    SET name = CASE WHEN $2 ? 'name' THEN $2 ->> 'name' ELSE d.name END,
        description = CASE WHEN $2 ? 'description' THEN $2 ->> 'description' ELSE d.description END
    WHERE d.resource_id = target_id;
    IF $2 ? 'version_info' THEN
        UPDATE arkkan.resource_versions AS v SET version_info = $2 ->> 'version_info'
        WHERE v.version_id = target_version_id;
    END IF;
    SELECT pg_catalog.jsonb_agg(entry.key ORDER BY entry.key) INTO fields
    FROM pg_catalog.jsonb_object_keys($2) AS entry(key);
    response_data := pg_catalog.jsonb_build_object('slug', $1, 'updated_fields', fields);
    IF $3 IS NOT NULL THEN
        response_data := response_data || pg_catalog.jsonb_build_object('version', $3);
    END IF;
    RETURN arkkan.api_response('update_resource', 'success', response_data, NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response(
        'update_resource', 'error', NULL,
        'Concurrent change prevented the operation; retry the transaction.'
    );
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.update_resource(text, jsonb, text) FROM PUBLIC;
