CREATE FUNCTION arkkan_api.get_resource_content(slug text, version text, mode text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    payload jsonb;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) OR NOT arkkan.api_identifier_valid($2) THEN
        RETURN arkkan.api_response('get_resource_content', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    IF NOT arkkan.api_mode_valid($3) THEN
        RETURN arkkan.api_response('get_resource_content', 'error', NULL, 'Unknown retrieval mode.');
    END IF;
    SELECT pg_catalog.jsonb_build_object('slug', d.slug, 'version', v.version,
                                        'state', v.state, 'content', v.content)
    INTO payload
    FROM arkkan.resource_definitions AS d
    JOIN arkkan.resource_versions AS v USING (resource_id)
    WHERE d.slug = $1 AND v.state IN ('enabled', 'enabled_default')
      AND (v.version = $2 OR ($3 <> 'strict' AND v.state = 'enabled_default'))
    ORDER BY CASE WHEN $3 = 'default_priority' THEN v.state = 'enabled_default'
                  ELSE v.version = $2 END DESC
    LIMIT 1;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('get_resource_content', 'error', NULL, 'Requested resource version is unavailable.');
    END IF;
    RETURN arkkan.api_response('get_resource_content', 'success', payload, NULL);
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.get_resource_content(text, text, text) FROM PUBLIC;
