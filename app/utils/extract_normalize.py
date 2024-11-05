# app/utils/extract_normalize.py
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from ..models.subject import SubjectCategories, Subjects
from ..models.requirement import CourseRequirement

class SubjectExtractor:
    def __init__(self, json_data=None):

        self.subject_patterns = {
            'english': r'English\s+Language|English\b',
            'mathematics': r'Mathematics|Math\b|Mathematic\b',
            'biology': r'Biology|Agricultural Science|Health Science',
            'chemistry': r'Chemistry',
            'physics': r'Physics|Applied Physics|Basic Physics',
            'economics': r'Economics|Business Studies|Commercial Studies',
            'literature': r'Literature\s+in\s+English|Literature',
            'government': r'Government|Civics',
            'geography': r'Geography',
            'history': r'History',
            'computer_science': r'Computer Science|Computing|ICT',
            'technical': r'Technical Drawing|Engineering Drawing|Metal Work|Wood Work',
            'arts': r'Fine Arts?|Creative Arts?|Visual Arts?',
            'vocational': r'Home Economics|Food and Nutrition|Agricultural Science',
            'religious': r'CRK|Christian Religious Studies|Islamic Studies|IRK',
            'language': r'French|Hausa|Igbo|Yoruba|Arabic'
        }
        
        self.category_mappings = {
            'english': 'language_arts',
            'mathematics': 'mathematical_sciences',
            'biology': 'pure_sciences',
            'chemistry': 'pure_sciences',
            'physics': 'pure_sciences',
            'economics': 'social_sciences',
            'literature': 'language_arts',
            'government': 'social_sciences',
            'geography': 'earth_sciences',
            'history': 'humanities',
            'computer_science': 'applied_sciences',
            'technical': 'applied_sciences',
            'arts': 'creative_arts',
            'vocational': 'vocational_studies',
            'religious': 'humanities',
            'language': 'language_arts'
        }

        self.subject_aliases = {
            'english': ['eng', 'eng lang', 'english language'],
            'mathematics': ['math', 'maths', 'further maths', 'further mathematics'],
            'biology': ['bio', 'agric', 'agricultural science', 'health science'],
            'economics': ['econs', 'business studies', 'commerce'],
            'literature': ['lit', 'lit in eng', 'english literature'],
            'computer_science': ['computer', 'computing', 'ict', 'information technology'],
            'technical': ['tech drawing', 'engineering drawing', 'metalwork', 'woodwork'],
            'religious': ['crk', 'irk', 'islamic studies', 'christian religious studies']
        }
        
        self.additional_categories = {
            'vocational_technical': [
                'Fabrication', 'Glass', 'Construction', 'Maintenance',
                'Foundry Technology', 'Needle Work', 'Air Conditioning',
                'Furniture Making', 'Electronics', 'Type Writing',
                'Engine Maintenance', 'Transmission System'
            ],
            'examination_types': [
                'WAEC', 'NECO', 'NABTEB', 'SSCE', 'GCE', 'JUPEB'
            ],
            'academic_requirements': [
                'Credit Pass', 'Merit', 'Distinction', 'Grade II',
                'Ordinary Level', 'Advanced Level'
            ]
        }

        # Load JSON data
        self.json_data = json_data
        if json_data is None:
            try:
                import json
                with open('app/data/inst_data.json', 'r') as f:
                    self.json_data = json.load(f)
            except Exception as e:
                raise ValueError(f"Failed to load JSON data: {str(e)}")
        else:
            self.json_data = json_data
            
        # Validate JSON structure and data
        self._validate_json_structure()
        validation_errors = self._validate_subject_data()
        if validation_errors:
            raise ValueError(f"Invalid subject data: {', '.join(validation_errors)}")

    def _validate_json_structure(self):
        """Validate the JSON data structure"""
        if not self.json_data or not isinstance(self.json_data, dict):
            raise ValueError("Invalid JSON data format")
            
        if 'subject_classifications' not in self.json_data:
            raise ValueError("Missing 'subject_classifications' in JSON data")
            
        classifications = self.json_data['subject_classifications']
        if not isinstance(classifications, dict):
            raise ValueError("Invalid 'subject_classifications' format")

    def _validate_subject_data(self):
        """Validate the structure and content of subject data"""
        validation_errors = []
        
        if 'subject_classifications' not in self.json_data:
            return ["Missing subject_classifications"]
            
        for category_name, category in self.json_data['subject_classifications'].items():
            if not isinstance(category, dict):
                validation_errors.append(f"Invalid category structure for {category_name}")
                continue
                
            for subcategory_name, subjects in category.items():
                if not isinstance(subjects, list):
                    validation_errors.append(
                        f"Invalid subjects list in {category_name}.{subcategory_name}"
                    )
                else:
                    # Validate individual subjects
                    for idx, subject in enumerate(subjects):
                        if not isinstance(subject, str):
                            validation_errors.append(
                                f"Invalid subject at {category_name}.{subcategory_name}[{idx}]"
                            )
                        elif not subject.strip():
                            validation_errors.append(
                                f"Empty subject at {category_name}.{subcategory_name}[{idx}]"
                            )
        
        return validation_errors

    def extract_subjects_from_text(self, text: str) -> Set[str]:
        """Extract subject names with enhanced cleaning and validation."""
        if not text:
            return set()

        subjects = set()
        text = text.strip()

        # Clean requirement text first
        requirement_patterns = [
            r'at\s+not\s+more\s+than\s+(one|two)\s+sittings?',
            r'obtained\s+at',
            r'or\s+their\s+equivalents?',
            r'which\s+includes?',
            r'as\s+follows',
            r'subjects?\s+at\s+ssce',
            r'with\s+a\s+least',
            r'certificate\s+or',
            r'level\s+subjects?',
            r'credit\s+pass(?:es)?',
            r'minimum\s+of',
            r'maximum\s+of',
            r'candidates?\s+(?:must|should|are)\s+(?:have|possess)',
            r'required\s+to\s+have',
            r'in\s+addition\s+to',
            r'including',
            r'such\s+as',
            r'any\s+of\s+the\s+following',
            r'credit\s+in',
            r'pass\s+in',
            r'at\s+least',
            r'examination\s+in',
            r'or\s+equivalent',
            r'senior\s+secondary'
        ]

        cleaned_text = text
        for pattern in requirement_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)

        # First pass: Extract using subject patterns
        for subject_type, pattern in self.subject_patterns.items():
            matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
            for match in matches:
                subject = match.group().strip()
                normalized = self.normalize_subject_name(subject)
                if normalized and len(normalized) > 1:
                    subjects.add(normalized)

        # Second pass: Split on multiple delimiters
        delimiters = r'[,;/]|\s+and\s+|\s+or\s+|\s+plus\s+|\s+with\s+|\s+in\s+'
        parts = [p.strip() for p in re.split(delimiters, cleaned_text) if p.strip()]

        for part in parts:
            # Skip parts that look like requirements
            if re.search(r'credit|pass|minimum|maximum|candidate|require|possess|sitting|obtained|certificate|equivalent|ssce|neco|waec|general|must|should', 
                        part, re.IGNORECASE):
                continue

            # Look for potential subjects with improved pattern
            subject_pattern = r'([A-Z][a-zA-Z]+(?:[- ][A-Z][a-zA-Z]+)*(?:\s*[IVX]+)?)'
            potential_subjects = re.finditer(subject_pattern, part)

            for match in potential_subjects:
                subject = match.group().strip()
                
                # Skip if it's a known non-subject term
                if subject.lower() in {
                    'ssce', 'neco', 'waec', 'general', 'certificate', 
                    'examination', 'level', 'credit', 'pass'
                }:
                    continue

                # Try to normalize and validate the subject
                normalized = self.normalize_subject_name(subject)
                if not normalized:
                    continue

                # Check if it's in approved subjects list
                for category in self.json_data['subject_classifications'].values():
                    for subjects_list in category.values():
                        if isinstance(subjects_list, list):
                            if any(self._subjects_match(normalized, s) for s in subjects_list):
                                subjects.add(normalized)
                                break

                # Also add if it matches our known patterns
                if any(re.match(pattern, normalized, re.IGNORECASE) 
                      for pattern in self.subject_patterns.values()):
                    subjects.add(normalized)

        # Final cleanup: Handle special cases and combinations
        final_subjects = set()
        for subject in subjects:
            if '/' in subject:  # Handle combined subjects
                parts = [p.strip() for p in subject.split('/')]
                for part in parts:
                    if self._is_valid_subject(part):
                        normalized = self.normalize_subject_name(part)
                        if normalized:
                            final_subjects.add(normalized)
            elif self._is_valid_subject(subject):
                final_subjects.add(subject)

        return final_subjects

    def _subjects_match(self, subject1: str, subject2: str) -> bool:
        """Compare two subjects accounting for variations."""
        s1 = re.sub(r'[-\s]+', '', subject1.lower())
        s2 = re.sub(r'[-\s]+', '', subject2.lower())
        
        # Direct match
        if s1 == s2:
            return True
            
        # Check aliases
        for aliases in self.subject_aliases.values():
            normalized_aliases = [re.sub(r'[-\s]+', '', a.lower()) for a in aliases]
            if s1 in normalized_aliases and s2 in normalized_aliases:
                return True
                
        return False

    def _is_valid_subject(self, subject: str) -> bool:
        """Validate if a string represents a valid subject."""
        if not subject or len(subject) < 2:
            return False

        # Remove spaces and hyphens for comparison
        normalized = re.sub(r'[-\s]+', '', subject.lower())

        # Check against known patterns
        if any(re.match(pattern, subject, re.IGNORECASE) 
               for pattern in self.subject_patterns.values()):
            return True

        # Check against aliases
        for aliases in self.subject_aliases.values():
            normalized_aliases = [re.sub(r'[-\s]+', '', a.lower()) for a in aliases]
            if normalized in normalized_aliases:
                return True

        # Check against approved subjects
        for category in self.json_data['subject_classifications'].values():
            for subjects in category.values():
                if isinstance(subjects, list):
                    if any(self._subjects_match(subject, s) for s in subjects):
                        return True

        # Final validation for subject name format
        return bool(re.match(r'^[A-Z][a-zA-Z]*(?:[-\s][A-Z][a-zA-Z]*)*$', subject))

    def normalize_subject_name(self, subject: str) -> str:
        """Enhanced normalization with better text cleaning."""
        if not subject or len(subject) < 2:
            return ""
            
        # Clean requirement-specific phrases
        requirement_patterns = [
            r'at\s+not\s+more\s+than\s+(one|two)\s+sitting[s]?',
            r'obtained\s+at',
            r'or\s+their\s+equivalents?',
            r'which\s+includes?',
            r'as\s+follows',
            r'subjects?\s+at\s+ssce',
            r'with\s+a\s+least',
            r'certificate\s+or',
            r'level\s+subjects?'
        ]
        
        cleaned_subject = subject.strip().lower()
        for pattern in requirement_patterns:
            cleaned_subject = re.sub(pattern, '', cleaned_subject, flags=re.IGNORECASE)
            
        # Split composite strings and take the most likely subject
        parts = [p.strip() for p in cleaned_subject.split() if p.strip()]
        if not parts:
            return ""
            
        # Check known subject names first
        for part in parts:
            if any(part in alias.lower() for aliases in self.subject_aliases.values() for alias in aliases):
                return self.get_standard_name(part)
                
        # Try to match with approved subjects from JSON
        approved_subjects = set()
        for category in self.json_data['subject_classifications'].values():
            for subcategory in category.values():
                if isinstance(subcategory, list):
                    approved_subjects.update(s.lower() for s in subcategory)
        
        for part in parts:
            if part in approved_subjects:
                return part.title()
                
        # Return the first capitalized word that looks like a subject
        for part in parts:
            if re.match(r'^[A-Z][a-z]+$', part):
                return part
                
        return ""
    
    def get_standard_name(self, subject: str) -> str:
        """Get standard name for a known subject."""
        subject = subject.lower().strip()
        
        # Check direct matches first
        for standard_name, aliases in self.subject_aliases.items():
            if subject in [a.lower() for a in aliases]:
                return standard_name.title()
                
        # Check pattern matches
        for subject_type, pattern in self.subject_patterns.items():
            if re.match(pattern, subject, re.IGNORECASE):
                return subject_type.title()
                
        return subject.title()

    def get_subject_category(self, subject: str) -> str:
        normalized_subject = self.normalize_subject_name(subject).lower()
        
        # Check additional categories first
        for category, subjects in self.additional_categories.items():
            if any(s.lower() in normalized_subject for s in subjects):
                return category
                
        # Existing category logic...
        for subject_key, category in self.category_mappings.items():
            if subject_key in normalized_subject:
                return category
                
        # Enhanced heuristics
        if re.search(r'technology|engineering|technical', normalized_subject, re.IGNORECASE):
            return 'applied_sciences'
            
        if re.search(r'craft|practical|workshop', normalized_subject, re.IGNORECASE):
            return 'vocational_technical'
            
        if re.search(r'certificate|examination|level', normalized_subject, re.IGNORECASE):
            return 'examination_types'
            
        return 'other'

