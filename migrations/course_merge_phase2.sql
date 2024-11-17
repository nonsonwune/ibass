-- Phase 2 of Course Merge Operations
BEGIN;

-- Drop existing tables and functions if they exist
DROP TABLE IF EXISTS course_merge_log;
DROP FUNCTION IF EXISTS normalize_course_name(TEXT);
DROP FUNCTION IF EXISTS merge_course_requirements(INTEGER, INTEGER);
DROP FUNCTION IF EXISTS find_and_merge_similar_courses();

-- Create a function to normalize course names
CREATE OR REPLACE FUNCTION normalize_course_name(course_name TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN TRIM(REGEXP_REPLACE(
        UPPER(course_name),
        '[\s\-_]+',  -- Replace multiple spaces/hyphens/underscores
        ' ',         -- with a single space
        'g'
    ));
END;
$$ LANGUAGE plpgsql IMMUTABLE;  -- Mark as IMMUTABLE since it always returns the same output for the same input

-- Create a table to log merge operations
CREATE TABLE course_merge_log (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    source_name TEXT,
    target_name TEXT,
    merge_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    merge_reason TEXT
);

-- Function to merge course requirements
CREATE OR REPLACE FUNCTION merge_course_requirements(
    source_id INTEGER,
    target_id INTEGER
) RETURNS VOID AS $$
BEGIN
    -- Update course requirements to point to target course
    UPDATE course_requirement
    SET course_id = target_id
    WHERE course_id = source_id
    AND NOT EXISTS (
        SELECT 1 FROM course_requirement cr2
        WHERE cr2.course_id = target_id
        AND cr2.utme_template_id = course_requirement.utme_template_id
        AND cr2.de_template_id = course_requirement.de_template_id
    );
    
    -- Delete any duplicate requirements
    DELETE FROM course_requirement
    WHERE course_id = source_id;
END;
$$ LANGUAGE plpgsql;

-- Function to find and merge similar courses
CREATE OR REPLACE FUNCTION find_and_merge_similar_courses() RETURNS INTEGER AS $$
DECLARE
    merged_count INTEGER := 0;
    source_record RECORD;
    target_record RECORD;
BEGIN
    -- Find courses with similar names
    FOR source_record IN (
        SELECT c1.id as source_id, 
               c1.course_name as source_name,
               c2.id as target_id,
               c2.course_name as target_name
        FROM course c1
        JOIN course c2 ON normalize_course_name(c1.course_name) = normalize_course_name(c2.course_name)
        WHERE c1.id < c2.id  -- Ensure we don't process the same pair twice
    ) LOOP
        -- Merge the courses
        PERFORM merge_course_requirements(source_record.source_id, source_record.target_id);
        
        -- Log the merge operation
        INSERT INTO course_merge_log (
            source_id, 
            target_id, 
            source_name, 
            target_name, 
            merge_reason
        ) VALUES (
            source_record.source_id,
            source_record.target_id,
            source_record.source_name,
            source_record.target_name,
            'Automatic merge - similar names'
        );
        
        -- Delete the source course
        DELETE FROM course WHERE id = source_record.source_id;
        
        merged_count := merged_count + 1;
    END LOOP;
    
    RETURN merged_count;
END;
$$ LANGUAGE plpgsql;

-- Execute the merge operation
SELECT find_and_merge_similar_courses();

-- Create indexes to improve performance
CREATE INDEX IF NOT EXISTS idx_normalized_course_name 
ON course (normalize_course_name(course_name));

-- Verify data integrity
DO $$
DECLARE
    orphaned_requirements INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphaned_requirements
    FROM course_requirement cr
    LEFT JOIN course c ON cr.course_id = c.id
    WHERE c.id IS NULL;
    
    IF orphaned_requirements > 0 THEN
        RAISE EXCEPTION 'Found % orphaned course requirements', orphaned_requirements;
    END IF;
END $$;

COMMIT;
