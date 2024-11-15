-- Drop existing tables if they exist
DROP TABLE IF EXISTS nabteb_program_acceptance;
DROP TABLE IF EXISTS nabteb_faculty_acceptance;
DROP TABLE IF EXISTS nabteb_acceptance;

-- Create NABTEB acceptance table
CREATE TABLE nabteb_acceptance (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES university(id) ON DELETE CASCADE,
    accepts_as_olevel BOOLEAN DEFAULT FALSE,
    accepts_advanced_cert BOOLEAN DEFAULT FALSE,
    verification_source VARCHAR(255) NOT NULL,
    special_conditions TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(university_id)
);

-- Create faculty acceptance table
CREATE TABLE nabteb_faculty_acceptance (
    id SERIAL PRIMARY KEY,
    nabteb_acceptance_id INTEGER REFERENCES nabteb_acceptance(id) ON DELETE CASCADE,
    faculty_name VARCHAR(255) NOT NULL,
    acceptance_type VARCHAR(20) CHECK (acceptance_type IN ('full', 'partial', 'conditional')),
    conditions TEXT,
    UNIQUE(nabteb_acceptance_id, faculty_name)
);

-- Create program acceptance table
CREATE TABLE nabteb_program_acceptance (
    id SERIAL PRIMARY KEY,
    nabteb_acceptance_id INTEGER REFERENCES nabteb_acceptance(id) ON DELETE CASCADE,
    program_name VARCHAR(255) NOT NULL,
    acceptance_type VARCHAR(20) CHECK (acceptance_type IN ('full', 'partial', 'conditional')),
    conditions TEXT,
    UNIQUE(nabteb_acceptance_id, program_name)
);

-- Insert data for Kaduna State University
INSERT INTO nabteb_acceptance (
    university_id,
    accepts_as_olevel,
    accepts_advanced_cert,
    verification_source,
    special_conditions
)
SELECT 
    id,
    FALSE,
    FALSE,
    'institutional_data_2023',
    'Explicitly only accepts WAEC and NECO certificates'
FROM university 
WHERE university_name ILIKE '%Kaduna State%';

-- Insert data for University of Benin and its faculty/program acceptances
DO $$
DECLARE
    uniben_id INTEGER;
BEGIN
    -- Insert UNIBEN acceptance and get its ID
    INSERT INTO nabteb_acceptance (
        university_id,
        accepts_as_olevel,
        accepts_advanced_cert,
        verification_source,
        special_conditions
    )
    SELECT 
        id,
        TRUE,
        TRUE,
        'institutional_data_2023',
        'Accepted as O''level equivalent for basic requirements. NABTEB Advanced Certificate recognized as specialized diploma equivalent.'
    FROM university 
    WHERE university_name ILIKE '%Benin%'
    LIMIT 1
    RETURNING id INTO uniben_id;

    -- Insert faculty acceptances
    INSERT INTO nabteb_faculty_acceptance (nabteb_acceptance_id, faculty_name, acceptance_type, conditions)
    VALUES 
        (uniben_id, 'Social Sciences', 'full', NULL),
        (uniben_id, 'Education', 'full', NULL),
        (uniben_id, 'Engineering', 'full', NULL),
        (uniben_id, 'Management Sciences', 'full', NULL),
        (uniben_id, 'Arts', 'partial', 'Only selected programs');

    -- Insert program acceptances
    INSERT INTO nabteb_program_acceptance (nabteb_acceptance_id, program_name, acceptance_type, conditions)
    VALUES 
        (uniben_id, 'Geography and Regional Planning', 'full', NULL),
        (uniben_id, 'Political Science', 'full', NULL),
        (uniben_id, 'Sociology', 'full', NULL),
        (uniben_id, 'Public Administration', 'full', NULL),
        (uniben_id, 'Economics', 'full', NULL),
        (uniben_id, 'Accounting', 'full', NULL),
        (uniben_id, 'Business Administration', 'full', NULL),
        (uniben_id, 'Banking and Finance', 'full', NULL),
        (uniben_id, 'Fine Arts', 'full', NULL),
        (uniben_id, 'Mass Communication', 'full', NULL);
END $$;
