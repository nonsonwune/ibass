-- Create change log table
CREATE TABLE IF NOT EXISTS requirement_change_log (
    id SERIAL PRIMARY KEY,
    course_name TEXT NOT NULL,
    requirement_type TEXT NOT NULL,
    old_requirement TEXT NOT NULL,
    new_requirement TEXT NOT NULL,
    confidence_score NUMERIC NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
