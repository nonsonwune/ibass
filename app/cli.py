# app/cli.py
import click
from flask.cli import with_appcontext
from .utils.search import init_search_vectors
from .extensions import db
from sqlalchemy import text

def init_app(app):
    @app.cli.command()
    @with_appcontext
    def init_search():
        """Initialize search vectors for existing records"""
        click.echo('Initializing search vectors...')
        init_search_vectors()
        click.echo('Search vectors initialized.')

    @app.cli.command()
    @with_appcontext
    def reset_search_vectors():
        """Reset search vectors to null"""
        click.echo('Resetting search vectors...')
        with db.session.begin():
            db.session.execute(text('UPDATE university SET search_vector = NULL'))
            db.session.execute(text('UPDATE course SET search_vector = NULL'))
        click.echo('Search vectors reset. Run init-search to reinitialize them.')
    
    @app.cli.command()
    @with_appcontext
    def verify_search_setup():
        """Verify search setup and indexes"""
        click.echo("\nChecking database setup...")
        
        try:
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
            raise