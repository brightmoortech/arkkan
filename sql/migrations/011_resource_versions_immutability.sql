DO $migration$
BEGIN
    IF pg_catalog.to_regprocedure('arkkan.reject_resource_versions_change()') IS NULL THEN
        CREATE FUNCTION arkkan.reject_resource_versions_change()
        RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog
        AS $body$
BEGIN
    IF NEW.version_id IS DISTINCT FROM OLD.version_id
       OR NEW.resource_id IS DISTINCT FROM OLD.resource_id
       OR NEW.version IS DISTINCT FROM OLD.version
       OR NEW.content IS DISTINCT FROM OLD.content
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Immutable resource field cannot change.';
    END IF;
    RETURN NEW;
END;
$body$;
        REVOKE ALL ON FUNCTION arkkan.reject_resource_versions_change() FROM PUBLIC;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger
        WHERE tgrelid = 'arkkan.resource_versions'::regclass AND tgname = 'protect_resource_versions_immutable'
    ) THEN
        CREATE TRIGGER protect_resource_versions_immutable
        BEFORE UPDATE ON arkkan.resource_versions
        FOR EACH ROW EXECUTE FUNCTION arkkan.reject_resource_versions_change();
        ALTER TABLE arkkan.resource_versions ENABLE ALWAYS TRIGGER protect_resource_versions_immutable;
    END IF;
END;
$migration$;