def clean_requirement_text(text: str) -> str:
    """Clean and normalize requirement text."""
    if not text:
        return ""
        
    # Remove common boilerplate phrases
    boilerplate = [
        r"candidates must have",
        r"candidates should possess",
        r"candidates are required to have",
        r"credit passes? in",
        r"at not more than two sittings",
        r"candidates who have successfully completed",
        r"senior secondary school certificate or its equivalent",
    ]
    
    cleaned = text.strip()
    for phrase in boilerplate:
        cleaned = re.sub(phrase, "", cleaned, flags=re.IGNORECASE)
    
    # Normalize subject names
    cleaned = re.sub(r"(?i)eng\b", "English", cleaned)
    cleaned = re.sub(r"(?i)math\b", "Mathematics", cleaned)
    cleaned = re.sub(r"(?i)bio\b", "Biology", cleaned)
    
    # Remove redundant whitespace
    cleaned = " ".join(cleaned.split())
    
    return cleaned

class RequirementExtractor:
    def __init__(self, subject_extractor: SubjectExtractor):
        self.subject_extractor = subject_extractor

    def parse_requirements(self, requirements_text: str) -> Dict:
        """Parse requirements with improved text cleaning."""
        requirements_text = clean_requirement_text(requirements_text)
        
        result = {
            'min_credits': 5,  # Default value
            'max_sittings': 2,  # Default value
            'mandatory_subjects': set(),
            'optional_subjects': set()
        }
        
        if not requirements_text:
            return result

        # Extract credit requirement
        credit_match = re.search(r'(\d+)\s*(?:credit|credits)', requirements_text, re.IGNORECASE)
        if credit_match:
            result['min_credits'] = int(credit_match.group(1))

        # Extract sitting requirement
        sitting_match = re.search(r'(\d+)\s*sitting', requirements_text, re.IGNORECASE)
        if sitting_match:
            result['max_sittings'] = int(sitting_match.group(1))

        # Extract mandatory subjects
        mandatory_pattern = r'must\s+include|mandatory|required|compulsory'
        mandatory_match = re.search(f"({mandatory_pattern}).*?(?=\.|$)", requirements_text, re.IGNORECASE)
        if mandatory_match:
            mandatory_text = mandatory_match.group(0)
            result['mandatory_subjects'].update(
                self.subject_extractor.extract_subjects_from_text(mandatory_text)
            )

        # Extract all subjects and add non-mandatory ones to optional
        all_subjects = self.subject_extractor.extract_subjects_from_text(requirements_text)
        result['optional_subjects'] = all_subjects - result['mandatory_subjects']

        return result

