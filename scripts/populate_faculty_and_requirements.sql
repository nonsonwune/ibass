-- Create and populate faculty table
CREATE TABLE IF NOT EXISTS faculty (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate main faculties based on program requirements from JSON
INSERT INTO faculty (name, code, description) VALUES
    ('Faculty of Sciences', 'SCI', 'Natural and Physical Sciences including Mathematics, Physics, Chemistry, Biology and Computer Science'),
    ('Faculty of Engineering', 'ENG', 'Engineering disciplines requiring Mathematics, Physics and Chemistry'),
    ('Faculty of Arts', 'ARTS', 'Arts and Humanities programs with focus on Languages and Literature'),
    ('Faculty of Social Sciences', 'SOC', 'Social Science programs including Economics and Mass Communication'),
    ('Faculty of Law', 'LAW', 'Legal Studies with emphasis on English and Literature'),
    ('Faculty of Medicine', 'MED', 'Medical Sciences requiring strong foundation in Sciences'),
    ('Faculty of Agriculture', 'AGRIC', 'Agricultural Sciences and related programs'),
    ('Faculty of Environmental Sciences', 'ENV', 'Environmental Studies and Management'),
    ('Faculty of Management Sciences', 'MGT', 'Business and Management programs'),
    ('Faculty of Education', 'EDU', 'Education programs with various teaching subject combinations')
ON CONFLICT (name) DO NOTHING;

-- Create subject requirements table if not exists
CREATE TABLE IF NOT EXISTS faculty_subject_requirements (
    id SERIAL PRIMARY KEY,
    faculty_id INTEGER REFERENCES faculty(id),
    mandatory_subjects TEXT[],
    optional_subjects TEXT[],
    minimum_credits INTEGER DEFAULT 5,
    special_requirements JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate faculty subject requirements
INSERT INTO faculty_subject_requirements (faculty_id, mandatory_subjects, optional_subjects, minimum_credits, special_requirements)
SELECT 
    f.id,
    CASE 
        WHEN f.name = 'Faculty of Sciences' THEN 
            ARRAY['English Language', 'Mathematics', 'Chemistry', 'Physics', 'Biology']
        WHEN f.name = 'Faculty of Engineering' THEN 
            ARRAY['English Language', 'Mathematics', 'Physics', 'Chemistry']
        WHEN f.name = 'Faculty of Arts' THEN 
            ARRAY['English Language', 'Literature in English']
        WHEN f.name = 'Faculty of Social Sciences' THEN 
            ARRAY['English Language', 'Mathematics']
        WHEN f.name = 'Faculty of Law' THEN 
            ARRAY['English Language', 'Literature in English']
        WHEN f.name = 'Faculty of Medicine' THEN 
            ARRAY['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology']
        WHEN f.name = 'Faculty of Agriculture' THEN 
            ARRAY['English Language', 'Mathematics', 'Chemistry', 'Biology']
        WHEN f.name = 'Faculty of Environmental Sciences' THEN 
            ARRAY['English Language', 'Mathematics']
        WHEN f.name = 'Faculty of Management Sciences' THEN 
            ARRAY['English Language', 'Mathematics']
        WHEN f.name = 'Faculty of Education' THEN 
            ARRAY['English Language']
    END,
    CASE 
        WHEN f.name = 'Faculty of Sciences' THEN 
            ARRAY['Agricultural Science']
        WHEN f.name = 'Faculty of Arts' THEN 
            ARRAY['History', 'Government', 'CRS/IRS', 'Any Nigerian Language']
        WHEN f.name = 'Faculty of Social Sciences' THEN 
            ARRAY['Economics', 'Government', 'Geography', 'Commerce']
        WHEN f.name = 'Faculty of Environmental Sciences' THEN 
            ARRAY['Physics', 'Chemistry', 'Geography', 'Technical Drawing', 'Fine Arts']
        WHEN f.name = 'Faculty of Management Sciences' THEN 
            ARRAY['Economics', 'Commerce', 'Accounting', 'Government']
        ELSE 
            ARRAY[]::TEXT[]
    END,
    5,
    CASE 
        WHEN f.name = 'Faculty of Medicine' THEN 
            '{"sitting_requirement": "One sitting only", "minimum_grade": "Credit pass in all subjects"}'::JSONB
        WHEN f.name = 'Faculty of Law' THEN 
            '{"mathematics_requirement": "Pass acceptable"}'::JSONB
        WHEN f.name = 'Faculty of Arts' THEN 
            '{"mathematics_requirement": "Pass acceptable"}'::JSONB
        ELSE 
            '{}'::JSONB
    END
FROM faculty f
ON CONFLICT DO NOTHING;

-- Create table for special program requirements
CREATE TABLE IF NOT EXISTS program_specific_requirements (
    id SERIAL PRIMARY KEY,
    faculty_id INTEGER REFERENCES faculty(id),
    program_name VARCHAR(255),
    additional_requirements JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate special program requirements
INSERT INTO program_specific_requirements (faculty_id, program_name, additional_requirements)
SELECT 
    f.id,
    p.program_name,
    p.requirements::JSONB
FROM faculty f
CROSS JOIN (
    VALUES 
        ('Faculty of Arts', 'English and Literary Studies', 
         '{"mandatory_subjects": ["Literature in English"]}'),
        ('Faculty of Social Sciences', 'Economics', 
         '{"mandatory_subjects": ["Economics"]}'),
        ('Faculty of Social Sciences', 'Mass Communication', 
         '{"mandatory_subjects": ["Literature in English"], "minimum_grade": "Pass acceptable"}'),
        ('Faculty of Sciences', 'Computer Science', 
         '{"acceptable_substitution": "Agricultural Science can replace Biology"}'),
        ('Faculty of Environmental Sciences', 'Environmental Management', 
         '{"physics_requirement": {"condition": "Pass acceptable if credit in Geography or Agricultural Science"}}')
) AS p(faculty_name, program_name, requirements)
WHERE f.name = p.faculty_name
ON CONFLICT DO NOTHING;
