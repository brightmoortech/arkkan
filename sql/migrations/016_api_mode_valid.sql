CREATE FUNCTION arkkan.api_mode_valid(value text)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog
AS $body$
    SELECT COALESCE(value IN ('strict', 'version_priority', 'default_priority'), FALSE);
$body$;
REVOKE ALL ON FUNCTION arkkan.api_mode_valid(text) FROM PUBLIC;
