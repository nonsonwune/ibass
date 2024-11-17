-- Check for [Not Available] in various requirement fields
BEGIN;

-- Check UTME requirements
SELECT 'UTME Template' as source, id, requirements
FROM utme_requirement_template
WHERE requirements LIKE '%[Not Available]%';

-- Check Direct Entry requirements
SELECT 'DE Template' as source, id, requirements
FROM direct_entry_requirement_template
WHERE requirements LIKE '%[Not Available]%';

-- Check course requirements with [Not Available]
WITH course_info AS (
    SELECT cr.id as requirement_id,
           c.course_name,
           ut.requirements as utme_requirements,
           dt.requirements as de_requirements
    FROM course_requirement cr
    JOIN course c ON cr.course_id = c.id
    LEFT JOIN utme_requirement_template ut ON cr.utme_template_id = ut.id
    LEFT JOIN direct_entry_requirement_template dt ON cr.de_template_id = dt.id
    WHERE ut.requirements LIKE '%[Not Available]%'
       OR dt.requirements LIKE '%[Not Available]%'
)
SELECT 'Course Requirements' as source,
       requirement_id,
       course_name,
       utme_requirements,
       de_requirements
FROM course_info
ORDER BY course_name;

-- Count total occurrences
SELECT 
    COUNT(*) FILTER (WHERE requirements LIKE '%[Not Available]%') as utme_count
FROM utme_requirement_template
UNION ALL
SELECT 
    COUNT(*) FILTER (WHERE requirements LIKE '%[Not Available]%')
FROM direct_entry_requirement_template;

ROLLBACK;
