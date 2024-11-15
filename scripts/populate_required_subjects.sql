-- Populate required_subjects table
-- First, ensure we have the correct subject IDs from the subjects table

-- General Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    NULL as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE s.name IN ('English Language')
ON CONFLICT DO NOTHING;

-- Science Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    (SELECT id FROM subject_categories WHERE name = 'Pure Sciences') as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Science%'))
AND s.name IN ('Mathematics', 'Physics', 'Chemistry', 'Biology')
ON CONFLICT DO NOTHING;

-- Engineering Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    (SELECT id FROM subject_categories WHERE name = 'Pure Sciences') as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Engineering%'))
AND s.name IN ('Mathematics', 'Physics', 'Chemistry')
ON CONFLICT DO NOTHING;

-- Arts Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    (SELECT id FROM subject_categories WHERE name = 'Languages') as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Arts%'))
AND s.name IN ('English Language', 'Literature in English')
ON CONFLICT DO NOTHING;

-- Social Science Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    (SELECT id FROM subject_categories WHERE name = 'Core Social Sciences') as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Social Science%'))
AND s.name IN ('English Language', 'Mathematics', 'Economics')
ON CONFLICT DO NOTHING;

-- Law Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    NULL as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Law%'))
AND s.name IN ('English Language', 'Literature in English')
ON CONFLICT DO NOTHING;

-- Medicine Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    (SELECT id FROM subject_categories WHERE name = 'Pure Sciences') as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Medicine%'))
AND s.name IN ('English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology')
ON CONFLICT DO NOTHING;

-- Religious Studies Program Requirements
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    true as is_mandatory,
    (SELECT id FROM subject_categories WHERE name = 'Humanities') as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE name LIKE '%Religious Studies%')
AND s.name IN ('English Language', 'Christian Religious Studies', 'Islamic Studies')
ON CONFLICT DO NOTHING;

-- Add Mathematics as non-mandatory for Arts programs
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT 
    r.id as requirement_id,
    s.id as subject_id,
    false as is_mandatory,
    NULL as subject_group_id
FROM course_requirement r
CROSS JOIN subjects s
WHERE r.course_id IN (SELECT id FROM course WHERE faculty_id IN (SELECT id FROM faculty WHERE name LIKE '%Arts%'))
AND s.name = 'Mathematics'
ON CONFLICT DO NOTHING;

-- Add subject groups for optional subjects
INSERT INTO required_subjects (requirement_id, subject_id, is_mandatory, subject_group_id)
SELECT DISTINCT
    r.id as requirement_id,
    NULL as subject_id,
    false as is_mandatory,
    sc.id as subject_group_id
FROM course_requirement r
CROSS JOIN subject_categories sc
WHERE sc.name IN ('Pure Sciences', 'Applied Sciences', 'Languages', 'Core Social Sciences', 'Business Studies', 'Humanities')
ON CONFLICT DO NOTHING;
