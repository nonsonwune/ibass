from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.exc import OperationalError
import time
from datetime import datetime
import logging
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def create_db_engine(url, max_retries=3, retry_interval=5):
    """Create database engine with retry logic"""
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                url,
                connect_args={
                    'connect_timeout': 30,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5
                }
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return engine
        except OperationalError as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

def create_tables(engine):
    """Create all required tables if they don't exist"""
    metadata = MetaData()
    
    # Define user table based on your User model
    user_table = Table(
        'user', metadata,
        Column('id', Integer, primary_key=True),
        Column('username', String(20), unique=True, nullable=False),
        Column('email', String(120), unique=True, nullable=False),
        Column('password', String(256), nullable=False),
        Column('is_admin', Boolean, default=False),
        Column('is_verified', Boolean, default=False),
        Column('score', Integer, default=0, nullable=False)
    )
    
    # Define other required tables
    university_table = Table(
        'university', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False)
        # Add other university columns as needed
    )
    
    course_table = Table(
        'course', metadata,
        Column('id', Integer, primary_key=True),
        Column('university_id', Integer, ForeignKey('university.id')),
        Column('name', String(100), nullable=False)
        # Add other course columns as needed
    )
    
    comment_table = Table(
        'comment', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('user.id')),
        Column('content', String(500), nullable=False)
        # Add other comment columns as needed
    )
    
    vote_table = Table(
        'vote', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('user.id')),
        Column('comment_id', Integer, ForeignKey('comment.id'))
        # Add other vote columns as needed
    )
    
    try:
        metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
        # Create admin user if user table was just created
        with engine.connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM \"user\" WHERE username = 'admin'")
            if result.scalar() == 0:
                admin_password = generate_password_hash("adminpassword")
                conn.execute(
                    user_table.insert().values(
                        username="admin",
                        email="admin@example.com",
                        password=admin_password,
                        is_admin=True,
                        is_verified=True,
                        score=0
                    )
                )
                conn.commit()
                logger.info("Admin user created successfully")
            
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

def init_database(database_url):
    """Initialize database with connection retry and table creation"""
    try:
        logger.info(f"Connecting to database: {database_url}")
        engine = create_db_engine(database_url)
        
        logger.info("Creating tables...")
        create_tables(engine)
        
        return engine
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Replace with your actual database URL
    DATABASE_URL = "postgresql://nuf_user:AuoK48a6pVT0vJQhl5HKt2GG9nJhtGZJ@dpg-cs91krogph6c73bv1930-a.oregon-postgres.render.com/naija_uni_finder_db"
    
    try:
        engine = init_database(DATABASE_URL)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        exit(1)