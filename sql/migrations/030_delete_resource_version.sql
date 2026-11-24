CREATE FUNCTION arkkan_api.delete_resource_version(slug text, version text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    current_state text;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) OR NOT arkkan.api_identifier_valid($2) THEN
        RETURN arkkan.api_response('delete_resource_version', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    SELECT d.resource_id INTO target_id FROM arkkan.resource_definitions AS d
    WHERE d.slug = $1 FOR UPDATE;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('delete_resource_version', 'error', NULL, 'Resource does not exist.');
    END IF;
    SELECT v.state INTO current_state FROM arkkan.resource_versions AS v
    WHERE v.resource_id = target_id AND v.version = $2;
    IF NOT FOUND OR current_state <> 'obsolete' THEN
        RETURN arkkan.api_response('delete_resource_version', 'error', NULL, 'Only an existing obsolete version can be deleted.');
    END IF;
    DELETE FROM arkkan.resource_versions AS v WHERE v.resource_id = target_id AND v.version = $2;
    RETURN arkkan.api_response('delete_resource_version', 'success', pg_catalog.jsonb_build_object('slug', $1, 'version', $2), NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response('delete_resource_version', 'error', NULL, 'Concurrent change prevented the operation; retry the transaction.');
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.delete_resource_version(text, text) FROM PUBLIC;
