DO $migration$
BEGIN
    IF pg_catalog.to_regprocedure('arkkan.reject_resource_types_change()') IS NULL THEN
        CREATE FUNCTION arkkan.reject_resource_types_change()
        RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog
        AS $body$
BEGIN
    IF NEW.type_id IS DISTINCT FROM OLD.type_id
       OR NEW.slug IS DISTINCT FROM OLD.slug
       OR NEW.is_system IS DISTINCT FROM OLD.is_system THEN
        RAISE EXCEPTION 'Immutable resource field cannot change.';
    END IF;
    RETURN NEW;
END;
$body$;
        REVOKE ALL ON FUNCTION arkkan.reject_resource_types_change() FROM PUBLIC;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger
        WHERE tgrelid = 'arkkan.resource_types'::regclass AND tgname = 'protect_resource_types_immutable'
    ) THEN
        CREATE TRIGGER protect_resource_types_immutable
        BEFORE UPDATE ON arkkan.resource_types
        FOR EACH ROW EXECUTE FUNCTION arkkan.reject_resource_types_change();
        ALTER TABLE arkkan.resource_types ENABLE ALWAYS TRIGGER protect_resource_types_immutable;
    END IF;
END;
$migration$;
