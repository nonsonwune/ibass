#!/usr/bin/env python3
import os
import subprocess
import logging
import time
from datetime import datetime, timedelta
import psycopg2
import difflib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from .env
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
BACKUP_DIR = os.getenv('BACKUP_DIR', 'database_backups')
LOG_FILE = os.getenv('LOG_FILE', 'database_backup.log')
BACKUP_INTERVAL_HOURS = int(os.getenv('BACKUP_INTERVAL_HOURS', 6))

# Ensure backup directory exists
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
)

def get_last_backup_time():
    """Retrieve the timestamp of the last backup."""
    last_backup_file = os.path.join(BACKUP_DIR, 'last_backup.txt')
    if os.path.exists(last_backup_file):
        with open(last_backup_file, 'r') as f:
            timestamp_str = f.read().strip()
            return datetime.fromisoformat(timestamp_str)
    else:
        return None

def update_last_backup_time():
    """Update the timestamp of the last backup."""
    last_backup_file = os.path.join(BACKUP_DIR, 'last_backup.txt')
    with open(last_backup_file, 'w') as f:
        f.write(datetime.now().isoformat())

def backup_database():
    """Perform the database backup."""
    # First verify database connection and existence
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.close()
    except psycopg2.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        print(f"Database connection failed: {e}")
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'backup_{timestamp}.sql'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        logging.info("Starting database backup.")
        # Construct the pg_dump command
        command = [
            'pg_dump',
            f'--dbname=postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
            '--file', backup_path,
            '--format', 'plain',
            '--no-owner',
            '--no-privileges',
        ]

        # Execute the backup command
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            logging.info(f"Database backup successful: {backup_filename}")
            print(f"Database backup successful: {backup_filename}")
            update_last_backup_time()
            # Optionally, check for schema changes
            check_for_schema_changes(backup_path)
        else:
            error_message = result.stderr.strip()
            logging.error(f"Database backup failed: {error_message}")
            print(f"Database backup failed: {error_message}")

    except Exception as e:
        logging.error(f"An error occurred during backup: {e}")
        print(f"An error occurred during backup: {e}")

def check_for_schema_changes(new_backup_path):
    """Compare the new backup with the previous one to detect schema changes."""
    # Find the most recent backup before the new one
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_') and f.endswith('.sql')],
        reverse=True
    )

    if len(backups) < 2:
        # Not enough backups to compare
        return

    previous_backup = backups[1]  # The second most recent backup
    previous_backup_path = os.path.join(BACKUP_DIR, previous_backup)

    # Read the schema from both backups
    with open(previous_backup_path, 'r') as f:
        previous_backup_content = f.readlines()

    with open(new_backup_path, 'r') as f:
        new_backup_content = f.readlines()

    # Generate a diff
    diff = difflib.unified_diff(
        previous_backup_content,
        new_backup_content,
        fromfile=previous_backup,
        tofile=os.path.basename(new_backup_path),
        lineterm=''
    )

    diff_output = '\n'.join(diff)

    if diff_output:
        # There are changes in the schema
        changes_log = os.path.join(BACKUP_DIR, 'schema_changes.log')
        with open(changes_log, 'a') as f:
            f.write(f"\nChanges detected on {datetime.now().isoformat()} between {previous_backup} and {os.path.basename(new_backup_path)}:\n")
            f.write(diff_output)
            f.write('\n')

        logging.info(f"Schema changes detected. Details saved in {changes_log}")
        print(f"Schema changes detected. Details saved in {changes_log}")
    else:
        logging.info("No schema changes detected.")
        print("No schema changes detected.")

def main():
    last_backup_time = get_last_backup_time()
    now = datetime.now()

    if last_backup_time is None:
        logging.info("No previous backup found. Creating a new backup.")
        backup_database()
    else:
        time_diff = now - last_backup_time
        if time_diff >= timedelta(hours=BACKUP_INTERVAL_HOURS):
            logging.info(f"Last backup was performed {time_diff} ago. Creating a new backup.")
            backup_database()
        else:
            next_backup_in = timedelta(hours=BACKUP_INTERVAL_HOURS) - time_diff
            logging.info(f"Next backup will be performed in {next_backup_in}.")
            print(f"Next backup will be performed in {next_backup_in}.")

if __name__ == '__main__':
    main()
