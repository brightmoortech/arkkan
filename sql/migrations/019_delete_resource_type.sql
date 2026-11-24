CREATE FUNCTION arkkan_api.delete_resource_type(slug text)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    target_id uuid;
    protected boolean;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response(
            'delete_resource_type', 'error', NULL,
            'Resource type slug must be nonblank.'
        );
    END IF;
    -- Lock before checking references: concurrent creation must acquire the
    -- foreign key lock and cannot race this eligibility check and deletion.
    SELECT t.type_id, t.is_system INTO target_id, protected
    FROM arkkan.resource_types AS t WHERE t.slug = $1 FOR UPDATE;
    IF NOT FOUND THEN
        RETURN arkkan.api_response(
            'delete_resource_type', 'error', NULL,
            'Resource type does not exist.'
        );
    END IF;
    IF protected THEN
        RETURN arkkan.api_response(
            'delete_resource_type', 'error', NULL,
            'Predefined resource types cannot be deleted.'
        );
    END IF;
    IF EXISTS (SELECT 1 FROM arkkan.resource_definitions AS d WHERE d.type_id = target_id) THEN
        RETURN arkkan.api_response(
            'delete_resource_type', 'error', NULL,
            'Resource type is referenced by a resource.'
        );
    END IF;
    DELETE FROM arkkan.resource_types AS t WHERE t.type_id = target_id;
    RETURN arkkan.api_response('delete_resource_type', 'success', pg_catalog.jsonb_build_object('slug', $1), NULL);
EXCEPTION WHEN foreign_key_violation THEN
    RETURN arkkan.api_response(
        'delete_resource_type', 'error', NULL,
        'Resource type is referenced by a resource.'
    );
WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response(
        'delete_resource_type', 'error', NULL,
        'Concurrent change prevented the operation; retry the transaction.'
    );
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.delete_resource_type(text) FROM PUBLIC;
