CREATE FUNCTION arkkan_api.set_resource_state(slug text, version text, target_state text, force boolean DEFAULT FALSE)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    current_state text;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) OR NOT arkkan.api_identifier_valid($2) THEN
        RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    IF NOT arkkan.api_state_valid($3) OR $4 IS NULL THEN
        RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'Target state and force flag must be valid non-null values.');
    END IF;
    SELECT d.resource_id INTO target_id FROM arkkan.resource_definitions AS d
    WHERE d.slug = $1 FOR UPDATE;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'Resource does not exist.');
    END IF;
    SELECT v.state INTO current_state FROM arkkan.resource_versions AS v
    WHERE v.resource_id = target_id AND v.version = $2;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'Resource version does not exist.');
    END IF;
    IF NOT arkkan.api_transition_valid(current_state, $3) THEN
        RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'State transition is not allowed.');
    END IF;
    IF current_state = 'enabled_default' AND NOT $4 THEN
        RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'Removing the default without a replacement requires force.');
    END IF;
    IF $3 = 'enabled_default' THEN
        UPDATE arkkan.resource_versions AS v SET state = 'enabled'
        WHERE v.resource_id = target_id AND v.state = 'enabled_default';
    END IF;
    UPDATE arkkan.resource_versions AS v SET state = $3
    WHERE v.resource_id = target_id AND v.version = $2;
    RETURN arkkan.api_response('set_resource_state', 'success', pg_catalog.jsonb_build_object('slug', $1, 'version', $2, 'state', $3), NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected OR unique_violation THEN
    RETURN arkkan.api_response('set_resource_state', 'error', NULL, 'Concurrent change prevented the operation; retry the transaction.');
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.set_resource_state(text, text, text, boolean) FROM PUBLIC;