def populate_subjects_and_categories(db, json_data, existing_courses):
    """Populate the subject-related tables with data from both sources."""
    subject_extractor = SubjectExtractor()
    requirement_extractor = RequirementExtractor(subject_extractor)
    
    # Create category records
    category_ids = {}
    for category_name in set(subject_extractor.category_mappings.values()):
        category = db.session.query(SubjectCategories).filter_by(name=category_name).first()
        if not category:
            category = SubjectCategories(name=category_name)
            db.session.add(category)
            db.session.flush()
        category_ids[category_name] = category.id

    # Extract subjects from JSON
    json_subjects = set()
    for category in json_data['subject_classifications'].values():
        for subjects in category.values():
            if isinstance(subjects, list):
                json_subjects.update(subjects)

    # Extract subjects from existing courses
    db_subjects = set()
    for course in existing_courses:
        if course.utme_requirements:
            parsed = requirement_extractor.parse_requirements(course.utme_requirements)
            db_subjects.update(parsed['mandatory_subjects'])
            db_subjects.update(parsed['optional_subjects'])

    # Combine and normalize all subjects
    all_subjects = json_subjects.union(db_subjects)
    normalized_subjects = {
        subject_extractor.normalize_subject_name(subject): subject_extractor.get_subject_category(subject)
        for subject in all_subjects
    }

    # Create subject records
    for subject_name, category in normalized_subjects.items():
        subject = db.session.query(Subjects).filter_by(name=subject_name).first()
        if not subject:
            subject = Subjects(
                name=subject_name,
                category_id=category_ids[category],
                is_core=subject_name.lower() in ['english language', 'mathematics']
            )
            db.session.add(subject)

    db.session.commit()

