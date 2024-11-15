-- Populate professional course requirements for Medicine and Surgery
WITH medicine_course AS (
    SELECT id FROM course WHERE course_name ILIKE '%Medicine and Surgery%' LIMIT 1
)
INSERT INTO professional_course_requirements (
    course_id,
    o_level_requirements,
    utme_requirements,
    direct_entry_requirements,
    special_conditions
)
SELECT 
    medicine_course.id,
    jsonb_build_object(
        'mandatory_subjects', ARRAY['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology'],
        'special_conditions', jsonb_build_object(
            'sitting_requirement', 'One sitting only',
            'minimum_grade', 'Credit pass in all subjects'
        )
    ),
    jsonb_build_object(
        'subjects', ARRAY['English Language', 'Physics', 'Chemistry', 'Biology']
    ),
    jsonb_build_object(
        'first_degree_pathway', jsonb_build_object(
            'minimum_class', ARRAY['First Class', 'Second Class Upper'],
            'additional_requirements', ARRAY[
                'Must have completed NYSC',
                'Must have UTME subject requirements',
                'Degree must be in relevant field'
            ],
            'accepting_institutions', ARRAY[
                'Obafemi Awolowo University',
                'University of Benin',
                'University of Calabar',
                'University of Ibadan',
                'University of Lagos',
                'University of Nigeria',
                'Ambrose Alli University',
                'University of Ilorin'
            ]
        ),
        'other_qualifications', jsonb_build_object(
            'a_level', jsonb_build_object(
                'required_subjects', ARRAY['Physics', 'Chemistry', 'Biology'],
                'minimum_grade', 'C'
            )
        )
    ),
    'Requires one sitting for O''level results. Advanced standing entry requires completion of NYSC.'
FROM medicine_course
ON CONFLICT (course_id) DO UPDATE SET
    o_level_requirements = EXCLUDED.o_level_requirements,
    utme_requirements = EXCLUDED.utme_requirements,
    direct_entry_requirements = EXCLUDED.direct_entry_requirements,
    special_conditions = EXCLUDED.special_conditions;

-- Populate professional course requirements for Law
WITH law_course AS (
    SELECT id FROM course WHERE course_name ILIKE '%Law%' LIMIT 1
)
INSERT INTO professional_course_requirements (
    course_id,
    o_level_requirements,
    utme_requirements,
    direct_entry_requirements,
    special_conditions
)
SELECT 
    law_course.id,
    jsonb_build_object(
        'mandatory_subjects', ARRAY['English Language', 'Literature in English'],
        'mathematics_requirement', 'Pass acceptable',
        'additional_requirements', 'Three other relevant subjects'
    ),
    jsonb_build_object(
        'subjects', ARRAY[
            'English Language',
            'Literature in English',
            'Government or History',
            'CRK/IRK or Social Studies'
        ]
    ),
    jsonb_build_object(
        'first_degree_pathway', jsonb_build_object(
            'minimum_class', ARRAY['First Class', 'Second Class Upper'],
            'additional_requirements', ARRAY[
                'Must have completed NYSC',
                'Literature in English not required for graduate candidates at some institutions'
            ]
        )
    ),
    'Literature in English requirement may be waived for graduate entry at some institutions.'
FROM law_course
ON CONFLICT (course_id) DO UPDATE SET
    o_level_requirements = EXCLUDED.o_level_requirements,
    utme_requirements = EXCLUDED.utme_requirements,
    direct_entry_requirements = EXCLUDED.direct_entry_requirements,
    special_conditions = EXCLUDED.special_conditions;

