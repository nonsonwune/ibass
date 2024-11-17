-- Analyze existing subject patterns
WITH ValidSubjects AS (
    SELECT DISTINCT subjects, COUNT(*) as usage_count
    FROM subject_requirement sr
    JOIN course_requirement cr ON sr.course_requirement_id = cr.id
    WHERE subjects NOT LIKE '%[Not Available]%'
    GROUP BY subjects
    HAVING COUNT(*) > 5
),
CourseSubjects AS (
    SELECT 
        c.course_name,
        c.standardized_name,
        sr.subjects,
        COUNT(*) OVER (PARTITION BY sr.subjects) as pattern_frequency
    FROM course_requirement cr
    JOIN course c ON cr.course_id = c.id
    JOIN subject_requirement sr ON sr.course_requirement_id = cr.id
    WHERE sr.subjects NOT LIKE '%[Not Available]%'
),
SubjectCombinations AS (
    SELECT 
        CASE 
            WHEN subjects LIKE '%Mathematics%' AND subjects LIKE '%Physics%' AND subjects LIKE '%Chemistry%' THEN 'MPC'
            WHEN subjects LIKE '%Mathematics%' AND subjects LIKE '%Physics%' AND subjects LIKE '%Biology%' THEN 'MPB'
            WHEN subjects LIKE '%Biology%' AND subjects LIKE '%Chemistry%' AND subjects LIKE '%Physics%' THEN 'BCP'
            WHEN subjects LIKE '%Mathematics%' AND subjects LIKE '%Economics%' THEN 'ME'
            WHEN subjects LIKE '%Literature%' AND subjects LIKE '%English%' THEN 'LE'
            ELSE 'Other'
        END as combination_type,
        subjects,
        COUNT(*) as frequency
    FROM ValidSubjects
    GROUP BY combination_type, subjects
)
SELECT 
    combination_type,
    subjects as subject_pattern,
    frequency,
    ROUND(frequency * 100.0 / SUM(frequency) OVER (PARTITION BY combination_type), 2) as percentage_in_type
FROM SubjectCombinations
ORDER BY combination_type, frequency DESC;

-- Analyze combination courses specifically
WITH CombinationCourses AS (
    SELECT 
        c.course_name,
        sr.subjects,
        SPLIT_PART(c.course_name, '/', 1) as primary_course,
        SPLIT_PART(c.course_name, '/', 2) as secondary_course
    FROM course c
    JOIN course_requirement cr ON c.id = cr.course_id
    LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
    WHERE c.course_name LIKE '%/%'
    AND sr.subjects NOT LIKE '%[Not Available]%'
)
SELECT 
    primary_course,
    secondary_course,
    array_agg(DISTINCT subjects) as subject_patterns,
    COUNT(*) as frequency
FROM CombinationCourses
GROUP BY primary_course, secondary_course
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

-- Create standardized subject mappings
CREATE TABLE IF NOT EXISTS standardized_subject_requirements (
    id SERIAL PRIMARY KEY,
    course_pattern TEXT NOT NULL,
    primary_subjects TEXT[] NOT NULL,
    alternative_subjects TEXT[] NOT NULL,
    min_subjects INTEGER NOT NULL DEFAULT 3,
    confidence_score NUMERIC NOT NULL DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert base patterns for main course categories
INSERT INTO standardized_subject_requirements 
    (course_pattern, primary_subjects, alternative_subjects, min_subjects, confidence_score)
VALUES
    -- Science & Engineering Base
    ('ENGINEERING%', 
     ARRAY['Mathematics', 'Physics', 'Chemistry'],
     ARRAY['Technical Drawing', 'Further Mathematics', 'Computer Science'],
     3, 0.95),
    
    -- Pure Sciences
    ('PHYSICS%',
     ARRAY['Physics', 'Mathematics', 'Chemistry'],
     ARRAY['Further Mathematics', 'Technical Drawing', 'Biology'],
     3, 0.90),
    
    ('CHEMISTRY%',
     ARRAY['Chemistry', 'Physics', 'Mathematics'],
     ARRAY['Biology', 'Agricultural Science', 'Technical Drawing'],
     3, 0.90),
    
    ('BIOLOGY%',
     ARRAY['Biology', 'Chemistry', 'Physics'],
     ARRAY['Mathematics', 'Agricultural Science', 'Geography'],
     3, 0.90),
    
    -- Computer Sciences
    ('COMPUTER%',
     ARRAY['Mathematics', 'Physics'],
     ARRAY['Chemistry', 'Biology', 'Economics', 'Further Mathematics'],
     3, 0.90),
    
    -- Business & Social Sciences
    ('ECONOMICS%',
     ARRAY['Mathematics', 'Economics'],
     ARRAY['Commerce', 'Government', 'Geography', 'Accounting'],
     3, 0.85),
    
    ('ACCOUNTING%',
     ARRAY['Mathematics', 'Economics', 'Commerce'],
     ARRAY['Accounting', 'Business Studies', 'Government'],
     3, 0.85),
    
    -- Arts & Languages
    ('ENGLISH%',
     ARRAY['Literature in English', 'English Language'],
     ARRAY['Government', 'History', 'CRS/IRS', 'French'],
     3, 0.80),
    
    -- Education
    ('EDUCATION%',
     ARRAY['English Language'],
     ARRAY['Mathematics', 'Biology', 'Chemistry', 'Physics', 'Economics', 'Literature', 'History', 'Geography'],
     4, 0.80);

-- Create a function to standardize subject requirements
CREATE OR REPLACE FUNCTION standardize_subject_requirement(
    p_course_name TEXT,
    p_existing_subjects TEXT
) RETURNS TABLE (
    standardized_subjects TEXT,
    confidence_score NUMERIC
) AS $$
DECLARE
    v_pattern RECORD;
    v_subjects TEXT;
    v_score NUMERIC;
BEGIN
    -- Find matching pattern
    SELECT * INTO v_pattern
    FROM standardized_subject_requirements
    WHERE p_course_name LIKE course_pattern
    ORDER BY confidence_score DESC
    LIMIT 1;
    
    IF FOUND THEN
        -- Build standardized subject string
        v_subjects := array_to_string(v_pattern.primary_subjects, ', ');
        
        IF v_pattern.min_subjects > array_length(v_pattern.primary_subjects, 1) THEN
            v_subjects := v_subjects || ' and any ' || 
                         (v_pattern.min_subjects - array_length(v_pattern.primary_subjects, 1))::TEXT || 
                         ' of ' || array_to_string(v_pattern.alternative_subjects, ', ');
        END IF;
        
        RETURN QUERY SELECT v_subjects, v_pattern.confidence_score;
    ELSE
        -- Return original subjects with lower confidence
        RETURN QUERY SELECT p_existing_subjects, 0.6::NUMERIC;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create view for subject requirement analysis
CREATE OR REPLACE VIEW subject_requirement_analysis AS
WITH SubjectStats AS (
    SELECT 
        c.course_name,
        sr.subjects,
        standardize_subject_requirement(c.course_name, sr.subjects) as standardized,
        COUNT(*) OVER (PARTITION BY sr.subjects) as pattern_frequency
    FROM course c
    JOIN course_requirement cr ON c.id = cr.course_id
    JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
    WHERE sr.subjects NOT LIKE '%[Not Available]%'
)
SELECT 
    course_name,
    subjects as current_subjects,
    (standardized).standardized_subjects as proposed_subjects,
    (standardized).confidence_score as confidence,
    pattern_frequency
FROM SubjectStats
ORDER BY (standardized).confidence_score DESC, pattern_frequency DESC;
