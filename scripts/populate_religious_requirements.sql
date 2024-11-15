-- Populate religious_institution_requirements table
INSERT INTO religious_institution_requirements (university_id, entry_requirements, special_provisions, created_at)
VALUES
    -- ECWA Theological Seminary
    (
        (SELECT id FROM university WHERE university_name ILIKE '%ecwa theological%' LIMIT 1),
        '{
            "o_level": {
                "compulsory_subjects": ["English Language"],
                "min_credits": 5,
                "max_sittings": 2,
                "mathematics_requirement": "Pass acceptable for most programs"
            },
            "utme": {
                "subjects": ["English Language", "Any other three relevant subjects"],
                "min_score": 160
            },
            "direct_entry": {
                "qualifications": [
                    "NCE with minimum of Merit in relevant subjects",
                    "ND with minimum of Upper Credit in relevant field",
                    "HND with minimum of Lower Credit in relevant field",
                    "First Degree with minimum of Third Class in relevant field"
                ]
            }
        }',
        '{
            "religious_requirements": [
                "Letter of recommendation from ECWA pastor",
                "Evidence of ECWA church membership",
                "Character testimonial",
                "Statement of faith"
            ],
            "dress_code": {
                "general": "Conservative and decent dressing required",
                "specific": [
                    "No revealing clothes",
                    "No tight-fitting clothes",
                    "Appropriate length for skirts and dresses",
                    "No offensive prints or inscriptions"
                ]
            },
            "behavioral_expectations": [
                "Regular attendance at chapel services",
                "Participation in religious activities",
                "Adherence to ECWA values and ethics",
                "Active involvement in ministry work"
            ],
            "special_notes": [
                "Strong emphasis on theological training",
                "Focus on pastoral ministry preparation",
                "Evangelical Christian worldview required"
            ]
        }',
        CURRENT_TIMESTAMP
    ),

    -- Spiritan School of Theology
    (
        (SELECT id FROM university WHERE university_name ILIKE '%spiritan school%' LIMIT 1),
        '{
            "o_level": {
                "compulsory_subjects": ["English Language"],
                "min_credits": 5,
                "max_sittings": 2,
                "mathematics_requirement": "Pass acceptable for most programs"
            },
            "utme": {
                "subjects": ["English Language", "Any other three relevant subjects"],
                "min_score": 160
            },
            "direct_entry": {
                "qualifications": [
                    "NCE with minimum of Merit in relevant subjects",
                    "ND with minimum of Upper Credit in relevant field",
                    "HND with minimum of Lower Credit in relevant field",
                    "First Degree with minimum of Third Class in relevant field"
                ]
            }
        }',
        '{
            "religious_requirements": [
                "Letter of recommendation from Catholic priest",
                "Baptismal certificate",
                "Confirmation certificate",
                "Character testimonial"
            ],
            "dress_code": {
                "general": "Conservative and decent dressing required",
                "specific": [
                    "No revealing clothes",
                    "No tight-fitting clothes",
                    "Appropriate length for skirts and dresses",
                    "No offensive prints or inscriptions"
                ]
            },
            "behavioral_expectations": [
                "Regular attendance at Mass",
                "Participation in religious activities",
                "Adherence to Catholic values and ethics",
                "Active involvement in spiritual formation"
            ],
            "special_notes": [
                "Strong emphasis on Catholic theology",
                "Focus on priestly formation",
                "Catholic faith commitment required"
            ]
        }',
        CURRENT_TIMESTAMP
    ),

    -- Baptist Theological Seminary
    (
        (SELECT id FROM university WHERE university_name ILIKE '%baptist theological%' LIMIT 1),
        '{
            "o_level": {
                "compulsory_subjects": ["English Language"],
                "min_credits": 5,
                "max_sittings": 2,
                "mathematics_requirement": "Pass acceptable for most programs"
            },
            "utme": {
                "subjects": ["English Language", "Any other three relevant subjects"],
                "min_score": 160
            },
            "direct_entry": {
                "qualifications": [
                    "NCE with minimum of Merit in relevant subjects",
                    "ND with minimum of Upper Credit in relevant field",
                    "HND with minimum of Lower Credit in relevant field",
                    "First Degree with minimum of Third Class in relevant field"
                ]
            }
        }',
        '{
            "religious_requirements": [
                "Letter of recommendation from Baptist pastor",
                "Evidence of Baptist church membership",
                "Character testimonial",
                "Statement of faith"
            ],
            "dress_code": {
                "general": "Conservative and decent dressing required",
                "specific": [
                    "No revealing clothes",
                    "No tight-fitting clothes",
                    "Appropriate length for skirts and dresses",
                    "No offensive prints or inscriptions"
                ]
            },
            "behavioral_expectations": [
                "Regular attendance at chapel services",
                "Participation in religious activities",
                "Adherence to Baptist values and ethics",
                "Active involvement in ministry work"
            ],
            "special_notes": [
                "Strong emphasis on Baptist theology",
                "Focus on pastoral ministry preparation",
                "Baptist faith commitment required"
            ]
        }',
        CURRENT_TIMESTAMP
    ),

    -- Methodist Theological Institute
    (
        (SELECT id FROM university WHERE university_name ILIKE '%methodist theological%' LIMIT 1),
        '{
            "o_level": {
                "compulsory_subjects": ["English Language"],
                "min_credits": 5,
                "max_sittings": 2,
                "mathematics_requirement": "Pass acceptable for most programs"
            },
            "utme": {
                "subjects": ["English Language", "Any other three relevant subjects"],
                "min_score": 160
            },
            "direct_entry": {
                "qualifications": [
                    "NCE with minimum of Merit in relevant subjects",
                    "ND with minimum of Upper Credit in relevant field",
                    "HND with minimum of Lower Credit in relevant field",
                    "First Degree with minimum of Third Class in relevant field"
                ]
            }
        }',
        '{
            "religious_requirements": [
                "Letter of recommendation from Methodist minister",
                "Evidence of Methodist church membership",
                "Character testimonial",
                "Statement of faith"
            ],
            "dress_code": {
                "general": "Conservative and decent dressing required",
                "specific": [
                    "No revealing clothes",
                    "No tight-fitting clothes",
                    "Appropriate length for skirts and dresses",
                    "No offensive prints or inscriptions"
                ]
            },
            "behavioral_expectations": [
                "Regular attendance at chapel services",
                "Participation in religious activities",
                "Adherence to Methodist values and ethics",
                "Active involvement in ministry work"
            ],
            "special_notes": [
                "Strong emphasis on Methodist theology",
                "Focus on pastoral ministry preparation",
                "Methodist faith commitment required"
            ]
        }',
        CURRENT_TIMESTAMP
    ),

    -- Assemblies of God Divinity School
    (
        (SELECT id FROM university WHERE university_name ILIKE '%assemblies of god%' LIMIT 1),
        '{
            "o_level": {
                "compulsory_subjects": ["English Language"],
                "min_credits": 5,
                "max_sittings": 2,
                "mathematics_requirement": "Pass acceptable for most programs"
            },
            "utme": {
                "subjects": ["English Language", "Any other three relevant subjects"],
                "min_score": 160
            },
            "direct_entry": {
                "qualifications": [
                    "NCE with minimum of Merit in relevant subjects",
                    "ND with minimum of Upper Credit in relevant field",
                    "HND with minimum of Lower Credit in relevant field",
                    "First Degree with minimum of Third Class in relevant field"
                ]
            }
        }',
        '{
            "religious_requirements": [
                "Letter of recommendation from AG pastor",
                "Evidence of AG church membership",
                "Character testimonial",
                "Statement of faith"
            ],
            "dress_code": {
                "general": "Conservative and decent dressing required",
                "specific": [
                    "No revealing clothes",
                    "No tight-fitting clothes",
                    "Appropriate length for skirts and dresses",
                    "No offensive prints or inscriptions"
                ]
            },
            "behavioral_expectations": [
                "Regular attendance at chapel services",
                "Participation in religious activities",
                "Adherence to AG values and ethics",
                "Active involvement in ministry work"
            ],
            "special_notes": [
                "Strong emphasis on Pentecostal theology",
                "Focus on pastoral ministry preparation",
                "Pentecostal faith commitment required"
            ]
        }',
        CURRENT_TIMESTAMP
    ),

    -- Immanuel College of Theology
    (
        (SELECT id FROM university WHERE university_name ILIKE '%immanuel college%' LIMIT 1),
        '{
            "o_level": {
                "compulsory_subjects": ["English Language"],
                "min_credits": 5,
                "max_sittings": 2,
                "mathematics_requirement": "Pass acceptable for most programs"
            },
            "utme": {
                "subjects": ["English Language", "Any other three relevant subjects"],
                "min_score": 160
            },
            "direct_entry": {
                "qualifications": [
                    "NCE with minimum of Merit in relevant subjects",
                    "ND with minimum of Upper Credit in relevant field",
                    "HND with minimum of Lower Credit in relevant field",
                    "First Degree with minimum of Third Class in relevant field"
                ]
            }
        }',
        '{
            "religious_requirements": [
                "Letter of recommendation from church leader",
                "Evidence of church membership",
                "Character testimonial",
                "Statement of faith"
            ],
            "dress_code": {
                "general": "Conservative and decent dressing required",
                "specific": [
                    "No revealing clothes",
                    "No tight-fitting clothes",
                    "Appropriate length for skirts and dresses",
                    "No offensive prints or inscriptions"
                ]
            },
            "behavioral_expectations": [
                "Regular attendance at chapel services",
                "Participation in religious activities",
                "Adherence to Christian values and ethics",
                "Active involvement in ministry work"
            ],
            "special_notes": [
                "Strong emphasis on theological training",
                "Focus on pastoral ministry preparation",
                "Christian faith commitment required"
            ]
        }',
        CURRENT_TIMESTAMP
    )
ON CONFLICT (university_id) DO UPDATE 
SET 
    entry_requirements = EXCLUDED.entry_requirements,
    special_provisions = EXCLUDED.special_provisions,
    created_at = CURRENT_TIMESTAMP;
