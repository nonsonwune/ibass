-- Create a table to store combination course patterns
CREATE TABLE IF NOT EXISTS combination_course_patterns (
    id SERIAL PRIMARY KEY,
    primary_course_pattern TEXT NOT NULL,
    secondary_course_pattern TEXT NOT NULL,
    combined_subjects TEXT NOT NULL,
    confidence_score NUMERIC NOT NULL DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert common combination patterns
INSERT INTO combination_course_patterns 
    (primary_course_pattern, secondary_course_pattern, combined_subjects, confidence_score)
VALUES
    -- Language Combinations
    ('ENGLISH', 'LITERATURE%', 
     'Literature in English and any two (2) Arts subjects.', 0.90),
    
    ('ENGLISH', '%LANGUAGE%', 
     'Literature in English, the specified Language, and one other Arts subject.', 0.85),
    
    -- Education Combinations
    ('EDUCATION', 'MATHEMATICS%', 
     'Mathematics and any two (2) Science subjects.', 0.90),
    
    ('EDUCATION', 'PHYSICS%', 
     'Physics, Mathematics and one (1) Science subject.', 0.90),
    
    ('EDUCATION', 'CHEMISTRY%', 
     'Chemistry and any two (2) of Physics, Biology and Mathematics.', 0.90),
    
    ('EDUCATION', 'BIOLOGY%', 
     'Biology and any two (2) of Physics, Chemistry and Mathematics.', 0.90),
    
    -- Computer Science Combinations
    ('COMPUTER%', 'MATHEMATICS%', 
     'Mathematics, Physics and one (1) of Chemistry, Economics, or Further Mathematics.', 0.90),
    
    ('COMPUTER%', 'PHYSICS%', 
     'Physics, Mathematics and one (1) Science subject.', 0.90),
    
    -- Social Science Combinations
    ('ECONOMICS%', 'STATISTICS%', 
     'Mathematics, Economics and one (1) Social Science subject.', 0.85),
    
    ('POLITICAL%', 'HISTORY%', 
     'Government/History and any two (2) Social Science subjects.', 0.85),
    
    -- Arts Combinations
    ('THEATRE%', 'CREATIVE%', 
     'Literature in English and any two (2) Arts subjects.', 0.80),
    
    ('MUSIC%', 'CREATIVE%', 
     'English Language and any two (2) Arts subjects.', 0.80),
    
    -- Language & Social Science
    ('ENGLISH%', 'ECONOMICS%', 
     'Literature in English, Economics and one (1) Social Science subject.', 0.85),
    
    ('HISTORY%', 'INTERNATIONAL%', 
     'Government/History and any two (2) Social Science subjects.', 0.85);

-- Function to handle combination course requirements
CREATE OR REPLACE FUNCTION get_combination_requirement(
    p_course_name TEXT
) RETURNS TABLE (
    combined_requirement TEXT,
    confidence_score NUMERIC
) AS $$
DECLARE
    v_primary TEXT;
    v_secondary TEXT;
    v_pattern RECORD;
    v_result RECORD;
BEGIN
    -- Split the course name
    v_primary := SPLIT_PART(p_course_name, '/', 1);
    v_secondary := SPLIT_PART(p_course_name, '/', 2);
    
    -- Try to find a matching pattern
    SELECT * INTO v_pattern
    FROM combination_course_patterns
    WHERE (v_primary LIKE primary_course_pattern AND v_secondary LIKE secondary_course_pattern)
       OR (v_secondary LIKE primary_course_pattern AND v_primary LIKE secondary_course_pattern)
    ORDER BY confidence_score DESC
    LIMIT 1;
    
    IF FOUND THEN
        RETURN QUERY SELECT v_pattern.combined_subjects, v_pattern.confidence_score;
    ELSE
        -- Try to find individual patterns and combine them
        SELECT 
            CASE 
                WHEN p.standardized_subjects = s.standardized_subjects THEN 
                    p.standardized_subjects
                ELSE 
                    'Combined requirement: ' || p.standardized_subjects || ' OR ' || s.standardized_subjects
            END as combined_req,
            LEAST(p.confidence_score, s.confidence_score) * 0.9 as conf_score
        INTO v_result
        FROM standardize_subject_requirement(v_primary, '[Not Available]') p,
             standardize_subject_requirement(v_secondary, '[Not Available]') s
        LIMIT 1;
        
        IF FOUND THEN
            RETURN QUERY SELECT v_result.combined_req, v_result.conf_score;
        ELSE
            RETURN QUERY SELECT 'No requirement found'::TEXT, 0.0::NUMERIC;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create a view to analyze combination courses
CREATE OR REPLACE VIEW combination_course_analysis AS
WITH CombinationCourses AS (
    SELECT 
        c.course_name,
        SPLIT_PART(c.course_name, '/', 1) as primary_course,
        SPLIT_PART(c.course_name, '/', 2) as secondary_course,
        sr.subjects as current_subjects,
        get_combination_requirement(c.course_name) as proposed_requirement
    FROM course c
    JOIN course_requirement cr ON c.id = cr.course_id
    LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
    WHERE c.course_name LIKE '%/%'
)
SELECT 
    course_name,
    primary_course,
    secondary_course,
    current_subjects,
    (proposed_requirement).combined_requirement as proposed_subjects,
    (proposed_requirement).confidence_score as confidence
FROM CombinationCourses
ORDER BY (proposed_requirement).confidence_score DESC;

-- Function to update combination course requirements
CREATE OR REPLACE FUNCTION update_combination_requirement(
    p_course_name TEXT,
    p_requirement_type TEXT
) RETURNS VOID AS $$
DECLARE
    v_requirement RECORD;
BEGIN
    SELECT * INTO v_requirement 
    FROM get_combination_requirement(p_course_name);
    
    IF FOUND AND v_requirement.confidence_score >= 0.8 THEN
        PERFORM update_requirement_with_confidence(
            p_course_name,
            p_requirement_type,
            v_requirement.combined_requirement,
            v_requirement.confidence_score
        );
    END IF;
END;
$$ LANGUAGE plpgsql;
