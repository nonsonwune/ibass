# app/cli.py
import click
from flask.cli import with_appcontext
from .utils.search import init_search_vectors
from .extensions import db
from sqlalchemy import text
import logging

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
                WHERE table_name = 'university' 
                AND column_name = 'search_vector'
            """)).fetchone()
            click.echo(f"University search_vector column exists: {result is not None}")
            
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'course' 
                AND column_name = 'search_vector'
            """)).fetchone()
            click.echo(f"Course search_vector column exists: {result is not None}")
            
            # Check indexes
            result = db.session.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'university' 
                AND indexname = 'idx_university_search'
            """)).fetchone()
            click.echo(f"University search index exists: {result is not None}")
            
            # Check if vectors are populated
            uni_count = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM university 
                WHERE search_vector IS NOT NULL
            """)).scalar()
            click.echo(f"Universities with search vectors: {uni_count}")
            
            # Test a simple search
            click.echo("\nTesting search for 'lagos'...")
            unis = db.session.execute(text("""
                SELECT university_name 
                FROM university 
                WHERE search_vector @@ to_tsquery('english', 'lagos')
                LIMIT 5
            """)).fetchall()
            click.echo(f"Found {len(unis)} universities containing 'lagos'")
            for uni in unis:
                click.echo(f"- {uni.university_name}")
                
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
            
            # Get transfer log records
            transfer_stats = db.session.execute(text("""
                SELECT table_name, last_transferred_id
                FROM transfer_log
                WHERE table_name IN ('universities', 'courses')
            """)).fetchall()
            
            # Get actual table counts and max IDs
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
            """)).fetchall()
            
            # Get orphaned courses
            orphaned_courses = db.session.execute(text("""
                SELECT c.id, c.course_name, c.university_name
                FROM course c
                LEFT JOIN university u ON c.university_name = u.university_name
                WHERE u.university_name IS NULL
            """)).fetchall()
            
            # Get duplicate courses
            duplicate_courses = db.session.execute(text("""
                SELECT course_name, university_name, COUNT(*)
                FROM course
                GROUP BY course_name, university_name
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            click.echo("\nTransfer Log Status:")
            for record in transfer_stats:
                click.echo(f"{record.table_name}: Last ID = {record.last_transferred_id}")
                
            click.echo("\nCurrent Table Status:")
            for stat in table_stats:
                click.echo(f"{stat.table_name}:")
                click.echo(f"  Record Count: {stat.record_count}")
                click.echo(f"  Max ID: {stat.max_id}")
                
            if orphaned_courses:
                click.echo("\nOrphaned Courses (no matching university):")
                for course in orphaned_courses:
                    click.echo(f"ID: {course.id}, Course: {course.course_name}, "
                             f"University: {course.university_name}")
                    
            if duplicate_courses:
                click.echo("\nDuplicate Courses:")
                for dup in duplicate_courses:
                    click.echo(f"Course: {dup.course_name}, University: {dup.university_name}, "
                             f"Count: {dup[2]}")
            
            # Check for gaps in IDs
            click.echo("\nChecking for gaps in IDs...")
            gaps = db.session.execute(text("""
                WITH RECURSIVE numbers AS (
                    SELECT MIN(id) as num FROM course
                    UNION ALL
                    SELECT num + 1
                    FROM numbers
                    WHERE num < (SELECT MAX(id) FROM course)
                )
                SELECT num
                FROM numbers n
                WHERE NOT EXISTS (
                    SELECT 1 FROM course c WHERE c.id = n.num
                )
            """)).fetchall()
            
            if gaps:
                click.echo(f"\nFound {len(gaps)} gaps in course IDs:")
                click.echo(f"First few missing IDs: {[gap[0] for gap in gaps[:5]]}")
            
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