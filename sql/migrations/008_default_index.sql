CREATE UNIQUE INDEX IF NOT EXISTS resource_versions_one_default
ON arkkan.resource_versions (resource_id)
WHERE state = 'enabled_default';
