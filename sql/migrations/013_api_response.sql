CREATE FUNCTION arkkan.api_response(
    operation_name text, result text, data jsonb, reason text
)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path = pg_catalog
AS $body$
BEGIN
    IF operation_name IS NULL OR operation_name !~ '[^[:space:]]' THEN
        RAISE EXCEPTION 'Invalid internal response operation name.' USING ERRCODE = '22023';
    END IF;
    IF result = 'success'
       AND pg_catalog.jsonb_typeof(data) IN ('object', 'array')
       AND reason IS NULL THEN
        RETURN pg_catalog.jsonb_build_object(
            'operation_name', operation_name, 'message_type', 'response',
            'result', result, 'data', data
        );
    ELSIF result = 'error' AND data IS NULL AND reason ~ '[^[:space:]]' THEN
        RETURN pg_catalog.jsonb_build_object(
            'operation_name', operation_name, 'message_type', 'response',
            'result', result, 'reason', reason
        );
    END IF;
    -- Invalid internal calls are programming errors, not ordinary API failures.
    RAISE EXCEPTION 'Invalid internal response arguments.' USING ERRCODE = '22023';
END;
$body$;
REVOKE ALL ON FUNCTION arkkan.api_response(text, text, jsonb, text) FROM PUBLIC;
