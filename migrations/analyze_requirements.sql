-- Analyze subject requirements by faculty
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

-- Analyze pattern coverage
SELECT 
    cp.primary_course_pattern,
    cp.secondary_course_pattern,
    cp.confidence_score,
    COUNT(DISTINCT c.course_name) as matched_courses
FROM combination_course_patterns cp
LEFT JOIN course c ON 
    (SPLIT_PART(c.course_name, '/', 1) LIKE cp.primary_course_pattern 
     AND SPLIT_PART(c.course_name, '/', 2) LIKE cp.secondary_course_pattern)
GROUP BY cp.primary_course_pattern, cp.secondary_course_pattern, cp.confidence_score
HAVING COUNT(DISTINCT c.course_name) > 0
ORDER BY cp.confidence_score DESC, matched_courses DESC;

-- Validate existing patterns
SELECT 
    c.course_name,
    sr.subjects,
    v.is_valid,
    v.validation_message
FROM course c
JOIN course_requirement cr ON c.id = cr.course_id
JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
CROSS JOIN LATERAL validate_combination_requirement(
    sr.subjects,
    SPLIT_PART(c.course_name, '/', 1),
    SPLIT_PART(c.course_name, '/', 2)
) v
WHERE c.course_name LIKE '%/%'
AND sr.subjects != '[Not Available]'
ORDER BY v.is_valid, c.course_name
LIMIT 10;
