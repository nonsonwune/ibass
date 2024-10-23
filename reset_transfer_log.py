# reset_transfer_log.py
import logging
import sys
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# ----------------------------- Configuration -----------------------------

# Configure logging
LOG_FILE = "reset_transfer_log.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s %(levelname)s:%(message)s",
)

# Database URI (Ensure this matches your PostgreSQL configuration)
POSTGRES_DATABASE_URI = "postgresql://nuf_user:AuoK48a6pVT0vJQhl5HKt2GG9nJhtGZJ@dpg-cs91krogph6c73bv1930-a.oregon-postgres.render.com/naija_uni_finder_db"

# ----------------------------- Database Setup -----------------------------

# Create engine and session
try:
    postgres_engine = create_engine(POSTGRES_DATABASE_URI)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    logging.debug("Successfully connected to PostgreSQL database.")
except Exception as e:
    logging.error(f"Error connecting to PostgreSQL database: {str(e)}")
    sys.exit(1)

# Create declarative base
Base = declarative_base()

# ----------------------------- Models -----------------------------

# TransferLog model to keep track of last transferred IDs
class TransferLog(Base):
    __tablename__ = "transfer_log"
    id = Column(Integer, primary_key=True)
    table_name = Column(String, nullable=False, unique=True)
    last_transferred_id = Column(Integer, nullable=False)
    last_transfer_time = Column(DateTime, nullable=False)

# ----------------------------- Reset Function -----------------------------

def reset_transfer_log():
    """
    Resets the TransferLog by deleting all entries.
    """
    try:
        # Delete all entries from TransferLog
        delete_stmt = text("DELETE FROM transfer_log;")
        postgres_session.execute(delete_stmt)
        postgres_session.commit()
        logging.info("Successfully reset TransferLog by deleting all entries.")
        print("Successfully reset TransferLog by deleting all entries.")
    except SQLAlchemyError as e:
        postgres_session.rollback()
        logging.error(f"Error resetting TransferLog: {str(e)}")
        print(f"Error resetting TransferLog: {str(e)}")
        sys.exit(1)
    finally:
        postgres_session.close()
        logging.debug("PostgreSQL session closed.")

# ----------------------------- Main Execution -----------------------------

def main():
    reset_transfer_log()

if __name__ == "__main__":
    main()
