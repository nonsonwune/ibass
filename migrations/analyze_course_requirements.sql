-- Create a temporary table to store requirement patterns
CREATE TEMP TABLE requirement_patterns AS
WITH course_patterns AS (
    SELECT 
        c.course_name,
        c.normalized_name,
        u.university_name,
        ut.requirements as utme_requirements,
        det.requirements as de_requirements,
        sr.subjects,
        COUNT(*) OVER (PARTITION BY c.normalized_name) as course_count
    FROM course c
    JOIN course_requirement cr ON c.id = cr.course_id
    JOIN university u ON cr.university_id = u.id
    LEFT JOIN utme_requirement_template ut ON cr.utme_template_id = ut.id
    LEFT JOIN direct_entry_requirement_template det ON cr.de_template_id = det.id
    LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
    WHERE ut.requirements != '[Not Available]' 
    AND (det.requirements != '[Not Available]' OR det.requirements IS NULL)
)
SELECT 
    normalized_name,
    course_name,
    COUNT(*) as total_instances,
    MODE() WITHIN GROUP (ORDER BY utme_requirements) as common_utme_req,
    MODE() WITHIN GROUP (ORDER BY de_requirements) as common_de_req,
    MODE() WITHIN GROUP (ORDER BY subjects) as common_subjects,
    array_agg(DISTINCT university_name) as universities
FROM course_patterns
GROUP BY normalized_name, course_name
HAVING COUNT(*) > 1
ORDER BY total_instances DESC;

-- View the most common requirement patterns
SELECT 
    normalized_name,
    course_name,
    total_instances,
    common_utme_req,
    common_de_req,
    common_subjects,
    array_length(universities, 1) as num_universities
FROM requirement_patterns
ORDER BY total_instances DESC
LIMIT 20;

-- Analyze courses with [Not Available] requirements
WITH na_courses AS (
    SELECT 
        c.course_name,
        c.normalized_name,
        u.university_name,
        COUNT(*) OVER (PARTITION BY c.normalized_name) as na_count
    FROM course c
    JOIN course_requirement cr ON c.id = cr.course_id
    JOIN university u ON cr.university_id = u.id
    WHERE cr.utme_template_id = 1856 OR cr.de_template_id = 1133
)
SELECT 
    normalized_name,
    course_name,
    COUNT(*) as total_na_instances,
    array_agg(DISTINCT university_name) as universities
FROM na_courses
GROUP BY normalized_name, course_name
ORDER BY total_na_instances DESC;

-- Create a mapping table for requirement replacements
CREATE TABLE requirement_replacement_map (
    id SERIAL PRIMARY KEY,
    course_pattern text,
    original_utme_id integer,
    original_de_id integer,
    replacement_utme_id integer,
    replacement_de_id integer,
    replacement_subjects text,
    confidence_score float,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    reviewed boolean DEFAULT false,
    applied boolean DEFAULT false
);

-- Insert high-confidence replacements
INSERT INTO requirement_replacement_map 
(course_pattern, original_utme_id, original_de_id, replacement_utme_id, replacement_de_id, replacement_subjects, confidence_score)
SELECT 
    rp.normalized_name as course_pattern,
    1856 as original_utme_id,
    1133 as original_de_id,
    ut.id as replacement_utme_id,
    det.id as replacement_de_id,
    rp.common_subjects as replacement_subjects,
    CASE 
        WHEN rp.total_instances >= 10 THEN 1.0
        WHEN rp.total_instances >= 5 THEN 0.8
        ELSE 0.6
    END as confidence_score
FROM requirement_patterns rp
JOIN utme_requirement_template ut ON ut.requirements = rp.common_utme_req
LEFT JOIN direct_entry_requirement_template det ON det.requirements = rp.common_de_req
WHERE rp.total_instances >= 3;

-- View proposed replacements
SELECT 
    rm.course_pattern,
    c.course_name,
    ut_old.requirements as old_utme_req,
    ut_new.requirements as new_utme_req,
    det_old.requirements as old_de_req,
    det_new.requirements as new_de_req,
    rm.confidence_score
FROM requirement_replacement_map rm
JOIN course c ON c.normalized_name = rm.course_pattern
JOIN utme_requirement_template ut_old ON ut_old.id = rm.original_utme_id
JOIN utme_requirement_template ut_new ON ut_new.id = rm.replacement_utme_id
LEFT JOIN direct_entry_requirement_template det_old ON det_old.id = rm.original_de_id
LEFT JOIN direct_entry_requirement_template det_new ON det_new.id = rm.replacement_de_id
WHERE rm.confidence_score >= 0.8
ORDER BY rm.confidence_score DESC, c.course_name;
