CREATE FUNCTION arkkan_api.get_resource_info(slug text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    payload jsonb;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response('get_resource_info', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    SELECT pg_catalog.jsonb_build_object(
        'slug', d.slug, 'name', d.name, 'description', d.description, 'type_slug', t.slug,
        'versions', COALESCE((
            SELECT pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
                'version', v.version, 'state', v.state,
                'created_at', pg_catalog.to_char(v.created_at AT TIME ZONE 'UTC',
                                               'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')) ORDER BY v.version)
            FROM arkkan.resource_versions AS v WHERE v.resource_id = d.resource_id
        ), '[]'::jsonb)) INTO payload
    FROM arkkan.resource_definitions AS d
    JOIN arkkan.resource_types AS t USING (type_id) WHERE d.slug = $1;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('get_resource_info', 'error', NULL, 'Resource does not exist.');
    END IF;
    RETURN arkkan.api_response('get_resource_info', 'success', payload, NULL);
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.get_resource_info(text) FROM PUBLIC;
