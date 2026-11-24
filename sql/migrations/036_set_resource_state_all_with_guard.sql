CREATE FUNCTION arkkan_api.set_resource_state_all_with_guard(slug text, source_state text, target_state text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
BEGIN
    RETURN arkkan.api_set_states('set_resource_state_all_with_guard', $1, $2, $3);
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.set_resource_state_all_with_guard(text, text, text) FROM PUBLIC;
