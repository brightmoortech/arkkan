CREATE FUNCTION arkkan_api.update_resource_type(slug text, description text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response(
            'update_resource_type', 'error', NULL,
            'Resource type slug must be nonblank.'
        );
    END IF;
    UPDATE arkkan.resource_types AS t SET description = $2 WHERE t.slug = $1;
    IF NOT FOUND THEN
        RETURN arkkan.api_response(
            'update_resource_type', 'error', NULL,
            'Resource type does not exist.'
        );
    END IF;
    RETURN arkkan.api_response('update_resource_type', 'success', pg_catalog.jsonb_build_object('slug', $1, 'description', $2), NULL);
EXCEPTION WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response(
        'update_resource_type', 'error', NULL,
        'Concurrent change prevented the operation; retry the transaction.'
    );
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.update_resource_type(text, text) FROM PUBLIC;
