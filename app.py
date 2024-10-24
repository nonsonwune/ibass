# app.py
from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash
import logging
from sqlalchemy import inspect, text
import sqlalchemy.exc

app = create_app()

def verify_table_exists(table_name):
    """Verify if a table exists and has the correct structure."""
    try:
        with db.engine.connect() as conn:
            conn.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
            return True
    except sqlalchemy.exc.ProgrammingError:
        return False

def drop_all_tables():
    """Drop all existing tables in the correct order."""
    try:
        with db.engine.connect() as conn:
            # First drop all constraints
            conn.execute(text("""
                DO $$ 
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT constraint_name, table_name 
                             FROM information_schema.table_constraints 
                             WHERE constraint_type IN ('FOREIGN KEY', 'UNIQUE')) 
                    LOOP
                        EXECUTE 'ALTER TABLE ' || quote_ident(r.table_name) || 
                                ' DROP CONSTRAINT IF EXISTS ' || quote_ident(r.constraint_name);
                    END LOOP;
                END $$;
            """))
            
            # Then drop all tables in reverse dependency order
            tables = ['votes', 'comments', 'courses', 'universities', 'users']
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            
            conn.commit()
    except Exception as e:
        logging.warning(f"Error dropping tables and constraints: {str(e)}")

def init_db():
    """Initialize database with proper error handling and verification."""
    with app.app_context():
        try:
            # Check if tables exist but are incomplete/corrupted
            tables_exist = all(
                verify_table_exists(table_name) 
                for table_name in ['users', 'universities', 'courses', 'comments', 'votes']
            )
            
            if not tables_exist:
                logging.info("Tables missing or incomplete. Recreating all tables...")
                
                # Drop everything and start fresh
                drop_all_tables()
                
                # Create all tables
                db.create_all()
                logging.info("Database tables created successfully")
                
                # Create admin user
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    password=generate_password_hash("adminpassword"),
                    is_admin=True,
                    is_verified=True,
                    score=0
                )
                db.session.add(admin)
                db.session.commit()
                logging.info("Admin user created successfully")
            
            else:
                logging.info("All required tables exist")
                
                # Verify admin user exists
                admin_user = User.query.filter_by(username="admin").first()
                if not admin_user:
                    admin = User(
                        username="admin",
                        email="admin@example.com",
                        password=generate_password_hash("adminpassword"),
                        is_admin=True,
                        is_verified=True,
                        score=0
                    )
                    db.session.add(admin)
                    db.session.commit()
                    logging.info("Admin user created")
                else:
                    logging.info("Admin user already exists")
            
            logging.info("Database initialization completed successfully")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during database initialization: {str(e)}")
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        init_db()
        app.run(host="0.0.0.0", port=5001)
    except Exception as e:
        logging.error(f"Failed to start application: {str(e)}")
        exit(1)