CREATE FUNCTION arkkan_api.clean_up()
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    removed bigint;
    deleted_count bigint := 0;
BEGIN
    -- Acquire parent locks in UUID order, matching every resource mutation.
    -- The scan defines this call's resource set; overlapping additions can be
    -- ordered after cleanup. No table-wide lock or persistent work table is needed.
    FOR target_id IN SELECT d.resource_id FROM arkkan.resource_definitions AS d
                     ORDER BY d.resource_id FOR UPDATE
    LOOP
        DELETE FROM arkkan.resource_versions AS v
        WHERE v.resource_id = target_id AND v.state = 'obsolete';
        GET DIAGNOSTICS removed = ROW_COUNT;
        deleted_count := deleted_count + removed;
    END LOOP;
    RETURN arkkan.api_response('clean_up', 'success', pg_catalog.jsonb_build_object('deleted_count', deleted_count), NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response('clean_up', 'error', NULL, 'Concurrent change prevented the operation; retry the transaction.');
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.clean_up() FROM PUBLIC;
