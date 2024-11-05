-- Start transaction
BEGIN;

-- Create new tables with same constraints as SQLAlchemy models
CREATE TABLE utme_requirement_template (
    id SERIAL PRIMARY KEY,
    requirements TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT utme_requirement_template_requirements_key UNIQUE (requirements)
);

CREATE TABLE direct_entry_requirement_template (
    id SERIAL PRIMARY KEY,
    requirements TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT direct_entry_requirement_template_requirements_key UNIQUE (requirements)
);

-- Add new columns to course_requirement
ALTER TABLE course_requirement 
ADD COLUMN utme_template_id INTEGER,
ADD COLUMN de_template_id INTEGER;

-- Populate template tables with distinct values
INSERT INTO utme_requirement_template (requirements)
SELECT DISTINCT utme_requirements 
FROM course_requirement 
WHERE utme_requirements IS NOT NULL;

INSERT INTO direct_entry_requirement_template (requirements)
SELECT DISTINCT direct_entry_requirements 
FROM course_requirement 
WHERE direct_entry_requirements IS NOT NULL;

-- Create temporary indexes to speed up the update
CREATE INDEX temp_idx_utme_req ON course_requirement(utme_requirements);
CREATE INDEX temp_idx_de_req ON course_requirement(direct_entry_requirements);

-- Update course_requirement with template references
WITH utme_mapping AS (
    SELECT id, requirements 
    FROM utme_requirement_template
)
UPDATE course_requirement cr
SET utme_template_id = utm.id
FROM utme_mapping utm
WHERE cr.utme_requirements = utm.requirements;

WITH de_mapping AS (
    SELECT id, requirements 
    FROM direct_entry_requirement_template
)
UPDATE course_requirement cr
SET de_template_id = dem.id
FROM de_mapping dem
WHERE cr.direct_entry_requirements = dem.requirements;

-- Verify data integrity
DO $$
DECLARE
    utme_count INTEGER;
    de_count INTEGER;
    original_utme_count INTEGER;
    original_de_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO original_utme_count 
    FROM course_requirement 
    WHERE utme_requirements IS NOT NULL;
    
    SELECT COUNT(*) INTO original_de_count 
    FROM course_requirement 
    WHERE direct_entry_requirements IS NOT NULL;
    
    SELECT COUNT(*) INTO utme_count 
    FROM course_requirement 
    WHERE utme_template_id IS NOT NULL;
    
    SELECT COUNT(*) INTO de_count 
    FROM course_requirement 
    WHERE de_template_id IS NOT NULL;
    
    IF utme_count != original_utme_count OR de_count != original_de_count THEN
        RAISE EXCEPTION 'Data migration verification failed';
    END IF;
END $$;

-- Add foreign key constraints
ALTER TABLE course_requirement
ADD CONSTRAINT fk_cr_utme_template 
FOREIGN KEY (utme_template_id) 
REFERENCES utme_requirement_template(id);

ALTER TABLE course_requirement
ADD CONSTRAINT fk_cr_de_template 
FOREIGN KEY (de_template_id) 
REFERENCES direct_entry_requirement_template(id);

-- Create composite index for template IDs
CREATE INDEX idx_course_requirement_template_ids 
ON course_requirement(utme_template_id, de_template_id);

-- Drop temporary indexes
DROP INDEX temp_idx_utme_req;
DROP INDEX temp_idx_de_req;

-- Optional: Drop old columns if migration is successful
ALTER TABLE course_requirement
DROP COLUMN utme_requirements,
DROP COLUMN direct_entry_requirements;

COMMIT;

-- Rollback script in case of failure
/*
BEGIN;
ALTER TABLE course_requirement DROP CONSTRAINT IF EXISTS fk_cr_utme_template;
ALTER TABLE course_requirement DROP CONSTRAINT IF EXISTS fk_cr_de_template;
DROP INDEX IF EXISTS idx_course_requirement_template_ids;
ALTER TABLE course_requirement DROP COLUMN IF EXISTS utme_template_id;
ALTER TABLE course_requirement DROP COLUMN IF EXISTS de_template_id;
DROP TABLE IF EXISTS utme_requirement_template;
DROP TABLE IF EXISTS direct_entry_requirement_template;
COMMIT;
*/