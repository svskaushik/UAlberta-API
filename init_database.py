#!/usr/bin/env python3
"""
Database initialization script for the University API.
This script ensures the database schema is properly set up and creates tables using SQLAlchemy models.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with proper schema"""
    try:
        from database.models import db_manager, Base
        from sqlalchemy import text
        
        logger.info("Initializing database...")
        
        # Create a connection to test database connectivity
        engine = db_manager.engine
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to database: {version}")
        
        # Drop all tables (for clean setup in development)
        if os.getenv('DROP_TABLES', 'false').lower() == 'true':
            logger.warning("Dropping all existing tables...")
            Base.metadata.drop_all(bind=engine)
        
        # Create all tables using SQLAlchemy models
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
        logger.info(f"Successfully created {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def verify_schema():
    """Verify that the database schema matches our models"""
    try:
        from database.models import db_manager
        from sqlalchemy import text, inspect
        
        logger.info("Verifying database schema...")
        
        engine = db_manager.engine
        inspector = inspect(engine)
        
        # Check if all expected tables exist
        expected_tables = [
            'universities', 'faculties', 'subjects', 'courses', 
            'terms', 'course_sections', 'exam_schedules', 
            'instructors', 'sync_logs'
        ]
        
        existing_tables = inspector.get_table_names()
        
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        
        # Check critical columns
        critical_checks = [
            ('universities', 'meta'),
            ('faculties', 'meta'),
            ('subjects', 'meta'),
            ('courses', 'meta'),
        ]
        
        for table, column in critical_checks:
            columns = [col['name'] for col in inspector.get_columns(table)]
            if column not in columns:
                logger.error(f"Missing column '{column}' in table '{table}'")
                return False
        
        logger.info("Schema verification successful!")
        return True
        
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False

def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")
    
    # Check database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    logger.info(f"Using database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    # Initialize database
    if not init_database():
        logger.error("Database initialization failed")
        sys.exit(1)
    
    # Verify schema
    if not verify_schema():
        logger.error("Schema verification failed")
        sys.exit(1)
    
    logger.info("Database initialization completed successfully!")

if __name__ == "__main__":
    main()
