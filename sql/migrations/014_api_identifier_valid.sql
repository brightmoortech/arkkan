CREATE FUNCTION arkkan.api_identifier_valid(value text)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog
AS $body$
    SELECT COALESCE(value ~ '[^[:space:]]', FALSE);
$body$;
REVOKE ALL ON FUNCTION arkkan.api_identifier_valid(text) FROM PUBLIC;
