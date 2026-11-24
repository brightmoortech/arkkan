DO $migration$
BEGIN
    IF pg_catalog.to_regprocedure('arkkan.reject_resource_definitions_change()') IS NULL THEN
        CREATE FUNCTION arkkan.reject_resource_definitions_change()
        RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog
        AS $body$
BEGIN
    IF NEW.resource_id IS DISTINCT FROM OLD.resource_id
       OR NEW.slug IS DISTINCT FROM OLD.slug
       OR NEW.type_id IS DISTINCT FROM OLD.type_id THEN
        RAISE EXCEPTION 'Immutable resource field cannot change.';
    END IF;
    RETURN NEW;
END;
$body$;
        REVOKE ALL ON FUNCTION arkkan.reject_resource_definitions_change() FROM PUBLIC;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger
        WHERE tgrelid = 'arkkan.resource_definitions'::regclass AND tgname = 'protect_resource_definitions_immutable'
    ) THEN
        CREATE TRIGGER protect_resource_definitions_immutable
        BEFORE UPDATE ON arkkan.resource_definitions
        FOR EACH ROW EXECUTE FUNCTION arkkan.reject_resource_definitions_change();
        ALTER TABLE arkkan.resource_definitions ENABLE ALWAYS TRIGGER protect_resource_definitions_immutable;
    END IF;
END;
$migration$;
