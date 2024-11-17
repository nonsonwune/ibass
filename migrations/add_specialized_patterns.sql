-- Add specialized patterns for combination courses based on analysis
INSERT INTO combination_course_patterns 
    (primary_course_pattern, secondary_course_pattern, combined_subjects, confidence_score)
VALUES
    -- Language & Social Studies Combinations
    ('ENGLISH', 'SOCIAL STUDIES', 
     'Literature in English, Government/History and one (1) Social Science subject.', 0.85),
    
    ('ENGLISH', 'POLITICAL SCIENCE', 
     'Literature in English, Government/History and one (1) Social Science subject.', 0.85),
    
    ('ENGLISH', 'ECONOMICS', 
     'Literature in English, Economics and one (1) Social Science subject.', 0.85),
    
    -- Adult Education Combinations
    ('ADULT AND NON-FORMAL EDUCATION', 'SOCIAL STUDIES',
     'Any three (3) Social Science subjects including Government/History.', 0.80),
    
    ('ADULT AND NON-FORMAL EDUCATION', 'ECONOMICS',
     'Economics and any two (2) Social Science subjects.', 0.80),
    
    -- Religious Studies Combinations
    ('ARABIC', 'ISLAMIC STUDIES',
     'Arabic, Islamic Studies and one (1) Arts subject.', 0.85),
    
    ('CHRISTIAN RELIGIOUS STUDIES', 'SOCIAL STUDIES',
     'Christian Religious Studies and any two (2) Arts or Social Science subjects.', 0.80),
    
    ('ISLAMIC STUDIES', 'ARABIC',
     'Arabic, Islamic Studies and one (1) Arts subject.', 0.85),
    
    -- Language & Cultural Combinations
    ('HAUSA', 'SOCIAL STUDIES',
     'Hausa and any two (2) Arts or Social Science subjects.', 0.80),
    
    ('FULFULDE', 'SOCIAL STUDIES',
     'Any three (3) Arts subjects.', 0.80),
    
    ('CULTURAL AND CREATIVE ARTS', 'THEATRE ARTS',
     'Literature in English and any two (2) Arts subjects.', 0.80),
    
    -- Special Education Combinations
    ('SPECIAL NEEDS EDUCATION', 'SOCIAL STUDIES',
     'Any three (3) Arts or Social Science subjects.', 0.80),
    
    -- Geography Combinations
    ('GEOGRAPHY', 'ECONOMICS',
     'Geography, Economics and one (1) Social Science subject.', 0.85),
    
    ('GEOGRAPHY', 'SOCIAL STUDIES',
     'Geography and any two (2) Social Science subjects.', 0.85),
    
    -- History Combinations
    ('HISTORY', 'POLITICAL SCIENCE',
     'Government/History and any two (2) Social Science subjects.', 0.85),
    
    -- Theatre Arts Combinations
    ('THEATRE ARTS', 'ENGLISH',
     'Literature in English and any two (2) Arts subjects.', 0.85),
    
    -- Yoruba Combinations
    ('YORUBA', 'ENGLISH',
     'Yoruba, Literature in English and one (1) Arts subject.', 0.85),
    
    ('YORUBA', 'SOCIAL STUDIES',
     'Yoruba and any two (2) Arts or Social Science subjects.', 0.80),
    
    -- French Combinations
    ('FRENCH', 'ENGLISH',
     'French, Literature in English and one (1) Arts subject.', 0.85),
    
    ('FRENCH', 'SOCIAL STUDIES',
     'French and any two (2) Arts or Social Science subjects.', 0.80);

-- Create a function to generate a report of pattern coverage
CREATE OR REPLACE FUNCTION analyze_pattern_coverage() 
RETURNS TABLE (
    total_combinations BIGINT,
    matched_patterns BIGINT,
    coverage_percentage NUMERIC,
    avg_confidence NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH Stats AS (
        SELECT 
            COUNT(DISTINCT course_name) as total,
            COUNT(DISTINCT CASE WHEN confidence >= 0.8 THEN course_name END) as matched,
            AVG(confidence) as avg_conf
        FROM combination_course_analysis
        WHERE current_subjects = '[Not Available]'
    )
    SELECT 
        total as total_combinations,
        matched as matched_patterns,
        ROUND((matched::NUMERIC / total::NUMERIC) * 100, 2) as coverage_percentage,
        ROUND(avg_conf::NUMERIC, 2) as avg_confidence
    FROM Stats;
END;
$$ LANGUAGE plpgsql;

-- Create a view for monitoring pattern effectiveness
CREATE OR REPLACE VIEW pattern_effectiveness_analysis AS
WITH PatternStats AS (
    SELECT 
        cp.primary_course_pattern,
        cp.secondary_course_pattern,
        cp.confidence_score as pattern_confidence,
        COUNT(DISTINCT c.course_name) as matches,
        AVG(ca.confidence) as actual_confidence
    FROM combination_course_patterns cp
    LEFT JOIN course c ON 
        (SPLIT_PART(c.course_name, '/', 1) LIKE cp.primary_course_pattern 
         AND SPLIT_PART(c.course_name, '/', 2) LIKE cp.secondary_course_pattern)
    LEFT JOIN combination_course_analysis ca ON c.course_name = ca.course_name
    GROUP BY cp.primary_course_pattern, cp.secondary_course_pattern, cp.confidence_score
)
SELECT 
    primary_course_pattern,
    secondary_course_pattern,
    pattern_confidence,
    matches,
    ROUND(actual_confidence::NUMERIC, 2) as actual_confidence,
    CASE 
        WHEN matches = 0 THEN 'Unused Pattern'
        WHEN actual_confidence >= pattern_confidence THEN 'Effective'
        ELSE 'Needs Review'
    END as pattern_status
FROM PatternStats
ORDER BY matches DESC, pattern_confidence DESC;
