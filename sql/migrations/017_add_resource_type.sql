CREATE FUNCTION arkkan_api.add_resource_type(slug text, description text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog
AS $body$
DECLARE
    new_type_id uuid;
BEGIN
    IF NOT arkkan.api_identifier_valid($1) THEN
        RETURN arkkan.api_response(
            'add_resource_type', 'error', NULL,
            'Resource type slug must be nonblank.'
        );
    END IF;
    INSERT INTO arkkan.resource_types (slug, description, is_system)
    VALUES ($1, $2, FALSE) RETURNING type_id INTO new_type_id;
    RETURN arkkan.api_response('add_resource_type', 'success', pg_catalog.jsonb_build_object('type_id', new_type_id, 'slug', $1), NULL);
EXCEPTION WHEN unique_violation THEN
    RETURN arkkan.api_response('add_resource_type', 'error', NULL, 'Resource type already exists.');
WHEN serialization_failure OR deadlock_detected THEN
    RETURN arkkan.api_response(
        'add_resource_type', 'error', NULL,
        'Concurrent change prevented the operation; retry the transaction.'
    );
END;
$body$;
REVOKE ALL ON FUNCTION arkkan_api.add_resource_type(text, text) FROM PUBLIC;
