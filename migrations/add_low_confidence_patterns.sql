-- Add more specialized patterns for low-confidence combinations
INSERT INTO combination_course_patterns 
    (primary_course_pattern, secondary_course_pattern, combined_subjects, confidence_score)
VALUES
    -- Adult Education Specialized Combinations
    ('ADULT AND NON-FORMAL EDUCATION', 'POLITICAL SCIENCE',
     'Government/History and any two (2) Social Science subjects.', 0.75),
     
    ('ADULT AND NON-FORMAL EDUCATION', 'GEOGRAPHY',
     'Geography and any two (2) Social Science subjects.', 0.75),
     
    -- Religious Studies Advanced Patterns
    ('CHRISTIAN RELIGIOUS STUDIES', 'HISTORY',
     'Christian Religious Studies, History and one (1) Arts subject.', 0.75),
     
    ('ISLAMIC STUDIES', 'HISTORY',
     'Islamic Studies, History and one (1) Arts subject.', 0.75),
     
    -- Language & Literature Specialized
    ('HAUSA', 'LITERATURE',
     'Hausa, Literature in English and one (1) Arts subject.', 0.75),
     
    ('FULFULDE', 'LITERATURE',
     'Literature in English and any two (2) Arts subjects.', 0.75),
     
    -- Creative Arts Combinations
    ('CULTURAL AND CREATIVE ARTS', 'MUSIC',
     'Any three (3) Arts subjects including Literature in English.', 0.75),
     
    ('CULTURAL AND CREATIVE ARTS', 'FINE ARTS',
     'Any three (3) Arts subjects including Literature in English.', 0.75),
     
    -- Special Education Specialized
    ('SPECIAL NEEDS EDUCATION', 'ENGLISH',
     'Literature in English and any two (2) Arts subjects.', 0.75),
     
    ('SPECIAL NEEDS EDUCATION', 'MATHEMATICS',
     'Mathematics and any two (2) Science subjects.', 0.75),
     
    -- Indigenous Language Combinations
    ('IGBO', 'LINGUISTICS',
     'Igbo and any two (2) Arts subjects.', 0.75),
     
    ('HAUSA', 'LINGUISTICS',
     'Hausa and any two (2) Arts subjects.', 0.75),
     
    ('YORUBA', 'LINGUISTICS',
     'Yoruba and any two (2) Arts subjects.', 0.75),
     
    -- Social Science Combinations
    ('POLITICAL SCIENCE', 'SOCIOLOGY',
     'Government/History and any two (2) Social Science subjects.', 0.75),
     
    ('ECONOMICS', 'GEOGRAPHY',
     'Economics, Geography and one (1) Social Science subject.', 0.75);

-- Create a view for analyzing subject requirements by faculty
CREATE OR REPLACE VIEW subject_requirement_analysis AS
WITH CourseCategories AS (
    SELECT 
        CASE 
            WHEN course_name LIKE '%EDUCATION%' THEN 'Education'
            WHEN course_name LIKE '%ENGINEERING%' OR course_name LIKE '%TECHNOLOGY%' THEN 'Engineering'
            WHEN course_name LIKE '%SCIENCE%' OR course_name LIKE '%PHYSICS%' OR course_name LIKE '%CHEMISTRY%' OR course_name LIKE '%BIOLOGY%' THEN 'Science'
            WHEN course_name LIKE '%ARTS%' OR course_name LIKE '%LANGUAGE%' OR course_name LIKE '%LITERATURE%' THEN 'Arts'
            WHEN course_name LIKE '%ECONOMICS%' OR course_name LIKE '%BUSINESS%' OR course_name LIKE '%ACCOUNTING%' THEN 'Business'
            WHEN course_name LIKE '%SOCIAL%' OR course_name LIKE '%POLITICAL%' OR course_name LIKE '%HISTORY%' THEN 'Social Sciences'
            ELSE 'Other'
        END as faculty,
        c.course_name,
        sr.subjects
    FROM course c
    JOIN course_requirement cr ON c.id = cr.course_id
    JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
    WHERE c.course_name LIKE '%/%'
)
SELECT 
    faculty,
    COUNT(*) as total_courses,
    COUNT(DISTINCT CASE WHEN subjects != '[Not Available]' THEN course_name END) as defined_requirements,
    ROUND((COUNT(DISTINCT CASE WHEN subjects != '[Not Available]' THEN course_name END)::NUMERIC / 
           COUNT(*)::NUMERIC) * 100, 2) as completion_percentage
FROM CourseCategories
GROUP BY faculty
ORDER BY total_courses DESC;

-- Create validation rules for combination patterns
CREATE OR REPLACE FUNCTION validate_combination_requirement(
    p_subjects TEXT,
    p_primary_course TEXT,
    p_secondary_course TEXT
) RETURNS TABLE (
    is_valid BOOLEAN,
    validation_message TEXT
) AS $$
BEGIN
    -- Basic validation
    IF p_subjects IS NULL OR p_subjects = '[Not Available]' THEN
        RETURN QUERY SELECT FALSE, 'Subject requirements cannot be null or [Not Available]';
        RETURN;
    END IF;
    
    -- Validate subject count
    IF p_subjects NOT ILIKE '%three%' AND p_subjects NOT ILIKE '%two%' AND p_subjects NOT ILIKE '%one%' THEN
        RETURN QUERY SELECT FALSE, 'Subject requirement must specify the number of subjects required';
        RETURN;
    END IF;
    
    -- Validate subject categories
    IF p_subjects NOT ILIKE '%Arts%' AND p_subjects NOT ILIKE '%Science%' AND 
       p_subjects NOT ILIKE '%Social Science%' THEN
        RETURN QUERY SELECT FALSE, 'Subject requirement must specify subject categories (Arts, Science, or Social Science)';
        RETURN;
    END IF;
    
    -- Specific validations for different faculties
    IF p_primary_course ILIKE '%EDUCATION%' AND p_subjects NOT ILIKE '%Education%' THEN
        RETURN QUERY SELECT FALSE, 'Education combinations should mention education-related requirements';
        RETURN;
    END IF;
    
    IF (p_primary_course ILIKE '%LANGUAGE%' OR p_secondary_course ILIKE '%LANGUAGE%') AND 
       p_subjects NOT ILIKE '%Language%' AND p_subjects NOT ILIKE '%Literature%' THEN
        RETURN QUERY SELECT FALSE, 'Language combinations should mention language or literature requirements';
        RETURN;
    END IF;
    
    -- If all validations pass
    RETURN QUERY SELECT TRUE, 'Valid requirement pattern';
END;
$$ LANGUAGE plpgsql;
