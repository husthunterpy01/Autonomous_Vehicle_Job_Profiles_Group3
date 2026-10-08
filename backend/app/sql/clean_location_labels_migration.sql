-- Cleans location names that kept page furniture from a career site: a leading
-- "Location:" label ("Location: Budapest, Hungary") or a trailing "+2 more"
-- count ("Gothenburg +1 more"). New names are cleaned during sync and job
-- creation; this fixes the rows that already exist. When the cleaned name is
-- already another location, the jobs move to it and the dirty row is deleted.
-- Apply to the BACKEND database. Repeatable; it only touches dirty rows.
-- If the country column exists, run `python -m app.refresh_location_countries`
-- afterwards.
BEGIN;
CREATE TEMP TABLE _location_clean ON COMMIT DROP AS
SELECT location_id,
       btrim(regexp_replace(regexp_replace(regexp_replace(name, '^\s*location\s*:\s*', '', 'i'),
                                           '\s*\+\s*\d+\s*more\s*$', '', 'i'), '\s+', ' ', 'g')) AS clean_name
FROM location
WHERE name ~* '^\s*location\s*:' OR name ~* '\+\s*\d+\s*more\s*$';

DELETE FROM _location_clean WHERE clean_name = '';

-- Jobs of a dirty row whose cleaned name already exists move to that row.
INSERT INTO job_location (job_id, location_id)
SELECT jl.job_id, existing.location_id
FROM _location_clean c
JOIN job_location jl ON jl.location_id = c.location_id
JOIN location existing ON existing.normalized_name = lower(c.clean_name) AND existing.location_id <> c.location_id
ON CONFLICT DO NOTHING;

DELETE FROM job_location
WHERE location_id IN (
    SELECT c.location_id FROM _location_clean c
    JOIN location existing ON existing.normalized_name = lower(c.clean_name) AND existing.location_id <> c.location_id
);
DELETE FROM location
WHERE location_id IN (
    SELECT c.location_id FROM _location_clean c
    JOIN location existing ON existing.normalized_name = lower(c.clean_name) AND existing.location_id <> c.location_id
);

-- The rest are renamed in place.
UPDATE location l
SET name = c.clean_name, normalized_name = lower(c.clean_name)
FROM _location_clean c
WHERE l.location_id = c.location_id;
COMMIT;
