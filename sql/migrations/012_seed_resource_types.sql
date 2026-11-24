INSERT INTO arkkan.resource_types (slug, description, is_system)
VALUES (%s, %s, TRUE)
ON CONFLICT (slug) DO NOTHING;
