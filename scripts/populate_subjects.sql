-- Populate subject categories
INSERT INTO subject_categories (name) VALUES
    ('Pure Sciences'),
    ('Applied Sciences'),
    ('Languages'),
    ('Core Social Sciences'),
    ('Business Studies'),
    ('Humanities'),
    ('Arts'),
    ('Technical/Vocational')
ON CONFLICT (name) DO NOTHING;

-- Populate subjects
INSERT INTO subjects (name, category_id, is_core)
SELECT 'English Language', id, true FROM subject_categories WHERE name = 'Languages'
ON CONFLICT (name) DO NOTHING;

-- Pure Sciences
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, s.is_core
FROM (
    VALUES 
        ('Mathematics', true),
        ('Physics', false),
        ('Chemistry', false),
        ('Biology', false),
        ('Agricultural Science', false),
        ('Health Science', false)
) as s(subject, is_core)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Pure Sciences'
ON CONFLICT (name) DO NOTHING;

-- Applied Sciences
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, false
FROM (
    VALUES 
        ('Technical Drawing'),
        ('Basic Electronics'),
        ('Basic Technology'),
        ('Computer Studies'),
        ('Food and Nutrition'),
        ('Applied Electricity')
) as s(subject)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Applied Sciences'
ON CONFLICT (name) DO NOTHING;

-- Languages
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, false
FROM (
    VALUES 
        ('Literature in English'),
        ('French'),
        ('Igbo'),
        ('Yoruba'),
        ('Hausa'),
        ('Arabic')
) as s(subject)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Languages'
ON CONFLICT (name) DO NOTHING;

-- Core Social Sciences
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, false
FROM (
    VALUES 
        ('Economics'),
        ('Geography'),
        ('Government'),
        ('History'),
        ('Social Studies'),
        ('Civic Education')
) as s(subject)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Core Social Sciences'
ON CONFLICT (name) DO NOTHING;

-- Business Studies
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, false
FROM (
    VALUES 
        ('Commerce'),
        ('Accounting'),
        ('Business Studies'),
        ('Marketing'),
        ('Office Practice')
) as s(subject)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Business Studies'
ON CONFLICT (name) DO NOTHING;

-- Humanities
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, false
FROM (
    VALUES 
        ('Christian Religious Studies'),
        ('Islamic Studies'),
        ('Music'),
        ('Visual Arts'),
        ('Fine Arts')
) as s(subject)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Humanities'
ON CONFLICT (name) DO NOTHING;

-- Arts and Vocational
INSERT INTO subjects (name, category_id, is_core)
SELECT s.subject, sc.id, false
FROM (
    VALUES 
        ('Home Economics'),
        ('Agricultural Science'),
        ('Metal Work'),
        ('Wood Work'),
        ('Auto Mechanics')
) as s(subject)
CROSS JOIN subject_categories sc
WHERE sc.name = 'Technical/Vocational'
ON CONFLICT (name) DO NOTHING;
