# app/cli.py
import click
from flask.cli import with_appcontext
from .utils.search import init_search_vectors
from .extensions import db
from sqlalchemy import text
import logging
import json
import os
import re
from .utils.extract_normalize import (
    SubjectExtractor, 
    RequirementExtractor,
    populate_subjects_and_categories,
    create_course_templates
)
from .utils.data_migration_manager import DataMigrationManager
from .models.requirement import (
    UTMERequirementTemplate,
    DirectEntryRequirementTemplate,
    CourseRequirement,  
    CourseRequirementTemplate
)
from .models.subject import (
    SubjectCategories,
    Subjects,
)


def wait_for_db_cli(retries=5, interval=5):
    """Ensure database is available before running CLI commands"""
    for attempt in range(retries):
        try:
            db.session.execute(text("SELECT 1")).scalar()
            return True
        except Exception as e:
            if attempt == retries - 1:
                click.echo(f"Failed to connect to database after {retries} attempts: {e}")
                return False
            click.echo(f"Database connection attempt {attempt + 1} failed. Retrying in {interval} seconds...")
            import time
            time.sleep(interval)

def init_app(app):
    @app.cli.command('db-info')
    @with_appcontext
    def db_info():
        """Show current database information"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
        
        try:
            # Get current database name
            db_name = db.session.execute(text("SELECT current_database()")).scalar()
            
            # Get database size
            size = db.session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)).scalar()
            
            # Get database version
            version = db.session.execute(text("SHOW server_version")).scalar()
            
            # Get connection info
            conn_info = db.session.execute(text("""
                SELECT 
                    current_user,
                    inet_server_addr(),
                    inet_server_port()
            """)).fetchone()
            
            # Get table counts with error handling
            try:
                uni_count = db.session.execute(text("SELECT COUNT(*) FROM university")).scalar()
                course_count = db.session.execute(text("SELECT COUNT(*) FROM course")).scalar()
            except Exception as e:
                uni_count = "Error counting"
                course_count = "Error counting"
                logging.error(f"Error counting records: {str(e)}")
            
            click.echo("\nDatabase Information:")
            click.echo(f"Name: {db_name}")
            click.echo(f"Size: {size}")
            click.echo(f"Version: {version}")
            click.echo(f"User: {conn_info[0]}")
            click.echo(f"Host: {conn_info[1]}")
            click.echo(f"Port: {conn_info[2]}")
            
            click.echo(f"\nTable Statistics:")
            click.echo(f"Universities: {uni_count}")
            click.echo(f"Courses: {course_count}")
            
        except Exception as e:
            click.echo(f"Error getting database info: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-search-init')
    @with_appcontext
    def init_search():
        """Initialize search vectors for existing records"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            click.echo('Initializing search vectors...')
            init_search_vectors()
            click.echo('Search vectors initialized.')
        except Exception as e:
            click.echo(f"Error initializing search vectors: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-search-reset')
    @with_appcontext
    def reset_search_vectors():
        """Reset search vectors to null"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            click.echo('Resetting search vectors...')
            with db.session.begin():
                db.session.execute(text('UPDATE university SET search_vector = NULL'))
                db.session.execute(text('UPDATE course SET search_vector = NULL'))
            click.echo('Search vectors reset. Run db-search-init to reinitialize them.')
        except Exception as e:
            click.echo(f"Error resetting search vectors: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
    
    @app.cli.command('db-search-verify')
    @with_appcontext
    def verify_search_setup():
        """Verify search setup and indexes"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            click.echo("\nChecking database setup...")
            
            # Check if search_vector columns exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'course' 
                AND column_name = 'search_vector'
            """)).fetchone()
            click.echo(f"Course search_vector column exists: {result is not None}")
            
            # Check if vectors are populated
            course_count = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM course 
                WHERE search_vector IS NOT NULL
            """)).scalar()
            click.echo(f"Courses with search vectors: {course_count}")
            
            # Test a simple search
            click.echo("\nTesting course search...")
            courses = db.session.execute(text("""
                SELECT c.course_name, u.university_name
                FROM course c
                JOIN course_requirement cr ON c.id = cr.course_id
                JOIN university u ON cr.university_id = u.id
                WHERE c.search_vector @@ to_tsquery('english', 'computer')
                LIMIT 5
            """)).fetchall()
            
            click.echo(f"Found {len(courses)} courses matching 'computer'")
            for course in courses:
                click.echo(f"- {course.course_name} at {course.university_name}")
                
        except Exception as e:
            click.echo(f"Error during verification: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-indexes')
    @with_appcontext
    def check_database_indexes():
        """Show all database indexes and their sizes"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            click.echo("\nDatabase Indexes:")
            indexes = db.session.execute(text("""
                SELECT
                    schemaname || '.' || tablename as table,
                    indexname as index,
                    pg_size_pretty(pg_relation_size(schemaname|| '.' || indexname::text)) as size,
                    indexdef as definition
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY pg_relation_size(schemaname|| '.' || indexname::text) DESC;
            """)).fetchall()
            
            for idx in indexes:
                click.echo(f"\nTable: {idx[0]}")
                click.echo(f"Index: {idx[1]}")
                click.echo(f"Size: {idx[2]}")
                click.echo(f"Definition: {idx[3]}")
                
        except Exception as e:
            click.echo(f"Error checking indexes: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-search-analyze')
    @with_appcontext
    def analyze_search_performance():
        """Analyze search vector performance"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            click.echo("\nAnalyzing search vector performance...")
            
            # Check index usage
            stats = db.session.execute(text("""
                SELECT 
                    schemaname || '.' || relname as table,
                    indexrelname as index,
                    idx_scan as number_of_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE indexrelname LIKE '%search%'
                ORDER BY idx_scan DESC;
            """)).fetchall()
            
            click.echo("\nSearch Index Usage Statistics:")
            for stat in stats:
                click.echo(f"\nTable: {stat[0]}")
                click.echo(f"Index: {stat[1]}")
                click.echo(f"Number of scans: {stat[2]}")
                click.echo(f"Tuples read: {stat[3]}")
                click.echo(f"Tuples fetched: {stat[4]}")
            
            # Check null vectors
            null_unis = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM university 
                WHERE search_vector IS NULL
            """)).scalar()
            
            null_courses = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM course 
                WHERE search_vector IS NULL
            """)).scalar()
            
            click.echo(f"\nNull Vector Statistics:")
            click.echo(f"Universities with null vectors: {null_unis}")
            click.echo(f"Courses with null vectors: {null_courses}")
            
        except Exception as e:
            click.echo(f"Error analyzing search performance: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-verify-data')
    @with_appcontext
    def verify_data():
        """Verify data consistency between tables and transfer log"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
        
        try:
            click.echo("\nVerifying data consistency...")
            
            # Get actual table counts and max IDs for all tables
            table_stats = db.session.execute(text("""
                SELECT 
                    'universities' as table_name,
                    COUNT(*) as record_count,
                    MAX(id) as max_id
                    FROM university
                UNION ALL
                SELECT 
                    'courses' as table_name,
                    COUNT(*) as record_count,
                    MAX(id) as max_id
                    FROM course
                UNION ALL
                SELECT 
                    'subjects' as table_name,
                    COUNT(*) as record_count,
                    MAX(id) as max_id
                    FROM subjects
                UNION ALL
                SELECT 
                    'subject_categories' as table_name,
                    COUNT(*) as record_count,
                    MAX(id) as max_id
                    FROM subject_categories
                UNION ALL
                SELECT 
                    'course_requirement_templates' as table_name,
                    COUNT(*) as record_count,
                    MAX(id) as max_id
                    FROM course_requirement_template
            """)).fetchall()
            
            # Original orphaned courses check
            orphaned_courses = db.session.execute(text("""
                SELECT c.id, c.course_name
                FROM course c
                LEFT JOIN course_requirement cr ON c.id = cr.course_id
                WHERE cr.id IS NULL
            """)).fetchall()
            
            # Original duplicate courses check
            duplicate_courses = db.session.execute(text("""
                SELECT c.course_name, u.university_name, COUNT(*)
                FROM course c
                JOIN course_requirement cr ON c.id = cr.course_id
                JOIN university u ON cr.university_id = u.id
                GROUP BY c.course_name, u.university_name
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            # New: Check orphaned subjects (subjects without categories)
            orphaned_subjects = db.session.execute(text("""
                SELECT s.id, s.name
                FROM subjects s
                LEFT JOIN subject_categories sc ON s.category_id = sc.id
                WHERE sc.id IS NULL
            """)).fetchall()
            
            # New: Check unused categories (categories with no subjects)
            unused_categories = db.session.execute(text("""
                SELECT sc.id, sc.name
                FROM subject_categories sc
                LEFT JOIN subjects s ON sc.id = s.category_id
                WHERE s.id IS NULL
            """)).fetchall()
            
            # New: Check orphaned course requirement templates
            orphaned_templates = db.session.execute(text("""
                SELECT crt.id, crt.name
                FROM course_requirement_template crt
                LEFT JOIN course_requirement cr ON crt.id = cr.course_id
                WHERE cr.id IS NULL
            """)).fetchall()
            
            # Output all verification results
            click.echo("\nCurrent Table Status:")
            for stat in table_stats:
                click.echo(f"{stat.table_name}:")
                click.echo(f"  Record Count: {stat.record_count}")
                click.echo(f"  Max ID: {stat.max_id}")
            
            if orphaned_courses:
                click.echo("\nOrphaned Courses (no requirements):")
                for course in orphaned_courses:
                    click.echo(f"ID: {course.id}, Course: {course.course_name}")
            
            if duplicate_courses:
                click.echo("\nDuplicate Courses:")
                for dup in duplicate_courses:
                    click.echo(f"Course: {dup[0]}, University: {dup[1]}, Count: {dup[2]}")
            
            if orphaned_subjects:
                click.echo("\nOrphaned Subjects (no category):")
                for subject in orphaned_subjects:
                    click.echo(f"ID: {subject.id}, Subject: {subject.name}")
            
            if unused_categories:
                click.echo("\nUnused Categories (no subjects):")
                for category in unused_categories:
                    click.echo(f"ID: {category.id}, Category: {category.name}")
            
            if orphaned_templates:
                click.echo("\nOrphaned Course Requirement Templates:")
                for template in orphaned_templates:
                    click.echo(f"ID: {template.id}, Template: {template.name}")
            
            # New: Summary of verification
            click.echo("\nVerification Summary:")
            click.echo(f"Total Orphaned Courses: {len(orphaned_courses)}")
            click.echo(f"Total Duplicate Courses: {len(duplicate_courses)}")
            click.echo(f"Total Orphaned Subjects: {len(orphaned_subjects)}")
            click.echo(f"Total Unused Categories: {len(unused_categories)}")
            click.echo(f"Total Orphaned Templates: {len(orphaned_templates)}")
            
        except Exception as e:
            click.echo(f"Error verifying data: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()


            
    @app.cli.command('db-analyze-gaps')
    @with_appcontext
    def analyze_gaps():
        """Perform detailed analysis of gaps in course IDs"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
        
        try:
            click.echo("\nAnalyzing gaps in course IDs...")
            
            # Get sequence info
            sequence_info = db.session.execute(text("""
                SELECT 
                    MIN(id) as min_id,
                    MAX(id) as max_id,
                    COUNT(*) as total_records,
                    MAX(id) - MIN(id) + 1 as id_range,
                    MAX(id) - MIN(id) + 1 - COUNT(*) as total_gaps
                FROM course
            """)).fetchone()
            
            click.echo("\nSequence Statistics:")
            click.echo(f"ID Range: {sequence_info[0]} to {sequence_info[1]}")
            click.echo(f"Total Records: {sequence_info[2]}")
            click.echo(f"ID Range Size: {sequence_info[3]}")
            click.echo(f"Total Gaps: {sequence_info[4]}")
            
            # Analyze gap patterns
            click.echo("\nAnalyzing gap patterns...")
            gaps = db.session.execute(text("""
                WITH RECURSIVE numbers AS (
                    SELECT MIN(id) as num FROM course
                    UNION ALL
                    SELECT num + 1
                    FROM numbers
                    WHERE num < (SELECT MAX(id) FROM course)
                ),
                gaps AS (
                    SELECT num
                    FROM numbers n
                    WHERE NOT EXISTS (
                        SELECT 1 FROM course c WHERE c.id = n.num
                    )
                )
                SELECT 
                    num as gap_id,
                    num - LAG(num, 1) OVER (ORDER BY num) as gap_distance
                FROM gaps
                ORDER BY num
            """)).fetchall()
            
            # Analyze gap patterns
            distances = [gap[1] for gap in gaps if gap[1] is not None]
            if distances:
                common_distance = max(set(distances), key=distances.count)
                pattern_count = distances.count(common_distance)
                
                click.echo(f"\nGap Pattern Analysis:")
                click.echo(f"Most common gap distance: {common_distance}")
                click.echo(f"Number of gaps with this pattern: {pattern_count}")
                click.echo(f"Pattern consistency: {(pattern_count/len(distances))*100:.1f}%")
            
            # Get records around gaps
            if gaps:
                first_gap = gaps[0][0]
                click.echo(f"\nRecords around first gap (ID: {first_gap}):")
                surrounding = db.session.execute(text("""
                    SELECT id, course_name, university_name
                    FROM course
                    WHERE id BETWEEN :start AND :end
                    ORDER BY id
                """), {'start': first_gap-2, 'end': first_gap+2}).fetchall()
                
                for record in surrounding:
                    click.echo(f"ID: {record[0]}, Course: {record[1]}, University: {record[2]}")
            
        except Exception as e:
            click.echo(f"Error analyzing gaps: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-analyze-cleanup')
    @with_appcontext
    def analyze_cleanup():
        """Analyze potential cleanup patterns in course data"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
        
        try:
            click.echo("\nAnalyzing course data patterns...")
            
            # Analyze distribution around gap region
            click.echo("\nDistribution around major gap region (12000-13000):")
            distribution = db.session.execute(text("""
                WITH ranges AS (
                    SELECT 
                        CASE 
                            WHEN id < 12000 THEN 'before_gap'
                            WHEN id BETWEEN 12000 AND 13000 THEN 'during_gap'
                            ELSE 'after_gap'
                        END as range_type,
                        COUNT(*) as count,
                        COUNT(DISTINCT university_name) as uni_count,
                        COUNT(DISTINCT course_name) as course_count
                    FROM course
                    GROUP BY 
                        CASE 
                            WHEN id < 12000 THEN 'before_gap'
                            WHEN id BETWEEN 12000 AND 13000 THEN 'during_gap'
                            ELSE 'after_gap'
                        END
                )
                SELECT * FROM ranges ORDER BY 
                    CASE range_type 
                        WHEN 'before_gap' THEN 1 
                        WHEN 'during_gap' THEN 2 
                        ELSE 3 
                    END
            """)).fetchall()
            
            for dist in distribution:
                click.echo(f"\n{dist[0]}:")
                click.echo(f"  Records: {dist[1]}")
                click.echo(f"  Unique Universities: {dist[2]}")
                click.echo(f"  Unique Courses: {dist[3]}")
            
            # Check for course name patterns in gap region
            click.echo("\nMost common courses around gaps:")
            common_courses = db.session.execute(text("""
                SELECT 
                    course_name,
                    COUNT(*) as frequency,
                    COUNT(DISTINCT university_name) as uni_count
                FROM course
                WHERE id BETWEEN 12000 AND 13000
                GROUP BY course_name
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)).fetchall()
            
            for course in common_courses:
                click.echo(f"\nCourse: {course[0]}")
                click.echo(f"Frequency: {course[1]}")
                click.echo(f"Universities: {course[2]}")
            
            # Check for university patterns
            click.echo("\nUniversity distribution in gap region:")
            uni_distribution = db.session.execute(text("""
                SELECT 
                    university_name,
                    COUNT(*) as course_count,
                    MIN(id) as min_id,
                    MAX(id) as max_id
                FROM course
                WHERE id BETWEEN 12000 AND 13000
                GROUP BY university_name
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)).fetchall()
            
            for uni in uni_distribution:
                click.echo(f"\nUniversity: {uni[0]}")
                click.echo(f"Courses: {uni[1]}")
                click.echo(f"ID Range: {uni[2]} - {uni[3]}")
            
        except Exception as e:
            click.echo(f"Error analyzing cleanup patterns: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-gap-report')
    @with_appcontext
    def analyze_gap_report():
        """Generate comprehensive gap analysis report"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
        
        try:
            click.echo("\nGenerating Gap Analysis Report...")
            
            # Basic sequence analysis
            sequence_info = db.session.execute(text("""
                SELECT 
                    MIN(id) as min_id,
                    MAX(id) as max_id,
                    COUNT(*) as total_records,
                    MAX(id) - MIN(id) + 1 - COUNT(*) as total_gaps
                FROM course
            """)).fetchone()
            
            # Get detailed gap analysis
            gaps = db.session.execute(text("""
                WITH RECURSIVE numbers AS (
                    SELECT MIN(id) as num FROM course
                    UNION ALL
                    SELECT num + 1
                    FROM numbers
                    WHERE num < (SELECT MAX(id) FROM course)
                ),
                gap_analysis AS (
                    SELECT 
                        num as gap_id,
                        num - LAG(num, 1) OVER (ORDER BY num) as gap_distance,
                        LEAD(num, 1) OVER (ORDER BY num) - num as next_gap_distance
                    FROM (
                        SELECT num
                        FROM numbers n
                        WHERE NOT EXISTS (
                            SELECT 1 FROM course c WHERE c.id = n.num
                        )
                    ) gaps
                )
                SELECT 
                    gap_id,
                    gap_distance,
                    next_gap_distance,
                    COUNT(*) OVER (PARTITION BY gap_distance) as pattern_frequency
                FROM gap_analysis
                ORDER BY gap_id
            """)).fetchall()
            
            # Analysis around gaps
            context_query = text("""
                SELECT c.id, c.course_name, c.university_name, u.university_type
                FROM course c
                LEFT JOIN university u ON c.university_name = u.university_name
                WHERE c.id BETWEEN :start AND :end
                ORDER BY c.id
            """)
            
            # Print report
            click.echo("\n=== Gap Analysis Report ===")
            click.echo(f"\n1. Sequence Statistics:")
            click.echo(f"- ID Range: {sequence_info[0]} to {sequence_info[1]}")
            click.echo(f"- Total Records: {sequence_info[2]}")
            click.echo(f"- Total Gaps: {sequence_info[3]}")
            
            # Pattern analysis
            if gaps:
                distances = [g[1] for g in gaps if g[1] is not None]
                common_distance = max(set(distances), key=distances.count)
                pattern_count = distances.count(common_distance)
                
                click.echo(f"\n2. Gap Pattern Analysis:")
                click.echo(f"- Most common gap distance: {common_distance}")
                click.echo(f"- Gaps following this pattern: {pattern_count}")
                click.echo(f"- Pattern consistency: {(pattern_count/len(distances))*100:.1f}%")
                
                # Analyze first gap context
                first_gap = gaps[0][0]
                context = db.session.execute(context_query, 
                                        {'start': first_gap-2, 'end': first_gap+2}).fetchall()
                
                click.echo(f"\n3. Context Around First Gap (ID: {first_gap}):")
                for record in context:
                    click.echo(f"ID: {record[0]}, Course: {record[1]}")
                    click.echo(f"University: {record[2]} ({record[3] or 'Unknown type'})")
                    
        except Exception as e:
            click.echo(f"Error generating gap report: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-analyze-education')
    @with_appcontext
    def analyze_education_patterns():
        """Analyze patterns specific to colleges of education"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
        
        try:
            click.echo("\nAnalyzing College of Education Patterns...")
            
            # Analyze distribution of education colleges
            education_dist = db.session.execute(text("""
                WITH ranges AS (
                    SELECT 
                        CASE 
                            WHEN id < 12000 THEN 'pre_gap'
                            WHEN id BETWEEN 12000 AND 13000 THEN 'gap_region'
                            ELSE 'post_gap'
                        END as region,
                        university_name,
                        course_name
                    FROM course
                    WHERE university_name LIKE '%COLLEGE OF EDUCATION%'
                )
                SELECT 
                    region,
                    COUNT(DISTINCT university_name) as unique_institutions,
                    COUNT(*) as total_courses,
                    COUNT(DISTINCT course_name) as unique_courses
                FROM ranges
                GROUP BY region
                ORDER BY 
                    CASE region 
                        WHEN 'pre_gap' THEN 1 
                        WHEN 'gap_region' THEN 2 
                        ELSE 3 
                    END
            """)).fetchall()
            
            # Analyze course patterns in education colleges
            education_courses = db.session.execute(text("""
                WITH education_colleges AS (
                    SELECT id, university_name, course_name
                    FROM course
                    WHERE university_name LIKE '%COLLEGE OF EDUCATION%'
                    AND id BETWEEN 12000 AND 13000
                )
                SELECT 
                    course_name,
                    COUNT(*) as frequency,
                    COUNT(DISTINCT university_name) as institution_count,
                    MIN(id) as min_id,
                    MAX(id) as max_id
                FROM education_colleges
                GROUP BY course_name
                HAVING COUNT(*) > 5
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)).fetchall()
            
            # Analyze institutional overlap
            institution_overlap = db.session.execute(text("""
                WITH edu_courses AS (
                    SELECT DISTINCT university_name, course_name
                    FROM course
                    WHERE university_name LIKE '%COLLEGE OF EDUCATION%'
                    AND id BETWEEN 12000 AND 13000
                )
                SELECT 
                    c1.course_name,
                    COUNT(DISTINCT c1.university_name) as institution_count,
                    STRING_AGG(DISTINCT c1.university_name, '; ' ORDER BY c1.university_name) 
                        as institutions
                FROM edu_courses c1
                JOIN edu_courses c2 
                    ON c1.course_name = c2.course_name 
                    AND c1.university_name != c2.university_name
                GROUP BY c1.course_name
                HAVING COUNT(DISTINCT c1.university_name) > 3
                ORDER BY COUNT(DISTINCT c1.university_name) DESC
                LIMIT 5
            """)).fetchall()
            
            # Print detailed report
            click.echo("\n=== College of Education Analysis Report ===")
            
            click.echo("\n1. Distribution by Region:")
            for dist in education_dist:
                click.echo(f"\n{dist[0]}:")
                click.echo(f"  Institutions: {dist[1]}")
                click.echo(f"  Total Courses: {dist[2]}")
                click.echo(f"  Unique Courses: {dist[3]}")
            
            click.echo("\n2. Most Common Courses in Gap Region:")
            for course in education_courses:
                click.echo(f"\nCourse: {course[0]}")
                click.echo(f"  Frequency: {course[1]}")
                click.echo(f"  Institutions: {course[2]}")
                click.echo(f"  ID Range: {course[3]} - {course[4]}")
            
            click.echo("\n3. Course Overlap Analysis:")
            for overlap in institution_overlap:
                click.echo(f"\nCourse: {overlap[0]}")
                click.echo(f"Shared by {overlap[1]} institutions")
                
        except Exception as e:
            click.echo(f"Error analyzing education patterns: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-migrate-requirements')
    @with_appcontext
    def migrate_requirements():
        """Migrate course requirements to template table"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return

        try:
            click.echo('Starting course requirements migration...')
            
            # First, get subjects for reference
            subjects = {s.name: s.id for s in Subjects.query.all()}
            if not subjects:
                click.echo("No subjects found in database. Please run db-migrate-subjects first.")
                return
            
            click.echo(f'Found {len(subjects)} subjects for reference')
            
            # Get unique courses with their UTMERequirementTemplate
            click.echo('\nAnalyzing existing requirements...')
            patterns = db.session.execute(text("""
                SELECT 
                    c.course_name,
                    ut.requirements as requirement_text,
                    COUNT(*) as usage_count
                FROM course c
                JOIN course_requirement cr ON c.id = cr.course_id
                JOIN utme_requirement_template ut ON cr.utme_template_id = ut.id
                WHERE ut.requirements IS NOT NULL
                GROUP BY c.course_name, ut.requirements
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            
            click.echo(f'Found {len(patterns)} unique requirement patterns')
            
            # Create templates
            templates_created = 0
            requirement_pattern_map = {}  # To store pattern to template_id mapping
            
            for pattern in patterns:
                try:
                    course_name = pattern[0]
                    req_text = pattern[1]
                    usage_count = pattern[2]
                    
                    # Extract requirements
                    min_credits = 5  # Default
                    max_sittings = 2  # Default
                    
                    # Extract values if present
                    credits_match = re.search(r'(\d+)\s*credits?', req_text, re.IGNORECASE)
                    if credits_match:
                        min_credits = int(credits_match.group(1))
                    
                    sittings_match = re.search(r'(\d+)\s*sittings?', req_text, re.IGNORECASE)
                    if sittings_match:
                        max_sittings = int(sittings_match.group(1))
                    
                    # Create template
                    template = CourseRequirementTemplate(
                        name=f"{course_name}_Requirements",
                        min_credits=min_credits,
                        max_sittings=max_sittings
                    )
                    
                    db.session.add(template)
                    db.session.flush()  # Get template ID
                    
                    templates_created += 1
                    requirement_pattern_map[req_text] = template.id
                    
                    if templates_created % 50 == 0:
                        db.session.commit()
                        click.echo(f'Created {templates_created} templates...')
                    
                except Exception as e:
                    click.echo(f'Error creating template for {course_name}: {str(e)}')
                    continue
            
            try:
                db.session.commit()
                click.echo(f'Successfully created {templates_created} requirement templates')
            except Exception as e:
                db.session.rollback()
                click.echo(f'Error committing templates: {str(e)}')
                return
            
            # Update course requirements with new template IDs
            click.echo('\nUpdating course requirements...')
            updates_made = 0
            
            # Process in batches
            batch_size = 100
            offset = 0
            
            while True:
                requirements = db.session.execute(text("""
                    SELECT 
                        cr.id,
                        ut.requirements
                    FROM course_requirement cr
                    JOIN utme_requirement_template ut ON cr.utme_template_id = ut.id
                    LIMIT :limit OFFSET :offset
                """), {"limit": batch_size, "offset": offset}).fetchall()
                
                if not requirements:
                    break
                
                for req in requirements:
                    try:
                        req_id = req[0]
                        req_text = req[1]
                        template_id = requirement_pattern_map.get(req_text)
                        
                        if template_id:
                            # Update course_requirement to use new template
                            db.session.execute(text("""
                                UPDATE course_requirement
                                SET template_id = :template_id
                                WHERE id = :req_id
                            """), {
                                "template_id": template_id,
                                "req_id": req_id
                            })
                            updates_made += 1
                    except Exception as e:
                        click.echo(f'Error updating requirement {req_id}: {str(e)}')
                        continue
                
                try:
                    db.session.commit()
                    click.echo(f'Updated {updates_made} requirements...')
                except Exception as e:
                    db.session.rollback()
                    click.echo(f'Error in batch commit: {str(e)}')
                    continue
                
                offset += batch_size
            
            click.echo('\nMigration completed successfully')
            click.echo(f'Total templates created: {templates_created}')
            click.echo(f'Total requirements updated: {updates_made}')
            
            # Verify results
            verification = db.session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM course_requirement_template) as template_count,
                    (SELECT COUNT(*) FROM course_requirement WHERE template_id IS NOT NULL) as requirement_count,
                    (SELECT COUNT(DISTINCT course_id) FROM course_requirement WHERE template_id IS NOT NULL) as unique_courses
            """)).first()
            
            click.echo('\nVerification Results:')
            click.echo(f'Templates in database: {verification[0]}')
            click.echo(f'Requirements with templates: {verification[1]}')
            click.echo(f'Unique courses with templates: {verification[2]}')

        except Exception as e:
            click.echo(f"Error during migration: {str(e)}")
            db.session.rollback()
        finally:
            db.session.close()

    @app.cli.command('db-requirements-stats')
    @with_appcontext
    def requirements_stats():
        """Show statistics about course requirements"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return

        try:
            click.echo("\nRequirements Statistics:")
            
            # Get basic counts
            template_count = db.session.query(
                CourseRequirementTemplates
            ).count()
            
            subject_count = db.session.query(
                Subjects
            ).count()
            
            inst_req_count = db.session.query(
                InstitutionRequirements
            ).count()

            click.echo(f"\nTotal course templates: {template_count}")
            click.echo(f"Total subjects: {subject_count}")
            click.echo(f"Total institution-specific requirements: {inst_req_count}")

            # Get subject statistics
            subject_stats = db.session.execute(text("""
                SELECT 
                    category_id,
                    COUNT(*) as subject_count,
                    SUM(CASE WHEN is_core THEN 1 ELSE 0 END) as core_subjects
                FROM subjects
                GROUP BY category_id
            """)).fetchall()

            click.echo("\nSubject Distribution:")
            for stat in subject_stats:
                category = SubjectCategories.query.get(stat[0])
                click.echo(f"{category.name}:")
                click.echo(f"  Total subjects: {stat[1]}")
                click.echo(f"  Core subjects: {stat[2]}")

            # Get template statistics
            template_stats = db.session.execute(text("""
                SELECT 
                    min_credits,
                    COUNT(*) as template_count
                FROM course_requirement_templates
                GROUP BY min_credits
                ORDER BY min_credits
            """)).fetchall()

            click.echo("\nTemplate Credit Requirements:")
            for stat in template_stats:
                click.echo(f"{stat[0]} credits: {stat[1]} templates")

        except Exception as e:
            click.echo(f"Error getting statistics: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-requirements-verify')
    @with_appcontext
    def verify_requirements():
        """Verify integrity of course requirements"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return

        try:
            click.echo("\nVerifying requirements integrity...")

            # Check for orphaned records
            orphaned = db.session.execute(text("""
                SELECT 'template_requirements' as type, COUNT(*) 
                FROM template_subject_requirements tsr
                WHERE NOT EXISTS (
                    SELECT 1 FROM course_requirement_templates crt 
                    WHERE crt.id = tsr.template_id
                )
                UNION ALL
                SELECT 'institution_requirements' as type, COUNT(*)
                FROM institution_requirements ir
                WHERE NOT EXISTS (
                    SELECT 1 FROM university u WHERE u.id = ir.institution_id
                )
                UNION ALL
                SELECT 'subject_requirements' as type, COUNT(*)
                FROM institution_subject_requirements isr
                WHERE NOT EXISTS (
                    SELECT 1 FROM institution_requirements ir 
                    WHERE ir.id = isr.institution_requirement_id
                )
            """)).fetchall()

            click.echo("\nOrphaned Records Check:")
            for check in orphaned:
                click.echo(f"{check[0]}: {check[1]} orphaned records")

            # Check for duplicate requirements
            duplicates = db.session.execute(text("""
                SELECT template_id, subject_id, COUNT(*)
                FROM template_subject_requirements
                GROUP BY template_id, subject_id
                HAVING COUNT(*) > 1
            """)).fetchall()

            if duplicates:
                click.echo("\nFound duplicate template requirements:")
                for dup in duplicates:
                    click.echo(f"Template {dup[0]}, Subject {dup[1]}: {dup[2]} occurrences")

            # Check template coverage
            coverage = db.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT c.course_name) as total_courses,
                    COUNT(DISTINCT crt.name) as templates,
                    (COUNT(DISTINCT crt.name)::float / 
                    COUNT(DISTINCT c.course_name)::float * 100) as coverage
                FROM course c
                LEFT JOIN course_requirement_templates crt 
                    ON c.course_name = crt.name
            """)).fetchone()

            click.echo("\nTemplate Coverage:")
            click.echo(f"Total unique courses: {coverage[0]}")
            click.echo(f"Courses with templates: {coverage[1]}")
            click.echo(f"Coverage percentage: {coverage[2]:.2f}%")

        except Exception as e:
            click.echo(f"Error verifying requirements: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-migrate-subjects')
    @with_appcontext
    def migrate_subjects():
        """Extract and migrate subjects from JSON data"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return

        try:
            click.echo('Starting subject migration...')
            
            # Load JSON data
            json_path = os.path.join(app.root_path, 'data', 'inst_data.json')
            try:
                with open(json_path, 'r') as f:
                    json_data = json.load(f)
                click.echo('Loaded JSON data successfully')
            except Exception as e:
                click.echo(f'Error loading JSON data: {str(e)}')
                return

            # Create categories first
            categories_created = 0
            click.echo('\nCreating subject categories...')
            for category_name, subjects in json_data['subject_classifications'].items():
                try:
                    category = SubjectCategories(name=category_name)
                    db.session.add(category)
                    categories_created += 1
                except Exception as e:
                    click.echo(f'Error creating category {category_name}: {str(e)}')
                    continue
            
            try:
                db.session.commit()
                click.echo(f'Created {categories_created} categories successfully')
            except Exception as e:
                db.session.rollback()
                click.echo(f'Error committing categories: {str(e)}')
                return

            # Now create subjects
            subjects_created = 0
            click.echo('\nCreating subjects...')
            for category_name, subjects_data in json_data['subject_classifications'].items():
                category = SubjectCategories.query.filter_by(name=category_name).first()
                if not category:
                    click.echo(f'Category {category_name} not found, skipping its subjects')
                    continue

                for subcategory, subject_list in subjects_data.items():
                    if isinstance(subject_list, list):  # Ensure we're dealing with a list of subjects
                        for subject_name in subject_list:
                            try:
                                # Check if subject already exists
                                if not Subjects.query.filter_by(name=subject_name).first():
                                    is_core = subject_name.lower() in ['english language', 'mathematics']
                                    subject = Subjects(
                                        name=subject_name,
                                        category_id=category.id,
                                        is_core=is_core
                                    )
                                    db.session.add(subject)
                                    subjects_created += 1
                            except Exception as e:
                                click.echo(f'Error creating subject {subject_name}: {str(e)}')
                                continue

            try:
                db.session.commit()
                click.echo(f'Created {subjects_created} subjects successfully')
            except Exception as e:
                db.session.rollback()
                click.echo(f'Error committing subjects: {str(e)}')
                return

            click.echo('\nMigration completed successfully.')
            click.echo(f'Total categories created: {categories_created}')
            click.echo(f'Total subjects created: {subjects_created}')

        except Exception as e:
            click.echo(f"Error during migration: {str(e)}")
            db.session.rollback()
        finally:
            db.session.close()

    @app.cli.command('db-subjects-verify')
    @with_appcontext
    def verify_subjects():
        """Verify subject data migration"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return

        try:
            click.echo('\nVerifying subject data...')

            # Check categories
            categories = db.session.execute(text("""
                SELECT name, 
                    (SELECT COUNT(*) FROM subjects WHERE category_id = c.id) as subject_count
                FROM subject_categories c
                ORDER BY name
            """)).fetchall()

            click.echo('\nSubject Categories:')
            for cat in categories:
                click.echo(f'{cat[0]}: {cat[1]} subjects')

            # Check core subjects
            core_subjects = db.session.execute(text("""
                SELECT name, 
                    (SELECT name FROM subject_categories WHERE id = s.category_id) as category
                FROM subjects s
                WHERE is_core = true
                ORDER BY name
            """)).fetchall()

            click.echo('\nCore Subjects:')
            for subj in core_subjects:
                click.echo(f'{subj[0]} ({subj[1]})')

            # Check course templates
            templates = db.session.execute(text("""
                SELECT 
                    t.name,
                    COUNT(DISTINCT r.subject_id) as subject_count,
                    t.min_credits,
                    t.max_sittings
                FROM course_requirement_templates t
                LEFT JOIN template_subject_requirements r ON r.template_id = t.id
                GROUP BY t.id, t.name
                ORDER BY subject_count DESC
                LIMIT 10
            """)).fetchall()

            click.echo('\nTop 10 Course Templates by Subject Count:')
            for tmpl in templates:
                click.echo(f'{tmpl[0]}: {tmpl[1]} subjects (min credits: {tmpl[2]}, max sittings: {tmpl[3]})')

        except Exception as e:
            click.echo(f"Error during verification: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

    @app.cli.command('db-subjects-analyze')
    @with_appcontext
    def analyze_subjects():
        """Analyze subject patterns and relationships"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return

        try:
            click.echo('\nAnalyzing subject patterns...')

            # Analyze subject frequency in requirements
            subject_freq = db.session.execute(text("""
                WITH requirement_counts AS (
                    SELECT subject_id, 
                        COUNT(*) as total_uses,
                        SUM(CASE WHEN is_mandatory THEN 1 ELSE 0 END) as mandatory_uses
                    FROM template_subject_requirements
                    GROUP BY subject_id
                )
                SELECT 
                    s.name,
                    c.name as category,
                    r.total_uses,
                    r.mandatory_uses,
                    s.is_core
                FROM requirement_counts r
                JOIN subjects s ON s.id = r.subject_id
                JOIN subject_categories c ON c.id = s.category_id
                ORDER BY r.total_uses DESC
                LIMIT 20
            """)).fetchall()

            click.echo('\nTop 20 Most Used Subjects:')
            for subj in subject_freq:
                click.echo(
                    f'{subj[0]} ({subj[1]}): {subj[2]} total uses, '
                    f'{subj[3]} as mandatory {" (Core)" if subj[4] else ""}'
                )

            # Analyze subject combinations
            combinations = db.session.execute(text("""
                WITH subject_pairs AS (
                    SELECT 
                        t1.template_id,
                        t1.subject_id as subject1,
                        t2.subject_id as subject2
                    FROM template_subject_requirements t1
                    JOIN template_subject_requirements t2 
                        ON t1.template_id = t2.template_id 
                        AND t1.subject_id < t2.subject_id
                    WHERE t1.is_mandatory AND t2.is_mandatory
                )
                SELECT 
                    s1.name as subject1,
                    s2.name as subject2,
                    COUNT(*) as frequency
                FROM subject_pairs p
                JOIN subjects s1 ON s1.id = p.subject1
                JOIN subjects s2 ON s2.id = p.subject2
                GROUP BY s1.name, s2.name
                ORDER BY frequency DESC
                LIMIT 10
            """)).fetchall()

            click.echo('\nTop 10 Mandatory Subject Combinations:')
            for combo in combinations:
                click.echo(f'{combo[0]} + {combo[1]}: appears in {combo[2]} templates')

        except Exception as e:
            click.echo(f"Error during analysis: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-migrate-courses')
    @with_appcontext
    def migrate_courses():
        """Migrate courses to new normalized structure"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            click.echo('Starting course structure migration...')
            from .utils.db_ops import migrate_course_structure
            migrate_course_structure()
            click.echo('Course structure migration completed successfully.')
        except Exception as e:
            click.echo(f"Error during migration: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()
            
    @app.cli.command('db-verify-migration')
    @with_appcontext
    def verify_migration():
        """Verify course migration results"""
        if not wait_for_db_cli():
            click.echo("Could not establish database connection")
            return
            
        try:
            from .utils.db_ops import verify_migration_results
            results = verify_migration_results()
            
            click.echo("\nMigration Results:")
            click.echo(f"Original unique courses: {results['old_unique_courses']}")
            click.echo(f"Original total courses: {results['old_total_courses']}")
            click.echo(f"New unique courses: {results['new_unique_courses']}")
            click.echo(f"Course requirements: {results['course_requirements']}")
            click.echo(f"Subject requirements: {results['subject_requirements']}")
            
            # Verify counts match expectations
            if results['old_unique_courses'] != results['new_unique_courses']:
                click.echo("\nWARNING: Unique course counts don't match!")
            if results['old_total_courses'] != results['course_requirements']:
                click.echo("\nWARNING: Total course requirements don't match original course count!")
                
        except Exception as e:
            click.echo(f"Error during verification: {str(e)}")
            raise
        
    @app.cli.command('verify-course-search')
    @with_appcontext
    def verify_course_search():
        """Verify course search vectors and functionality"""
        try:
            # Check search vector population
            null_vectors = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM course 
                WHERE search_vector IS NULL
            """)).scalar()
            
            total_courses = db.session.execute(text("""
                SELECT COUNT(*) FROM course
            """)).scalar()
            
            click.echo(f"\nSearch Vector Status:")
            click.echo(f"Total courses: {total_courses}")
            click.echo(f"Courses without search vector: {null_vectors}")
            
            if null_vectors > 0:
                click.echo("\nUpdating missing search vectors...")
                db.session.execute(text("""
                    UPDATE course 
                    SET search_vector = 
                        setweight(to_tsvector('english', coalesce(course_name,'')), 'A') ||
                        setweight(to_tsvector('english', coalesce(code,'')), 'B')
                    WHERE search_vector IS NULL
                """))
                db.session.commit()
                
            click.echo("\nSearch vector verification complete.")
            
        except Exception as e:
            click.echo(f"Error verifying course search: {str(e)}")
            db.session.rollback()
            
    @app.cli.command('db-verify-relationships')
    @with_appcontext
    def verify_relationships():
        """Verify course-university relationships"""
        try:
            click.echo("\nVerifying course-university relationships...")
            
            # Check courses with no requirements
            orphaned = db.session.execute(text("""
                SELECT COUNT(*)
                FROM course c
                LEFT JOIN course_requirement cr ON c.id = cr.course_id
                WHERE cr.id IS NULL
            """)).scalar()
            
            # Check requirements with no subjects
            missing_subjects = db.session.execute(text("""
                SELECT COUNT(*)
                FROM course_requirement cr
                LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
                WHERE sr.id IS NULL
            """)).scalar()
            
            # Check requirement distribution
            requirement_stats = db.session.execute(text("""
                SELECT 
                    COUNT(DISTINCT c.id) as total_courses,
                    COUNT(DISTINCT cr.id) as total_requirements,
                    COUNT(DISTINCT sr.id) as total_subject_requirements
                FROM course c
                LEFT JOIN course_requirement cr ON c.id = cr.course_id
                LEFT JOIN subject_requirement sr ON cr.id = sr.course_requirement_id
            """)).fetchone()
            
            click.echo(f"\nRelationship Status:")
            click.echo(f"Courses without requirements: {orphaned}")
            click.echo(f"Requirements without subjects: {missing_subjects}")
            click.echo(f"\nDistribution:")
            click.echo(f"Total courses: {requirement_stats[0]}")
            click.echo(f"Total requirements: {requirement_stats[1]}")
            click.echo(f"Total subject requirements: {requirement_stats[2]}")
            
            # Check for courses with multiple requirements
            duplicates = db.session.execute(text("""
                SELECT c.course_name, COUNT(cr.id)
                FROM course c
                JOIN course_requirement cr ON c.id = cr.course_id
                GROUP BY c.id, c.course_name
                HAVING COUNT(cr.id) > 1
                ORDER BY COUNT(cr.id) DESC
                LIMIT 5
            """)).fetchall()
            
            if duplicates:
                click.echo("\nCourses with multiple requirements:")
                for dup in duplicates:
                    click.echo(f"- {dup[0]}: {dup[1]} requirements")
                    
        except Exception as e:
            click.echo(f"Error verifying relationships: {str(e)}")
            db.session.rollback()
            raise
        finally:
            db.session.close()