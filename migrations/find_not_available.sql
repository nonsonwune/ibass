-- Find all instances of [Not Available] in requirements
WITH requirement_info AS (
    SELECT 
        cr.id as requirement_id,
        u.university_name,
        c.course_name,
        ut.requirements as utme_requirements,
        dt.requirements as de_requirements,
        sr.subjects as subject_requirements,
        CASE 
            WHEN ut.requirements LIKE '%[Not Available]%' THEN true
            ELSE false
        END as has_na_utme,
        CASE 
            WHEN dt.requirements LIKE '%[Not Available]%' THEN true
            ELSE false
        END as has_na_de,
        CASE 
            WHEN sr.subjects LIKE '%[Not Available]%' THEN true
            ELSE false
        END as has_na_subjects
    FROM course_requirement cr
    JOIN university u ON cr.university_id = u.id
    JOIN course c ON cr.course_id = c.id
    LEFT JOIN utme_requirement_template ut ON cr.utme_template_id = ut.id
    LEFT JOIN direct_entry_requirement_template dt ON cr.de_template_id = dt.id
    LEFT JOIN subject_requirement sr ON sr.course_requirement_id = cr.id
    WHERE ut.requirements LIKE '%[Not Available]%'
       OR dt.requirements LIKE '%[Not Available]%'
       OR sr.subjects LIKE '%[Not Available]%'
)
SELECT 
    requirement_id,
    university_name,
    course_name,
    CASE 
        WHEN has_na_utme THEN utme_requirements 
        ELSE NULL 
    END as utme_na,
    CASE 
        WHEN has_na_de THEN de_requirements 
        ELSE NULL 
    END as de_na,
    CASE 
        WHEN has_na_subjects THEN subject_requirements 
        ELSE NULL 
    END as subject_na
FROM requirement_info
ORDER BY university_name, course_name;

-- Get summary counts
SELECT 
    'UTME Requirements' as type,
    COUNT(*) as count
FROM utme_requirement_template
WHERE requirements LIKE '%[Not Available]%'
UNION ALL
SELECT 
    'DE Requirements',
    COUNT(*)
FROM direct_entry_requirement_template
WHERE requirements LIKE '%[Not Available]%'
UNION ALL
SELECT 
    'Subject Requirements',
    COUNT(*)
FROM subject_requirement
WHERE subjects LIKE '%[Not Available]%'
ORDER BY type;
