CREATE FUNCTION arkkan_api.get_resource_content(slug text, version text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
BEGIN
    RETURN arkkan_api.get_resource_content($1, $2, 'strict');
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.get_resource_content(text, text) FROM PUBLIC;
