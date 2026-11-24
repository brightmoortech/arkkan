CREATE FUNCTION arkkan.api_transition_valid(source_state text, target_state text)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog
AS $body$
    SELECT COALESCE(CASE source_state
        WHEN 'enabled' THEN target_state IN ('enabled_default', 'disabled')
        WHEN 'enabled_default' THEN target_state IN ('enabled', 'disabled')
        WHEN 'disabled' THEN target_state IN ('enabled', 'enabled_default', 'obsolete')
        WHEN 'obsolete' THEN target_state = 'disabled'
        ELSE FALSE END, FALSE);
$body$;
REVOKE ALL ON FUNCTION arkkan.api_transition_valid(text, text) FROM PUBLIC;
