-- Create a temporary table to store the replacement mappings
CREATE TEMP TABLE requirement_replacements (
    course_category TEXT,
    pattern TEXT,
    replacement TEXT,
    confidence NUMERIC
);

-- Insert replacement patterns based on course categories
INSERT INTO requirement_replacements VALUES
-- Engineering Courses (High confidence)
('Engineering', '%ENGINEERING%', 'Mathematics, Physics and Chemistry.', 0.95),

-- Science Courses (High confidence)
('Science', '%PHYSICS%', 'Physics, Mathematics and Chemistry or Biology.', 0.90),
('Science', '%CHEMISTRY%', 'Chemistry and two (2) of Physics, Biology and Mathematics.', 0.90),
('Science', '%BIOLOGY%', 'Biology, Chemistry and Physics or Mathematics.', 0.90),
('Science', 'COMPUTER SCIENCE%', 'Mathematics, Physics and one (1) of Biology, Chemistry, Agric Science, Economics and Geography.', 0.90),

-- Business Courses (High confidence)
('Business', '%BUSINESS%', 'Mathematics, Economics and any other Social Science subject', 0.85),
('Business', '%ACCOUNTING%', 'Mathematics and two (2) of Geography, Commerce, Government, Principles of Accounts and Economics', 0.85),

-- Arts Courses (Medium confidence)
('Arts', '%ENGLISH%', 'Literature in English and any of Arts/Social Science subjects.', 0.80),
('Arts', '%LITERATURE%', 'Literature in English, one other Arts subject and another Arts or Social Science subject.', 0.80),

-- Education Courses (Medium confidence)
('Education', '%EDUCATION%', 'English Language and any other three (3) subjects.', 0.80);

-- Create backup of current requirements
CREATE TABLE IF NOT EXISTS requirement_backups_aggressive AS
SELECT cr.*, ut.requirements as utme_requirements, det.requirements as de_requirements
FROM course_requirement cr
LEFT JOIN utme_requirement_template ut ON cr.utme_template_id = ut.id
LEFT JOIN direct_entry_requirement_template det ON cr.de_template_id = det.id
WHERE ut.requirements LIKE '%[Not Available]%' OR det.requirements LIKE '%[Not Available]%';

-- Function to update requirements with logging
CREATE OR REPLACE FUNCTION update_requirement_with_confidence(
    p_course_name TEXT,
    p_requirement_type TEXT,
    p_new_requirement TEXT,
    p_confidence NUMERIC
) RETURNS VOID AS $$
BEGIN
    -- Update UTME requirements
    IF p_requirement_type = 'UTME' THEN
        UPDATE utme_requirement_template ut
        SET requirements = p_new_requirement,
            updated_at = CURRENT_TIMESTAMP
        FROM course_requirement cr
        JOIN course c ON cr.course_id = c.id
        WHERE cr.utme_template_id = ut.id
        AND c.course_name = p_course_name
        AND ut.requirements LIKE '%[Not Available]%';
    END IF;

    -- Update DE requirements
    IF p_requirement_type = 'DE' THEN
        UPDATE direct_entry_requirement_template det
        SET requirements = p_new_requirement,
            updated_at = CURRENT_TIMESTAMP
        FROM course_requirement cr
        JOIN course c ON cr.course_id = c.id
        WHERE cr.de_template_id = det.id
        AND c.course_name = p_course_name
        AND det.requirements LIKE '%[Not Available]%';
    END IF;

    -- Log the change
    INSERT INTO requirement_change_log (
        course_name,
        requirement_type,
        old_requirement,
        new_requirement,
        confidence_score,
        changed_at
    ) VALUES (
        p_course_name,
        p_requirement_type,
        '[Not Available]',
        p_new_requirement,
        p_confidence,
        CURRENT_TIMESTAMP
    );
END;
$$ LANGUAGE plpgsql;

-- Apply the aggressive replacements
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT DISTINCT 
            c.course_name,
            CASE 
                WHEN cr.utme_template_id IS NOT NULL THEN 'UTME'
                WHEN cr.de_template_id IS NOT NULL THEN 'DE'
            END as requirement_type,
            rr.replacement,
            rr.confidence
        FROM course_requirement cr
        JOIN course c ON cr.course_id = c.id
        JOIN requirement_replacements rr ON 
            c.course_name LIKE rr.pattern
        WHERE 
            (cr.utme_template_id IN (SELECT id FROM utme_requirement_template WHERE requirements LIKE '%[Not Available]%')
            OR cr.de_template_id IN (SELECT id FROM direct_entry_requirement_template WHERE requirements LIKE '%[Not Available]%'))
        ORDER BY rr.confidence DESC
    ) LOOP
        PERFORM update_requirement_with_confidence(
            r.course_name,
            r.requirement_type,
            r.replacement,
            r.confidence
        );
    END LOOP;
END;
$$;

-- Create summary views
CREATE OR REPLACE VIEW requirement_replacement_summary AS
SELECT 
    requirement_type,
    COUNT(*) as total_replacements,
    AVG(confidence_score) as avg_confidence,
    MIN(confidence_score) as min_confidence,
    MAX(confidence_score) as max_confidence
FROM requirement_change_log
GROUP BY requirement_type;

CREATE OR REPLACE VIEW remaining_not_available AS
SELECT 
    c.course_name,
    u.university_name,
    CASE 
        WHEN cr.utme_template_id IS NOT NULL THEN 'UTME'
        WHEN cr.de_template_id IS NOT NULL THEN 'DE'
    END as requirement_type
FROM course_requirement cr
JOIN course c ON cr.course_id = c.id
JOIN university u ON cr.university_id = u.id
WHERE 
    cr.utme_template_id IN (SELECT id FROM utme_requirement_template WHERE requirements LIKE '%[Not Available]%')
    OR cr.de_template_id IN (SELECT id FROM direct_entry_requirement_template WHERE requirements LIKE '%[Not Available]%');