def create_course_templates(db, courses):
    """Create course requirement templates from existing courses."""
    requirement_extractor = RequirementExtractor(SubjectExtractor())
    template_cache = {}

    for course in courses:
        if not course.utme_requirements:
            continue

        # Create template if it doesn't exist
        if course.course_name not in template_cache:
            requirements = requirement_extractor.parse_requirements(course.utme_requirements)
            
            template = CourseRequirementTemplates(
                name=course.course_name,
                min_credits=requirements['min_credits'],
                max_sittings=requirements['max_sittings']
            )
            db.session.add(template)
            db.session.flush()
            template_cache[course.course_name] = template.id

            # Add subject requirements
            for subject_name in requirements['mandatory_subjects']:
                subject = db.session.query(Subjects).filter_by(
                    name=subject_name
                ).first()
                if subject:
                    req = TemplateSubjectRequirements(
                        template_id=template.id,
                        subject_id=subject.id,
                        is_mandatory=True
                    )
                    db.session.add(req)

            for subject_name in requirements['optional_subjects']:
                subject = db.session.query(Subjects).filter_by(
                    name=subject_name
                ).first()
                if subject:
                    req = TemplateSubjectRequirements(
                        template_id=template.id,
                        subject_id=subject.id,
                        is_mandatory=False
                    )
                    db.session.add(req)

    db.session.commit()