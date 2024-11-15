-- Create faculty table if it doesn't exist
CREATE TABLE IF NOT EXISTS faculty (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Populate faculty table
INSERT INTO faculty (name, code, description) VALUES
    ('Faculty of Sciences', 'SCI', 'Natural and Physical Sciences'),
    ('Faculty of Engineering', 'ENG', 'Engineering and Technology'),
    ('Faculty of Arts', 'ARTS', 'Arts and Humanities'),
    ('Faculty of Social Sciences', 'SOC', 'Social and Behavioral Sciences'),
    ('Faculty of Law', 'LAW', 'Legal Studies'),
    ('Faculty of Medicine', 'MED', 'Medical and Health Sciences'),
    ('Faculty of Education', 'EDU', 'Education and Teaching'),
    ('Faculty of Agriculture', 'AGRIC', 'Agricultural Sciences'),
    ('Faculty of Environmental Sciences', 'ENV', 'Environmental Studies'),
    ('Faculty of Management Sciences', 'MGT', 'Business and Management'),
    ('Faculty of Pharmacy', 'PHARM', 'Pharmaceutical Sciences'),
    ('Faculty of Veterinary Medicine', 'VET', 'Veterinary Sciences'),
    ('Faculty of Basic Medical Sciences', 'BMS', 'Basic Medical Sciences'),
    ('Faculty of Clinical Sciences', 'CLIN', 'Clinical Medical Sciences'),
    ('Faculty of Dental Sciences', 'DENT', 'Dental Sciences')
ON CONFLICT (name) DO NOTHING;
