-- Begin transaction
BEGIN;

-- Create a temporary table to store the mapping
CREATE TEMP TABLE course_id_mapping (
    old_id INTEGER,
    new_id INTEGER
);

-- Store the IDs for reference
INSERT INTO course_id_mapping
SELECT 
    c_wrong.id as old_id,
    c_correct.id as new_id
FROM course c_wrong
CROSS JOIN course c_correct
WHERE c_wrong.course_name = 'ACTURIAL SCIENCE'
AND c_correct.course_name = 'ACTUARIAL SCIENCE';

-- Move any requirements from the wrong course to the correct course
UPDATE course_requirement
SET course_id = (SELECT new_id FROM course_id_mapping LIMIT 1)
WHERE course_id IN (SELECT old_id FROM course_id_mapping);

-- Delete the misspelled course
DELETE FROM course 
WHERE course_name = 'ACTURIAL SCIENCE';

-- Create a function to prevent future misspellings
CREATE OR REPLACE FUNCTION prevent_actuarial_misspelling()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.course_name ILIKE 'ACTURIAL%' THEN
        NEW.course_name = REPLACE(NEW.course_name, 'ACTURIAL', 'ACTUARIAL');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to prevent future misspellings
DROP TRIGGER IF EXISTS fix_actuarial_spelling ON course;
CREATE TRIGGER fix_actuarial_spelling
    BEFORE INSERT OR UPDATE ON course
    FOR EACH ROW
    EXECUTE FUNCTION prevent_actuarial_misspelling();

-- Log the change
CREATE TABLE IF NOT EXISTS course_name_changes (
    id SERIAL PRIMARY KEY,
    old_name VARCHAR(256),
    new_name VARCHAR(256),
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);

INSERT INTO course_name_changes (old_name, new_name, reason)
VALUES ('ACTURIAL SCIENCE', 'ACTUARIAL SCIENCE', 'Fixed spelling error and merged courses');

COMMIT;
