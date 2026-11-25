-- All functions exist and have passed catalog verification before exposure.
DO $grant$
BEGIN
    EXECUTE pg_catalog.format('GRANT CONNECT ON DATABASE %I TO arkkan_admin, arkkan_user',
                              pg_catalog.current_database());
END;
$grant$;
GRANT USAGE ON SCHEMA arkkan_api TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.add_resource_type(text, text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.update_resource_type(text, text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.delete_resource_type(text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.add_resource(text, text, text, text, text, text, text, text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.update_resource(text, jsonb, text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.get_resource_content(text, text, text) TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.get_resource_content(text, text) TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.get_resource_content(text) TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.list_resources_matching_type(text) TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.get_resource_version_default(text) TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.get_resource_info(text) TO arkkan_admin, arkkan_user;
GRANT EXECUTE ON FUNCTION arkkan_api.delete_resource_version(text, text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.delete_resource_version_all(text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.clean_up() TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.delete_resource(text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.set_resource_state(text, text, text, boolean) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.set_resource_state_all(text, text) TO arkkan_admin;
GRANT EXECUTE ON FUNCTION arkkan_api.set_resource_state_all_with_guard(text, text, text) TO arkkan_admin;
