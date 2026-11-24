CREATE FUNCTION arkkan_api.get_resource_version_default(slug text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    payload jsonb;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response('get_resource_version_default', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    SELECT pg_catalog.jsonb_build_object('slug', d.slug, 'version', v.version)
    INTO payload FROM arkkan.resource_definitions AS d
    JOIN arkkan.resource_versions AS v USING (resource_id)
    WHERE d.slug = $1 AND v.state = 'enabled_default';
    IF NOT FOUND THEN
        RETURN arkkan.api_response('get_resource_version_default', 'error', NULL, 'Resource or its default does not exist.');
    END IF;
    RETURN arkkan.api_response('get_resource_version_default', 'success', payload, NULL);
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.get_resource_version_default(text) FROM PUBLIC;
