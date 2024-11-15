-- Create special requirements table
CREATE TABLE IF NOT EXISTS special_requirement (
    id SERIAL PRIMARY KEY,
    university_id INTEGER NOT NULL REFERENCES university(id) ON DELETE CASCADE,
    requirements JSONB,
    special_notes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on university_id for faster lookups
CREATE INDEX IF NOT EXISTS ix_special_requirement_university_id ON special_requirement(university_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at timestamp
DROP TRIGGER IF EXISTS update_special_requirement_updated_at ON special_requirement;
CREATE TRIGGER update_special_requirement_updated_at
    BEFORE UPDATE ON special_requirement
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data only if universities exist
DO $$
DECLARE
    uni_id integer;
BEGIN
    -- Get the first university ID from the database
    SELECT id INTO uni_id FROM university LIMIT 1;
    
    -- Only insert if we found a university
    IF uni_id IS NOT NULL THEN
        INSERT INTO special_requirement (university_id, requirements, special_notes)
        VALUES 
        (uni_id, 
         '{
            "mathematics_requirement": {
                "condition": "Credit pass mandatory",
                "applicable_programs": ["All Education programs"]
            },
            "english_requirement": {
                "condition": "Credit pass required",
                "applicable_programs": ["All programs"]
            }
         }'::jsonb,
         '["Additional mathematics courses may be required for specific programs", 
           "English proficiency test may be required for international students"]'::jsonb
        );
    END IF;
END $$;
