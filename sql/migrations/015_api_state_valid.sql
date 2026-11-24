CREATE FUNCTION arkkan.api_state_valid(value text)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog
AS $body$
    SELECT COALESCE(value IN ('enabled', 'enabled_default', 'disabled', 'obsolete'), FALSE);
$body$;
REVOKE ALL ON FUNCTION arkkan.api_state_valid(text) FROM PUBLIC;
