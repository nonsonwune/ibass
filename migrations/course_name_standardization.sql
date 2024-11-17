-- Course Name Standardization Migration
BEGIN;

-- Create a temporary table to store the name mappings
CREATE TEMP TABLE course_name_mapping (
    old_name TEXT,
    new_name TEXT
);

-- Insert the standardized name mappings
INSERT INTO course_name_mapping (old_name, new_name) VALUES
    -- Group 1: Early Childhood Programs
    ('EARLY CHILDHOOD & CARE EDUCATION (DOUBLE MAJOR)', 'EARLY CHILDHOOD CARE & EDUCATION (DOUBLE MAJOR)'),
    ('EARLY CHILDHOOD AND CARE EDUCATION (DOUBLE MAJOR)', 'EARLY CHILDHOOD CARE & EDUCATION (DOUBLE MAJOR)'),
    ('EARLY CHILDHOOD & CARE EDUCATION', 'EARLY CHILDHOOD CARE & EDUCATION'),
    ('EARLY CHILDHOOD AND CARE EDUCATION', 'EARLY CHILDHOOD CARE & EDUCATION'),
    
    -- Group 2: Language and Communication
    ('COMMUNICATION & LANGUAGE ARTS EDUCATION', 'LANGUAGE & COMMUNICATION ARTS EDUCATION'),
    ('COMMUNICATION AND LANGUAGE ARTS EDUCATION', 'LANGUAGE & COMMUNICATION ARTS EDUCATION'),
    
    -- Group 3: Peace Studies
    ('CONFLICT RESOLUTION & PEACE', 'PEACE & CONFLICT RESOLUTION'),
    ('CONFLICT & PEACE STUDIES', 'PEACE & CONFLICT RESOLUTION'),
    
    -- Group 4: Hotel and Tourism
    ('TOURISM & HOTEL MANAGEMENT', 'HOTEL & TOURISM MANAGEMENT'),
    ('HOTEL AND TOURISM MANAGEMENT', 'HOTEL & TOURISM MANAGEMENT'),
    
    -- Group 5: Labor Relations
    ('INDUSTRIAL & LABOUR RELATIONS', 'LABOUR & INDUSTRIAL RELATIONS'),
    ('INDUSTRIAL AND LABOUR RELATIONS', 'LABOUR & INDUSTRIAL RELATIONS'),
    
    -- Group 6: Security Studies
    ('INTELLIGENCE & SECURITY STUDIES', 'SECURITY & INTELLIGENCE STUDIES'),
    ('INTELLIGENCE AND SECURITY STUDIES', 'SECURITY & INTELLIGENCE STUDIES'),
    
    -- Group 7: Security Technology
    ('SECURITY MANAGEMENT & TECHNOLOGY', 'SECURITY TECHNOLOGY & MANAGEMENT'),
    ('SECURITY MANAGEMENT AND TECHNOLOGY', 'SECURITY TECHNOLOGY & MANAGEMENT'),
    
    -- Group 8: Philosophy
    ('RELIGIOUS STUDIES & PHILOSOPHY', 'PHILOSOPHY & RELIGIOUS STUDIES'),
    ('RELIGIOUS & PHILOSOPHICAL STUDIES', 'PHILOSOPHY & RELIGIOUS STUDIES'),
    
    -- Group 9: Engineering
    ('MATERIAL & METALLURGICAL ENGINEERING', 'METALLURGICAL & MATERIALS ENGINEERING'),
    ('MATERIALS AND METALLURGICAL ENGINEERING', 'METALLURGICAL & MATERIALS ENGINEERING'),
    
    -- Group 10: Hospitality
    ('TOURISM & HOSPITALITY MANAGEMENT', 'HOSPITALITY & TOURISM MANAGEMENT'),
    ('TOURISM AND HOSPITALITY MANAGEMENT', 'HOSPITALITY & TOURISM MANAGEMENT'),
    
    -- Group 11: Education Programs
    ('English Education', 'ENGLISH EDUCATION'),
    ('english education', 'ENGLISH EDUCATION'),
    ('Industrial Education Technology', 'INDUSTRIAL TECHNOLOGY EDUCATION'),
    ('INDUSTRIAL EDUCATION TECHNOLOGY', 'INDUSTRIAL TECHNOLOGY EDUCATION'),
    ('Science And Education', 'SCIENCE EDUCATION'),
    ('SCIENCE AND EDUCATION', 'SCIENCE EDUCATION'),
    ('Education Technology', 'TECHNOLOGY EDUCATION'),
    ('EDUCATION TECHNOLOGY', 'TECHNOLOGY EDUCATION');

-- Create a function to log course name changes
CREATE TABLE IF NOT EXISTS course_name_change_log (
    id SERIAL PRIMARY KEY,
    course_id INTEGER,
    old_name TEXT,
    new_name TEXT,
    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update course names and log changes
WITH updates AS (
    UPDATE course c
    SET course_name = m.new_name
    FROM course_name_mapping m
    WHERE UPPER(c.course_name) = UPPER(m.old_name)
    RETURNING c.id, c.course_name as new_name, m.old_name
)
INSERT INTO course_name_change_log (course_id, old_name, new_name)
SELECT id, old_name, new_name
FROM updates;

-- Report changes
SELECT old_name, new_name, change_timestamp
FROM course_name_change_log
ORDER BY change_timestamp DESC;

-- Cleanup
DROP TABLE course_name_mapping;

-- Verify no duplicate course names exist
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO duplicate_count
    FROM (
        SELECT UPPER(course_name)
        FROM course
        GROUP BY UPPER(course_name)
        HAVING COUNT(*) > 1
    ) dupes;
    
    IF duplicate_count > 0 THEN
        RAISE EXCEPTION 'Found % course names that still have duplicates', duplicate_count;
    END IF;
END $$;

COMMIT;
