CREATE FUNCTION arkkan_api.delete_resource_version_all(slug text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    deleted_count bigint;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response('delete_resource_version_all', 'error', NULL, 'Required identifiers must be nonblank.');
    END IF;
    SELECT d.resource_id INTO target_id FROM arkkan.resource_definitions AS d
    WHERE d.slug = $1 FOR UPDATE;
    IF NOT FOUND THEN
        RETURN arkkan.api_response('delete_resource_version_all', 'error', NULL, 'Resource does not exist.');
    END IF;
    DELETE FROM arkkan.resource_versions AS v WHERE v.resource_id = target_id AND v.state = 'obsolete';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN arkkan.api_response('delete_resource_version_all', 'success', pg_catalog.jsonb_build_object('slug', $1, 'deleted_count', deleted_count), NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response('delete_resource_version_all', 'error', NULL, 'Concurrent change prevented the operation; retry the transaction.');
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.delete_resource_version_all(text) FROM PUBLIC;
