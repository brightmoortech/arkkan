CREATE FUNCTION arkkan_api.list_resources_matching_type(type_slug text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    payload jsonb;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response('list_resources_matching_type', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    SELECT COALESCE((
        SELECT pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
            'name', d.name, 'slug', d.slug, 'description', d.description) ORDER BY d.slug)
        FROM arkkan.resource_definitions AS d WHERE d.type_id = t.type_id
    ), '[]'::jsonb) INTO payload
    FROM arkkan.resource_types AS t WHERE t.slug = $1;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('list_resources_matching_type', 'error', NULL, 'Resource type does not exist.');
    END IF;
    RETURN arkkan.api_response('list_resources_matching_type', 'success', payload, NULL);
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.list_resources_matching_type(text) FROM PUBLIC;
