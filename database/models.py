from sqlalchemy import create_engine, Column, Integer, String, Text, DECIMAL, Boolean, DateTime, Date, Time, ForeignKey, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
import os
from typing import Optional
from datetime import datetime

Base = declarative_base()

class University(Base):
    __tablename__ = 'universities'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    country = Column(String(100))
    region = Column(String(100))
    website_url = Column(Text)
    api_config = Column(JSONB)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    faculties = relationship("Faculty", back_populates="university")
    subjects = relationship("Subject", back_populates="university")
    courses = relationship("Course", back_populates="university")
    terms = relationship("Term", back_populates="university")
    instructors = relationship("Instructor", back_populates="university")

class Faculty(Base):
    __tablename__ = 'faculties'
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id', ondelete='CASCADE'))
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    website_url = Column(Text)
    dean_info = Column(JSONB)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    university = relationship("University", back_populates="faculties")

class Subject(Base):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id', ondelete='CASCADE'))
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    website_url = Column(Text)
    faculty_associations = Column(JSONB)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    university = relationship("University", back_populates="subjects")
    courses = relationship("Course", back_populates="subject")

class Course(Base):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id', ondelete='CASCADE'))
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'))
    code = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    credit_hours = Column(DECIMAL(3,1))
    level = Column(String(20))
    prerequisites = Column(Text)
    corequisites = Column(Text)
    exclusions = Column(Text)
    website_url = Column(Text)
    fees = Column(JSONB)
    schedule_info = Column(JSONB)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    university = relationship("University", back_populates="courses")
    subject = relationship("Subject", back_populates="courses")
    sections = relationship("CourseSection", back_populates="course")

class Term(Base):
    __tablename__ = 'terms'
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id', ondelete='CASCADE'))
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    registration_start = Column(Date)
    registration_end = Column(Date)
    is_active = Column(Boolean, default=False)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    university = relationship("University", back_populates="terms")
    sections = relationship("CourseSection", back_populates="term")

class CourseSection(Base):
    __tablename__ = 'course_sections'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'))
    term_id = Column(Integer, ForeignKey('terms.id', ondelete='CASCADE'))
    section_code = Column(String(50), nullable=False)
    section_type = Column(String(50))
    capacity = Column(Integer)
    enrolled = Column(Integer, default=0)
    waitlist = Column(Integer, default=0)
    status = Column(String(50), default='open')
    instructor_info = Column(JSONB)
    schedule = Column(JSONB)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    course = relationship("Course", back_populates="sections")
    term = relationship("Term", back_populates="sections")
    exams = relationship("ExamSchedule", back_populates="section")

class ExamSchedule(Base):
    __tablename__ = 'exam_schedules'
    
    id = Column(Integer, primary_key=True)
    course_section_id = Column(Integer, ForeignKey('course_sections.id', ondelete='CASCADE'))
    exam_type = Column(String(50))
    exam_date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    location = Column(String(255))
    duration_minutes = Column(Integer)
    special_instructions = Column(Text)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    section = relationship("CourseSection", back_populates="exams")

class Instructor(Base):
    __tablename__ = 'instructors'
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id', ondelete='CASCADE'))
    employee_id = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    title = Column(String(100))
    department = Column(String(255))
    email = Column(String(255))
    office_location = Column(String(255))
    research_areas = Column(ARRAY(Text))
    ratings = Column(JSONB)
    salary_info = Column(JSONB)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    university = relationship("University", back_populates="instructors")

class SyncLog(Base):
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id', ondelete='CASCADE'))
    data_type = Column(String(100))
    sync_status = Column(String(50))
    records_processed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(JSONB)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    metadata = Column(JSONB)

# Database connection and session management
class DatabaseManager:
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://user:password@localhost:5432/university_data')
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close the database connection"""
        self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Dependency for FastAPI to get database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()
