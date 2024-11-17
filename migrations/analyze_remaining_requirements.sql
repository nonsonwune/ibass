-- Analysis of remaining [Not Available] requirements
WITH RemainingRequirements AS (
    SELECT 
        c.course_name,
        u.university_name,
        CASE 
            WHEN cr.utme_template_id IS NOT NULL THEN 'UTME'
            WHEN cr.de_template_id IS NOT NULL THEN 'DE'
        END as requirement_type,
        s.subjects,
        epr.specific_requirements,
        epr.additional_conditions
    FROM course_requirement cr
    JOIN course c ON cr.course_id = c.id
    JOIN university u ON cr.university_id = u.id
    LEFT JOIN subject_requirement s ON s.course_requirement_id = cr.id
    LEFT JOIN extended_program_requirements epr ON epr.course_requirement_id = cr.id
    WHERE 
        (cr.utme_template_id IN (SELECT id FROM utme_requirement_template WHERE requirements LIKE '%[Not Available]%')
        OR cr.de_template_id IN (SELECT id FROM direct_entry_requirement_template WHERE requirements LIKE '%[Not Available]%'))
)
SELECT 
    requirement_type,
    course_name,
    COUNT(*) as occurrence_count,
    array_agg(DISTINCT university_name) as universities,
    array_agg(DISTINCT subjects) FILTER (WHERE subjects IS NOT NULL) as subject_patterns,
    array_agg(DISTINCT specific_requirements) FILTER (WHERE specific_requirements IS NOT NULL) as specific_requirement_patterns
FROM RemainingRequirements
GROUP BY requirement_type, course_name
ORDER BY requirement_type, occurrence_count DESC;

-- Subject requirement patterns analysis
WITH SubjectPatterns AS (
    SELECT 
        sr.subjects,
        COUNT(*) as usage_count,
        array_agg(DISTINCT c.course_name) as courses
    FROM subject_requirement sr
    JOIN course_requirement cr ON sr.course_requirement_id = cr.id
    JOIN course c ON cr.course_id = c.id
    WHERE sr.subjects NOT LIKE '%[Not Available]%'
    GROUP BY sr.subjects
    HAVING COUNT(*) > 5
)
SELECT 
    subjects as common_subject_combination,
    usage_count,
    courses
FROM SubjectPatterns
ORDER BY usage_count DESC
LIMIT 20;

-- Course category analysis for remaining [Not Available] entries
WITH CourseCategories AS (
    SELECT 
        CASE 
            WHEN course_name LIKE '%ENGINEERING%' THEN 'Engineering'
            WHEN course_name LIKE '%SCIENCE%' OR course_name LIKE '%BIOLOGY%' OR course_name LIKE '%CHEMISTRY%' OR course_name LIKE '%PHYSICS%' THEN 'Science'
            WHEN course_name LIKE '%EDUCATION%' OR course_name LIKE '%TEACHING%' THEN 'Education'
            WHEN course_name LIKE '%ARTS%' OR course_name LIKE '%LANGUAGE%' OR course_name LIKE '%LITERATURE%' THEN 'Arts'
            WHEN course_name LIKE '%BUSINESS%' OR course_name LIKE '%ECONOMICS%' OR course_name LIKE '%ACCOUNTING%' THEN 'Business'
            ELSE 'Others'
        END as course_category,
        cr.id
    FROM course_requirement cr
    JOIN course c ON cr.course_id = c.id
    WHERE 
        cr.utme_template_id IN (SELECT id FROM utme_requirement_template WHERE requirements LIKE '%[Not Available]%')
        OR cr.de_template_id IN (SELECT id FROM direct_entry_requirement_template WHERE requirements LIKE '%[Not Available]%')
)
SELECT 
    course_category,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM CourseCategories
GROUP BY course_category
ORDER BY count DESC;
