# app.py
from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash
import logging
from sqlalchemy import inspect, text
import sqlalchemy.exc
import time

# Configure logging once at the module level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = create_app()

def wait_for_db(max_retries=5, retry_interval=5):
    """Wait for database to become available."""
    for attempt in range(max_retries):
        try:
            # Test connection with a simple query
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1")).first()
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                return False
            logging.warning(f"Database connection attempt {attempt + 1} failed. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

def verify_table_exists(table_name):
    """Verify if a table exists."""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = :table_name"
            ), {'table_name': table_name}).first()
            return result is not None
    except Exception as e:
        logging.error(f"Error checking table {table_name}: {str(e)}")
        return False

def verify_admin_exists():
    """Verify if admin user exists."""
    try:
        with app.app_context():
            admin = User.query.filter_by(username="admin").first()
            return admin is not None
    except Exception as e:
        logging.error(f"Error verifying admin: {str(e)}")
        return False

def init_db():
    """Initialize database with proper error handling and verification."""
    with app.app_context():
        try:
            # First, wait for database to be available
            if not wait_for_db():
                raise Exception("Could not establish database connection")

            # Configure SQLAlchemy engine with keepalive settings
            db.engine.pool_pre_ping = True
            db.engine.pool_recycle = 3600
            
            # Check if tables exist
            required_tables = ['user', 'university', 'course', 'comment', 'vote']
            missing_tables = []
            
            for table in required_tables:
                if not verify_table_exists(table):
                    missing_tables.append(table)
            
            if missing_tables:
                logging.error("The following tables are missing: %s", missing_tables)
                logging.error("Please ensure all required tables exist in the database")
                raise Exception(f"Missing required tables: {missing_tables}")
            
            logging.info("All required tables exist")
            
            # Only create admin user if it doesn't exist
            if not verify_admin_exists():
                logging.info("Creating admin user...")
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    password=generate_password_hash("adminpassword"),
                    is_admin=1,
                    is_verified=1,
                    score=0
                )
                db.session.add(admin)
                db.session.commit()
                logging.info("Admin user created successfully")
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
    
    try:
        init_db()
        # Configure the app to handle connection drops
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'connect_args': {
                'connect_timeout': 30,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        }
        app.run(host="0.0.0.0", port=5001)
    except Exception as e:
        logging.error(f"Failed to start application: {str(e)}")
        exit(1)