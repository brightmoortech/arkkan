CREATE FUNCTION arkkan.api_set_states(operation_name text, slug text, source_state text, target_state text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    selected_count bigint;
    selected_ids uuid[];
BEGIN
    IF $1 IS NULL OR $1 NOT IN ('set_resource_state_all', 'set_resource_state_all_with_guard')
       OR ($1 = 'set_resource_state_all' AND $3 IS NOT NULL) THEN
        RAISE EXCEPTION 'Invalid internal state operation.' USING ERRCODE = '22023';
    END IF;
    IF NOT arkkan.api_identifier_valid($2) OR NOT arkkan.api_state_valid($4)
       OR ($1 = 'set_resource_state_all_with_guard' AND NOT arkkan.api_state_valid($3)) THEN
        RETURN arkkan.api_response($1, 'error', NULL, 'Invalid resource identifier or state.');
    END IF;
    SELECT d.resource_id INTO target_id FROM arkkan.resource_definitions AS d
    WHERE d.slug = $2 FOR UPDATE;
    IF NOT FOUND THEN
        RETURN arkkan.api_response($1, 'error', NULL, 'Resource does not exist.');
    END IF;
    SELECT count(*), COALESCE(pg_catalog.array_agg(v.version_id), '{}'::uuid[])
    INTO selected_count, selected_ids FROM arkkan.resource_versions AS v
    WHERE v.resource_id = target_id AND ($3 IS NULL OR v.state = $3);
    IF EXISTS (
        SELECT 1 FROM arkkan.resource_versions AS v
        WHERE v.resource_id = target_id AND ($3 IS NULL OR v.state = $3)
          AND (NOT arkkan.api_transition_valid(v.state, $4)
               OR (v.state = 'enabled_default' AND $4 <> 'enabled_default'))
    ) OR ($4 = 'enabled_default' AND selected_count > 1) THEN
        RETURN arkkan.api_response($1, 'error', NULL, 'Bulk change violates transition or default policy.');
    END IF;
    IF selected_count > 0 THEN
        IF $4 = 'enabled_default' THEN
            UPDATE arkkan.resource_versions AS v SET state = 'enabled'
            WHERE v.resource_id = target_id AND v.state = 'enabled_default';
        END IF;
        -- Freeze membership before default demotion, which can itself create
        -- a row in source_state (enabled) outside the requested selection.
        UPDATE arkkan.resource_versions AS v SET state = $4
        WHERE v.version_id = ANY(selected_ids);
    END IF;
    RETURN arkkan.api_response($1, 'success',
        pg_catalog.jsonb_build_object('slug', $2, 'changed_count', selected_count), NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected OR unique_violation THEN
    RETURN arkkan.api_response($1, 'error', NULL, 'Concurrent change prevented the operation; retry the transaction.');
END;
$body$;
REVOKE ALL ON FUNCTION arkkan.api_set_states(text, text, text, text) FROM PUBLIC;
