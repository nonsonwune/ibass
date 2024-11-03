from typing import Dict, List, Set, Tuple, Optional
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, ProgrammingError
from datetime import datetime
import logging
from dataclasses import dataclass, field
from ..extensions import db
from .extract_normalize import SubjectExtractor, RequirementExtractor
from ..models.subject import (
    SubjectCategories,
    Subjects
)
from ..models.requirement import (
    CourseRequirementTemplates,
    TemplateSubjectRequirements,
    InstitutionRequirements,
    InstitutionSubjectRequirements
)
from ..models.university import Course, University
from contextlib import contextmanager
from sqlalchemy import inspect, text
import re

logger = logging.getLogger(__name__)

@dataclass
class MigrationStats:
    """Enhanced stats tracking with atomic counters and validation."""
    subjects_created: int = 0
    templates_created: int = 0
    requirements_created: int = 0
    subjects_updated: int = 0
    templates_updated: int = 0
    requirements_updated: int = 0
    errors: List[str] = field(default_factory=list)
    _checkpoints: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def create_checkpoint(self, name: str) -> None:
        """Create a stats checkpoint for rollback."""
        self._checkpoints[name] = {
            'subjects_created': self.subjects_created,
            'templates_created': self.templates_created,
            'requirements_created': self.requirements_created,
            'subjects_updated': self.subjects_updated,
            'templates_updated': self.templates_updated,
            'requirements_updated': self.requirements_updated
        }

    def rollback_to_checkpoint(self, name: str) -> None:
        """Rollback stats to a checkpoint."""
        if name in self._checkpoints:
            checkpoint = self._checkpoints[name]
            for key, value in checkpoint.items():
                setattr(self, key, value)
    
    def get_summary(self) -> Dict[str, int]:
        """Get a summary of all migration stats."""
        return {
            'subjects_created': self.subjects_created,
            'templates_created': self.templates_created,
            'requirements_created': self.requirements_created,
            'subjects_updated': self.subjects_updated,
            'templates_updated': self.templates_updated,
            'requirements_updated': self.requirements_updated,
            'total_errors': len(self.errors)
        }

