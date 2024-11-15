-- Check if we have any special requirements
SELECT sr.id, 
       u.university_name,
       sr.requirements,
       sr.special_notes,
       sr.created_at
FROM special_requirement sr
JOIN university u ON u.id = sr.university_id;