-- Populate professional course requirements for Engineering
WITH engineering_course AS (
    SELECT id FROM course WHERE course_name ILIKE '%Engineering%' LIMIT 1
)
INSERT INTO professional_course_requirements (
    course_id,
    o_level_requirements,
    utme_requirements,
    direct_entry_requirements,
    special_conditions
)
SELECT 
    engineering_course.id,
    jsonb_build_object(
        'mandatory_subjects', ARRAY['English Language', 'Mathematics', 'Physics', 'Chemistry'],
        'additional_requirements', 'One other Science subject',
        'special_notes', jsonb_build_object(
            'physics_requirement', jsonb_build_object(
                'standard', 'Credit',
                'exceptions', jsonb_build_object(
                    'pass_acceptable', ARRAY[
                        'Estate Management',
                        'Industrial Design',
                        'Urban and Regional Planning'
                    ]
                )
            )
        )
    ),
    jsonb_build_object(
        'subjects', ARRAY['English Language', 'Mathematics', 'Physics', 'Chemistry']
    ),
    jsonb_build_object(
        'a_level', jsonb_build_object(
            'required_subjects', ARRAY['Mathematics', 'Physics', 'Chemistry']
        ),
        'national_diploma', jsonb_build_object(
            'minimum_grade', 'Upper Credit',
            'relevant_programs_only', true
        )
    ),
    'Physics credit requirement may be relaxed for certain programs. ND must be in relevant engineering field.'
FROM engineering_course
ON CONFLICT (course_id) DO UPDATE SET
    o_level_requirements = EXCLUDED.o_level_requirements,
    utme_requirements = EXCLUDED.utme_requirements,
    direct_entry_requirements = EXCLUDED.direct_entry_requirements,
    special_conditions = EXCLUDED.special_conditions;

-- Create professional course specializations for Engineering
WITH engineering_course AS (
    SELECT id FROM course WHERE course_name ILIKE '%Engineering%' LIMIT 1
)
INSERT INTO professional_course_specializations (
    course_id,
    specialization_name,
    requirements,
    normalized_name
)
VALUES 
    ((SELECT id FROM engineering_course), 'Civil Engineering', 
     jsonb_build_object(
         'additional_subjects', ARRAY['Technical Drawing'],
         'recommended_subjects', ARRAY['Further Mathematics']
     ),
     'civil_engineering'),
    ((SELECT id FROM engineering_course), 'Electrical Engineering',
     jsonb_build_object(
         'additional_subjects', ARRAY['Electronics', 'Applied Electricity'],
         'recommended_subjects', ARRAY['Further Mathematics']
     ),
     'electrical_engineering'),
    ((SELECT id FROM engineering_course), 'Mechanical Engineering',
     jsonb_build_object(
         'additional_subjects', ARRAY['Technical Drawing', 'Metal Work'],
         'recommended_subjects', ARRAY['Further Mathematics']
     ),
     'mechanical_engineering')
ON CONFLICT (course_id, specialization_name) DO UPDATE SET
    requirements = EXCLUDED.requirements,
    normalized_name = EXCLUDED.normalized_name;

-- Create professional program requirements for specific programs
WITH 
medicine_course AS (
    SELECT id FROM course WHERE course_name ILIKE '%Medicine and Surgery%' LIMIT 1
),
law_course AS (
    SELECT id FROM course WHERE course_name ILIKE '%Law%' LIMIT 1
)
INSERT INTO professional_program_requirements (
    course_id,
    o_level_requirements,
    utme_subjects,
    direct_entry_requirements,
    special_conditions
)
VALUES
    ((SELECT id FROM medicine_course),
     jsonb_build_object(
         'mandatory_subjects', ARRAY['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology'],
         'minimum_grade', 'Credit',
         'sitting_requirement', 'One sitting only'
     ),
     ARRAY['English Language', 'Physics', 'Chemistry', 'Biology'],
     jsonb_build_object(
         'minimum_class', 'Second Class Upper',
         'additional_requirements', ARRAY['NYSC completion required', 'Relevant science degree']
     ),
     'Must have distinction in core science subjects for direct entry'),
    
    ((SELECT id FROM law_course),
     jsonb_build_object(
         'mandatory_subjects', ARRAY['English Language', 'Literature in English'],
         'minimum_grade', 'Credit',
         'mathematics_requirement', 'Pass'
     ),
     ARRAY['English Language', 'Literature in English', 'Government', 'CRK/IRK'],
     jsonb_build_object(
         'minimum_class', 'Second Class Upper',
         'additional_requirements', ARRAY['NYSC completion required']
     ),
     'Literature requirement may be waived for direct entry candidates')
ON CONFLICT (course_id) DO UPDATE SET
    o_level_requirements = EXCLUDED.o_level_requirements,
    utme_subjects = EXCLUDED.utme_subjects,
    direct_entry_requirements = EXCLUDED.direct_entry_requirements,
    special_conditions = EXCLUDED.special_conditions;