class DataMigrationManager:
    """Manages data migration with enhanced error handling and stats tracking."""
    
    BATCH_SIZE = 1000
    MAX_ERRORS = 50

    def __init__(self, db, json_data):
        self.db = db
        self.json_data = json_data
        self.subject_extractor = SubjectExtractor()
        self.requirement_extractor = RequirementExtractor(self.subject_extractor)
        self.stats = MigrationStats()
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def batch_operation(self, description: str):
        """Context manager for handling batch operations with proper error handling."""
        try:
            self.logger.info(f"Starting {description}...")
            self.stats.create_checkpoint(description)
            
            with self.db.session.begin_nested():
                yield
                
            self.db.session.commit()
            self.logger.info(f"Completed {description}")
            
        except Exception as e:
            self.logger.error(f"Error in {description}: {str(e)}")
            self.stats.rollback_to_checkpoint(description)
            self.stats.errors.append(f"Error in {description}: {str(e)}")
            self.db.session.rollback()
            raise

    def _ensure_clean_session(self):
        """Ensure the session is in a clean state before starting migration."""
        try:
            self.db.session.rollback()
            self.db.session.expire_all()
            self.db.session.expunge_all()
        except Exception as e:
            self.logger.warning(f"Error cleaning session: {str(e)}")
            self.db.session.remove()
            self.db = db.create_scoped_session()

    def yield_course_batches(self, batch_size: int = None):
        """Yield batches of courses for efficient processing."""
        batch_size = batch_size or self.BATCH_SIZE
        offset = 0
        while True:
            batch = Course.query.order_by(Course.id).offset(offset).limit(batch_size).all()
            if not batch:
                break
            yield batch
            offset += batch_size

    def _process_subject_batch(self, subjects: Set[str]) -> None:
        """Process a batch of subjects efficiently."""
        for subject_name in subjects:
            try:
                normalized_name = self.subject_extractor.normalize_subject_name(subject_name)
                if not normalized_name:
                    continue
                    
                category = self.subject_extractor.get_subject_category(normalized_name)
                if not category:
                    self.logger.warning(f"No category found for subject: {normalized_name}")
                    continue
                    
                category_record = SubjectCategories.query.filter_by(name=category).first()
                if not category_record:
                    category_record = SubjectCategories(
                        name=category,
                        description=f"Auto-generated category for {category}"
                    )
                    self.db.session.add(category_record)
                    self.db.session.flush()
                
                existing_subject = Subjects.query.filter_by(name=normalized_name).first()
                if existing_subject:
                    if subject_name not in existing_subject.alternative_names:
                        existing_subject.alternative_names.append(subject_name)
                        self.stats.subjects_updated += 1
                else:
                    subject = Subjects(
                        name=normalized_name,
                        category_id=category_record.id,
                        is_core=normalized_name.lower() in {'english language', 'mathematics'},
                        alternative_names=[subject_name] if subject_name != normalized_name else []
                    )
                    self.db.session.add(subject)
                    self.stats.subjects_created += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing subject {subject_name}: {str(e)}")
                raise

    def _create_subjects(self) -> None:
        """Create subjects with improved batch processing and stats tracking."""
        with self.batch_operation("subject creation"):
            # Collect all subjects
            json_subjects = {
                subject
                for category in self.json_data.get('subject_classifications', {}).values()
                for subjects in category.values()
                if isinstance(subjects, list)
                for subject in subjects
            }
            
            self.logger.info(f"Found {len(json_subjects)} subjects in JSON data")
            
            # Collect subjects from courses
            db_subjects = set()
            for courses in self.yield_course_batches():
                for course in courses:
                    if course.utme_requirements:
                        try:
                            parsed = self.requirement_extractor.parse_requirements(
                                course.utme_requirements
                            )
                            db_subjects.update(parsed['mandatory_subjects'])
                            db_subjects.update(parsed['optional_subjects'])
                        except Exception as e:
                            self.logger.warning(
                                f"Error parsing requirements for course {course.id}: {str(e)}"
                            )
            
            self.logger.info(f"Found {len(db_subjects)} subjects in database")
            
            # Process subjects in batches
            all_subjects = json_subjects.union(db_subjects)
            for i in range(0, len(all_subjects), self.BATCH_SIZE):
                batch = set(list(all_subjects)[i:i + self.BATCH_SIZE])
                self._process_subject_batch(batch)
                if i % (self.BATCH_SIZE * 5) == 0:
                    self.db.session.flush()

    def _process_json_templates(self) -> None:
        """Process course templates from JSON data with enhanced logging."""
        self.logger.info(f"JSON data keys: {list(self.json_data.keys())}")
        programs = self.json_data.get('professional_programs', {})
        self.logger.info(f"Found {len(programs)} professional programs")
        self.logger.debug(f"Program names: {list(programs.keys())}")
        
        processed_templates = set()
        
        for program_name, program_data in programs.items():
            self.logger.debug(f"Processing program: {program_name}")
            
            if program_name in processed_templates:
                continue
                
            try:
                o_level_reqs = program_data.get('o_level_requirements', {})
                
                existing_template = CourseRequirementTemplates.query.filter_by(
                    name=program_name
                ).first()
                
                if existing_template:
                    self._update_existing_template(
                        existing_template, 
                        program_name, 
                        o_level_reqs
                    )
                    self.stats.templates_updated += 1
                else:
                    template = self._create_new_template(
                        program_name, 
                        o_level_reqs
                    )
                    self.db.session.add(template)
                    self.stats.templates_created += 1
                
                processed_templates.add(program_name)
                
            except Exception as e:
                self.logger.warning(
                    f"Error processing program template {program_name}: {str(e)}"
                )
                continue
        
        self.logger.info(
            f"Processed {len(processed_templates)} templates "
            f"(Created: {self.stats.templates_created}, "
            f"Updated: {self.stats.templates_updated})"
        )

    def _create_course_templates(self) -> None:
        """Create course templates with enhanced error handling and stats tracking."""
        with self.batch_operation("course template creation"):
            # Process JSON templates
            self._process_json_templates()
            
            # Process course templates
            processed_courses = set()
            template_batch = []
            
            for courses in self.yield_course_batches():
                for course in courses:
                    if course.course_name in processed_courses or not course.utme_requirements:
                        continue
                        
                    template = self._create_template_from_course(course)
                    if template:
                        template_batch.append(template)
                        self.stats.templates_created += 1
                        
                    processed_courses.add(course.course_name)
                    
                    if len(template_batch) >= self.BATCH_SIZE:
                        self.db.session.bulk_save_objects(template_batch)
                        template_batch = []
                        self.db.session.flush()
            
            if template_batch:
                self.db.session.bulk_save_objects(template_batch)
                self.db.session.flush()

    def _create_institution_requirements(self) -> None:
        """Create institution requirements with improved error handling."""
        with self.batch_operation("institution requirements creation"):
            processed = set()
            
            for course in Course.query.all():
                if not course.utme_requirements or not course.course_name:
                    continue

                inst_template_key = (course.university_name, course.course_name)
                if inst_template_key in processed:
                    continue
                    
                processed.add(inst_template_key)

                try:
                    self._process_single_institution_requirement(course)
                except Exception as e:
                    self.logger.warning(
                        f"Error processing requirement for {course.university_name} - "
                        f"{course.course_name}: {str(e)}"
                    )
                    continue

                if len(self.stats.errors) >= self.MAX_ERRORS:
                    raise Exception(f"Maximum error limit ({self.MAX_ERRORS}) reached")

    def _process_single_institution_requirement(self, course: Course) -> None:
        """Process a single institution requirement with proper error handling."""
        template = CourseRequirementTemplates.query.filter_by(
            name=course.course_name
        ).first()
        
        if not template:
            self.stats.errors.append(f"Template not found for course: {course.course_name}")
            return

        institution = University.query.filter_by(
            university_name=course.university_name
        ).first()

        if not institution:
            self.stats.errors.append(f"Institution not found: {course.university_name}")
            return

        requirements = self.requirement_extractor.parse_requirements(
            course.utme_requirements
        )

        existing_req = InstitutionRequirements.query.filter_by(
            institution_id=institution.id,
            template_id=template.id
        ).first()

        if existing_req:
            self._update_existing_requirement(existing_req, requirements, course)
            self.stats.requirements_updated += 1
        else:
            new_req = self._create_new_requirement(
                institution.id,
                template.id,
                requirements,
                course
            )
            self.db.session.add(new_req)
            self.stats.requirements_created += 1

    def migrate_all(self) -> Tuple[bool, List[str]]:
        """Execute complete migration process with enhanced error handling."""
        try:
            self._ensure_clean_session()
            
            schema_valid, validation_errors = self.validate_schema()
            if not schema_valid:
                return False, validation_errors

            migration_steps = [
                self._create_subjects,
                self._create_course_templates,
                self._create_institution_requirements
            ]
            
            for step in migration_steps:
                try:
                    step()
                except Exception as e:
                    logger.error(f"Migration step failed: {str(e)}")
                    return False, self.stats.errors
                    
            # Final validation - Changed from _validate_migration to validate_migration
            if not self.validate_migration():
                return False, self.stats.errors
                
            logger.info(f"Migration completed successfully. Stats: {self.stats}")
            return True, []
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return False, [str(e)]

    def _validate_schema(self):
        """Validate database schema before migration using SQLAlchemy inspector."""
        try:
            inspector = inspect(self.db.engine)
            required_tables = ['university', 'course_requirement_templates', 'institution_requirements']
            existing_tables = inspector.get_table_names()
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            if missing_tables:
                for table in missing_tables:
                    self.errors.append(f"Missing required table: {table}")
                return False

            # Validate required columns in institution_requirements
            if 'institution_requirements' in existing_tables:
                columns = {col['name'] for col in inspector.get_columns('institution_requirements')}
                required_columns = {
                    'id', 'institution_id', 'template_id', 'override_min_credits',
                    'override_max_sittings', 'additional_requirements', 'created_at', 'updated_at'
                }
                missing_columns = required_columns - columns
                if missing_columns:
                    self.errors.append(f"Missing columns in institution_requirements: {missing_columns}")
                    return False

            return True
            
        except Exception as e:
            self.errors.append(f"Schema validation error: {str(e)}")
            return False

    def _create_subject_categories(self):
        """Create subject categories from JSON data."""
        categories = self.json_data['subject_classifications']
        
        for main_category, subcategories in categories.items():
            # Create main category
            main_cat = SubjectCategories(
                name=main_category,
                description=f"Main category for {main_category}"
            )
            self.db.session.add(main_cat)
            self.db.session.flush()

            # Create subcategories
            for subcat_name, _ in subcategories.items():
                subcat = SubjectCategories(
                    name=subcat_name,
                    description=f"Subcategory of {main_category}",
                    parent_id=main_cat.id
                )
                self.db.session.add(subcat)

    def _create_course_templates(self):
        """Create course templates with efficient batch processing."""
        with self.batch_operation("course template creation"):
            initial_template_count = CourseRequirementTemplates.query.count()
            # Process JSON templates
            self._process_json_templates()
            
            # Process course templates in batches
            processed_courses = set()
            for courses in self.yield_course_batches():
                template_batch = []
                for course in courses:
                    if course.course_name in processed_courses or not course.utme_requirements:
                        continue
                        
                    processed_courses.add(course.course_name)
                    template = self._create_template_from_course(course)
                    if template:
                        template_batch.append(template)
                        
                if template_batch:
                    self.db.session.bulk_save_objects(template_batch)
                    self.stats.templates_created += len(template_batch)
                    self.db.session.flush()

        final_template_count = CourseRequirementTemplates.query.count()
        self.stats.templates_created = final_template_count - initial_template_count


    def _create_institution_requirements(self):
        """Create or update institution requirements with enhanced error handling."""
        try:
            initial_req_count = InstitutionRequirements.query.count()
            processed = set()
            
            for course in Course.query.all():
                # Skip invalid courses
                if not course.utme_requirements or not course.course_name:
                    continue

                # Create composite key for tracking
                inst_template_key = (course.university_name, course.course_name)
                if inst_template_key in processed:
                    continue
                    
                processed.add(inst_template_key)

                # Find template with error handling
                template = CourseRequirementTemplates.query.filter_by(
                    name=course.course_name
                ).first()
                
                if not template:
                    self.errors.append(f"Template not found for course: {course.course_name}")
                    continue

                # Find institution with error handling
                institution = University.query.filter_by(
                    university_name=course.university_name
                ).first()

                if not institution:
                    self.errors.append(f"Institution not found: {course.university_name}")
                    continue

                try:
                    # Parse requirements
                    requirements = self.requirement_extractor.parse_requirements(
                        course.utme_requirements
                    )

                    # Check for existing requirement
                    existing_req = InstitutionRequirements.query.filter_by(
                        institution_id=institution.id,
                        template_id=template.id
                    ).first()

                    if existing_req:
                        # Update existing requirement
                        existing_req.override_min_credits = requirements.get('min_credits', 5)
                        existing_req.override_max_sittings = requirements.get('max_sittings', 2)
                        existing_req.additional_requirements = course.utme_requirements
                        existing_req.updated_at = datetime.utcnow()
                    else:
                        # Create new requirement
                        new_req = InstitutionRequirements(
                            institution_id=institution.id,
                            template_id=template.id,
                            override_min_credits=requirements.get('min_credits', 5),
                            override_max_sittings=requirements.get('max_sittings', 2),
                            additional_requirements=course.utme_requirements,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        self.db.session.add(new_req)
                        self.stats.requirements_created += 1

                    # Commit periodically to avoid large transactions
                    if self.stats.requirements_created % 1000 == 0:
                        self.db.session.flush()

                except Exception as e:
                    logger.warning(
                        f"Error processing requirement for {course.university_name} - "
                        f"{course.course_name}: {str(e)}"
                    )
                    continue

            self.db.session.flush()
            
            final_req_count = InstitutionRequirements.query.count()
            self.stats.requirements_created = final_req_count - initial_req_count
            logger.info(f"Created/updated {self.stats.requirements_created} institution requirements")

        except SQLAlchemyError as e:
            logger.error(f"Database error in institution requirements: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in institution requirements: {str(e)}")
            raise

    def validate_migration(self):
        """Validate the migrated data with proper transaction handling."""
        try:
            with self.db.session.begin_nested():
                # Basic count validations
                subject_count = Subjects.query.count()
                template_count = CourseRequirementTemplates.query.count()
                inst_req_count = InstitutionRequirements.query.count()

                logger.info(f"Total subjects created: {subject_count}")
                logger.info(f"Total course templates created: {template_count}")
                logger.info(f"Total institution requirements created: {inst_req_count}")

                if subject_count == 0 or template_count == 0:
                    self.errors.append("No subjects or templates created")
                    return False

                # Validate no orphaned records
                orphaned_requirements = self.db.session.query(InstitutionRequirements).filter(
                    ~InstitutionRequirements.institution_id.in_(
                        self.db.session.query(University.id)
                    )
                ).count()

                if orphaned_requirements > 0:
                    self.errors.append(f"Found {orphaned_requirements} orphaned institution requirements")
                    return False

                # Validate relationships
                invalid_templates = self.db.session.query(InstitutionRequirements).filter(
                    ~InstitutionRequirements.template_id.in_(
                        self.db.session.query(CourseRequirementTemplates.id)
                    )
                ).count()

                if invalid_templates > 0:
                    self.errors.append(f"Found {invalid_templates} invalid template references")
                    return False

                return True

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            self.errors.append(str(e))
            return False
        
    def _process_json_templates(self):
        logger.info(f"JSON data keys: {list(self.json_data.keys())}")
        programs = self.json_data.get('professional_programs', {})
        logger.info(f"Found {len(programs)} professional programs")
        logger.debug(f"Program names: {list(programs.keys())}")
        """Process course templates from JSON data with upsert handling."""
        try:
            # Track processed templates to avoid duplicates
            processed_templates = set()
            templates_before = self.stats.templates_created
            
            # Process professional programs
            logger.info("Processing professional program templates...")
            for program_name, program_data in self.json_data.get('professional_programs', {}).items():
                logger.debug(f"Processing program: {program_name}")
                
                if program_name in processed_templates:
                    continue
                    
                try:
                    # Check if template already exists
                    existing_template = CourseRequirementTemplates.query.filter_by(
                        name=program_name
                    ).first()
                    
                    o_level_reqs = program_data.get('o_level_requirements', {})
                    
                    if existing_template:
                        # Update existing template
                        existing_template.description = f"Professional program: {program_name}"
                        existing_template.min_credits = o_level_reqs.get('minimum_credits', 5)
                        existing_template.max_sittings = 2 if 'sitting_requirement' not in o_level_reqs else \
                            int(re.search(r'\d+', str(o_level_reqs['sitting_requirement'])).group())
                        existing_template.updated_at = datetime.utcnow()
                    else:
                        # Create new template
                        template = CourseRequirementTemplates(
                            name=program_name,
                            description=f"Professional program: {program_name}",
                            min_credits=o_level_reqs.get('minimum_credits', 5),
                            max_sittings=2 if 'sitting_requirement' not in o_level_reqs else \
                                int(re.search(r'\d+', str(o_level_reqs['sitting_requirement'])).group()),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        self.db.session.add(template)
                        self.stats.templates_created += 1
                    
                    processed_templates.add(program_name)
                    
                except Exception as e:
                    logger.warning(f"Error processing program template {program_name}: {str(e)}")
                    continue
            
            # Commit first batch
            self.db.session.flush()
            logger.info(f"Processed {self.stats.templates_created} professional program templates")
            
            return True
        
            templates_created = self.stats.templates_created - templates_before
            logger.info(f"Created {templates_created} new templates and updated {len(processed_templates) - templates_created} existing templates")
            
        except Exception as e:
            logger.error(f"Error in _process_json_templates: {str(e)}")
            raise
        
    def _create_template_from_course(self, course: Course) -> Optional[CourseRequirementTemplates]:
        """Create a course template from an existing course."""
        try:
            # Parse requirements
            requirements = self.requirement_extractor.parse_requirements(
                course.utme_requirements
            )

            # Check if template already exists
            existing_template = CourseRequirementTemplates.query.filter_by(
                name=course.course_name
            ).first()
            
            if existing_template:
                # Update existing template
                existing_template.min_credits = requirements.get('min_credits', 5)
                existing_template.max_sittings = requirements.get('max_sittings', 2)
                existing_template.updated_at = datetime.utcnow()
                return None  # Don't add to batch since we're updating
            
            # Create new template
            template = CourseRequirementTemplates(
                name=course.course_name,
                description=f"Template for {course.course_name}",
                min_credits=requirements.get('min_credits', 5),
                max_sittings=requirements.get('max_sittings', 2),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return template
            
        except Exception as e:
            logger.warning(
                f"Error creating template for course {course.course_name}: {str(e)}"
            )
            return None
        
    def validate_schema(self) -> Tuple[bool, List[str]]:
        """Validate database schema with detailed checks."""
        try:
            self.logger.info("Starting schema validation...")
            inspector = inspect(self.db.engine)
            validation_errors = []
            
            # Required table definitions with their columns
            required_tables = {
                'university': ['id', 'university_name'],
                'course_requirement_templates': ['id', 'name', 'min_credits'],
                'institution_requirements': [
                    'id', 'institution_id', 'template_id', 
                    'override_min_credits', 'override_max_sittings',
                    'additional_requirements', 'created_at', 'updated_at'
                ]
            }
            
            # Validate tables and columns
            for table, required_cols in required_tables.items():
                if table not in inspector.get_table_names():
                    validation_errors.append(f"Missing required table: {table}")
                    continue
                    
                existing_cols = {col['name'] for col in inspector.get_columns(table)}
                missing_cols = set(required_cols) - existing_cols
                if missing_cols:
                    validation_errors.append(
                        f"Missing columns in {table}: {missing_cols}"
                    )
            
            is_valid = len(validation_errors) == 0
            if is_valid:
                self.logger.info("Schema validation successful")
            else:
                self.logger.error(
                    f"Schema validation failed with {len(validation_errors)} errors"
                )
                
            return is_valid, validation_errors
            
        except Exception as e:
            self.logger.error(f"Schema validation error: {str(e)}")
            return False, [str(e)]