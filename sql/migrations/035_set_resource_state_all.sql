CREATE FUNCTION arkkan_api.set_resource_state_all(slug text, target_state text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
BEGIN
    RETURN arkkan.api_set_states('set_resource_state_all', $1, NULL, $2);
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.set_resource_state_all(text, text) FROM PUBLIC;
