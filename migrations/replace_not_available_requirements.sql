-- Migration to replace [Not Available] requirements
-- This migration includes safety checks and rollback capabilities

BEGIN;

-- Create backup tables
CREATE TABLE course_requirement_backup_20240117 AS 
SELECT * FROM course_requirement WHERE utme_template_id = 1856 OR de_template_id = 1133;

-- Create changelog table
CREATE TABLE requirement_change_log (
    id SERIAL PRIMARY KEY,
    course_requirement_id INTEGER,
    course_name TEXT,
    university_name TEXT,
    old_utme_id INTEGER,
    new_utme_id INTEGER,
    old_de_id INTEGER,
    new_de_id INTEGER,
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_type TEXT,
    confidence_score FLOAT
);

-- Function to update requirements with logging
CREATE OR REPLACE FUNCTION update_requirement_with_log(
    p_course_requirement_id INTEGER,
    p_new_utme_id INTEGER,
    p_new_de_id INTEGER,
    p_confidence_score FLOAT
) RETURNS VOID AS $$
DECLARE
    v_course_name TEXT;
    v_university_name TEXT;
    v_old_utme_id INTEGER;
    v_old_de_id INTEGER;
BEGIN
    -- Get current values
    SELECT 
        c.course_name,
        u.university_name,
        cr.utme_template_id,
        cr.de_template_id
    INTO 
        v_course_name,
        v_university_name,
        v_old_utme_id,
        v_old_de_id
    FROM course_requirement cr
    JOIN course c ON cr.course_id = c.id
    JOIN university u ON cr.university_id = u.id
    WHERE cr.id = p_course_requirement_id;

    -- Update requirement
    UPDATE course_requirement
    SET 
        utme_template_id = COALESCE(p_new_utme_id, utme_template_id),
        de_template_id = COALESCE(p_new_de_id, de_template_id)
    WHERE id = p_course_requirement_id;

    -- Log the change
    INSERT INTO requirement_change_log (
        course_requirement_id,
        course_name,
        university_name,
        old_utme_id,
        new_utme_id,
        old_de_id,
        new_de_id,
        change_type,
        confidence_score
    ) VALUES (
        p_course_requirement_id,
        v_course_name,
        v_university_name,
        v_old_utme_id,
        p_new_utme_id,
        v_old_de_id,
        p_new_de_id,
        'Automated replacement',
        p_confidence_score
    );
END;
$$ LANGUAGE plpgsql;

-- Update requirements based on mapping (high confidence only)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT 
            cr.id as requirement_id,
            rm.replacement_utme_id,
            rm.replacement_de_id,
            rm.confidence_score
        FROM course_requirement cr
        JOIN course c ON cr.course_id = c.id
        JOIN requirement_replacement_map rm ON c.normalized_name = rm.course_pattern
        WHERE (cr.utme_template_id = 1856 OR cr.de_template_id = 1133)
        AND rm.confidence_score >= 0.8
        AND NOT rm.applied
    ) LOOP
        PERFORM update_requirement_with_log(
            r.requirement_id,
            r.replacement_utme_id,
            r.replacement_de_id,
            r.confidence_score
        );
    END LOOP;
END $$;

-- Update replacement map status
UPDATE requirement_replacement_map
SET applied = true, updated_at = CURRENT_TIMESTAMP
WHERE confidence_score >= 0.8;

-- Verify changes
DO $$
DECLARE
    changed_count INTEGER;
    error_count INTEGER;
BEGIN
    -- Count successful changes
    SELECT COUNT(*) INTO changed_count
    FROM requirement_change_log
    WHERE change_date >= CURRENT_DATE;

    -- Check for any errors (requirements still pointing to [Not Available])
    SELECT COUNT(*) INTO error_count
    FROM course_requirement cr
    JOIN requirement_change_log rcl ON cr.id = rcl.course_requirement_id
    WHERE (cr.utme_template_id = 1856 OR cr.de_template_id = 1133)
    AND rcl.change_date >= CURRENT_DATE;

    IF error_count > 0 THEN
        RAISE EXCEPTION 'Migration verification failed: % requirements still have [Not Available]', error_count;
    END IF;

    RAISE NOTICE 'Successfully updated % requirements', changed_count;
END $$;

-- Create views for monitoring and reporting
CREATE OR REPLACE VIEW requirement_change_summary AS
SELECT 
    course_name,
    university_name,
    COUNT(*) as change_count,
    AVG(confidence_score) as avg_confidence,
    MIN(change_date) as first_change,
    MAX(change_date) as last_change
FROM requirement_change_log
GROUP BY course_name, university_name;

CREATE OR REPLACE VIEW remaining_not_available AS
SELECT 
    c.course_name,
    u.university_name,
    CASE 
        WHEN cr.utme_template_id = 1856 THEN 'UTME'
        WHEN cr.de_template_id = 1133 THEN 'DE'
        ELSE 'Both'
    END as requirement_type
FROM course_requirement cr
JOIN course c ON cr.course_id = c.id
JOIN university u ON cr.university_id = u.id
WHERE cr.utme_template_id = 1856 OR cr.de_template_id = 1133;

COMMIT;
