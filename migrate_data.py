#!/usr/bin/env python3
"""
Migration script to move data from JSON files to PostgreSQL database.
Run this after setting up your database to import existing data.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from database.models import db_manager
from database.services import (
    UniversityService, FacultyService, SubjectService, CourseService
)

def migrate_json_to_database():
    """Migrate existing JSON data to PostgreSQL database"""
    
    # Initialize database
    db_manager.create_tables()
    db = db_manager.get_session()
    
    try:
        # Initialize services
        university_service = UniversityService(db)
        faculty_service = FacultyService(db)
        subject_service = SubjectService(db)
        course_service = CourseService(db)
        
        # Create/get UAlberta university record
        university = university_service.get_or_create_university(
            code='ualberta',
            name='University of Alberta',
            country='Canada',
            region='Alberta',
            website_url='https://www.ualberta.ca',
            api_config={
                'base_url': 'https://apps.ualberta.ca',
                'catalog_url': 'https://apps.ualberta.ca/catalogue'
            }
        )
        
        print(f"Created/found university: {university.name} (ID: {university.id})")
        
        # Migrate faculties
        faculties_file = Path("data/faculties.json")
        if faculties_file.exists():
            print("Migrating faculties...")
            with open(faculties_file, 'r') as f:
                faculties_data = json.load(f)
            
            for faculty_code, faculty_info in faculties_data.items():
                faculty = faculty_service.upsert_faculty(
                    university_id=university.id,
                    code=faculty_code,
                    name=faculty_info.get('faculty_name', faculty_info.get('name', '')),
                    website_url=faculty_info.get('faculty_link'),
                    metadata={
                        'migrated_at': str(datetime.utcnow()),
                        'original_data': faculty_info
                    }
                )
                print(f"  Migrated faculty: {faculty.code} - {faculty.name}")
        
        # Migrate subjects
        subjects_file = Path("data/subjects.json")
        if subjects_file.exists():
            print("Migrating subjects...")
            with open(subjects_file, 'r') as f:
                subjects_data = json.load(f)
            
            for subject_code, subject_info in subjects_data.items():
                subject = subject_service.upsert_subject(
                    university_id=university.id,
                    code=subject_code,
                    name=subject_info.get('name', ''),
                    website_url=subject_info.get('link'),
                    faculty_associations=subject_info.get('faculties', []),
                    metadata={
                        'migrated_at': str(datetime.utcnow()),
                        'original_data': subject_info
                    }
                )
                print(f"  Migrated subject: {subject.code} - {subject.name}")
        
        # Migrate courses
        courses_file = Path("data/courses.json")
        if courses_file.exists():
            print("Migrating courses...")
            with open(courses_file, 'r') as f:
                courses_data = json.load(f)
            
            # Get subjects mapping for foreign keys
            subjects = subject_service.get_subjects_by_university(university.id)
            subject_map = {s.code: s.id for s in subjects}
            
            for course_code, course_info in courses_data.items():
                # Extract subject code from course code (e.g., CMPUT from CMPUT401)
                subject_code = ''.join([c for c in course_code if c.isalpha()]).upper()
                subject_id = subject_map.get(subject_code)
                
                if not subject_id:
                    print(f"  Warning: Subject {subject_code} not found for course {course_code}")
                    continue
                
                # Determine level
                level = 'junior' if any(c.isdigit() and c == '1' for c in course_code) else 'senior'
                
                # Parse credit hours
                credit_hours = None
                if 'course_weight' in course_info:
                    try:
                        weight_str = str(course_info['course_weight']).strip()
                        if weight_str and weight_str.replace('.', '').isdigit():
                            credit_hours = float(weight_str)
                    except:
                        pass
                
                course = course_service.upsert_course(
                    university_id=university.id,
                    subject_id=subject_id,
                    code=course_code,
                    name=course_info.get('course_name', ''),
                    description=course_info.get('course_description', ''),
                    credit_hours=credit_hours,
                    level=level,
                    prerequisites=course_info.get('course_prerequisites'),
                    website_url=course_info.get('course_link'),
                    fees={'fee_index': course_info.get('course_fee_index')} if course_info.get('course_fee_index') else None,
                    schedule_info={
                        'lecture_hours': course_info.get('course_hrs_for_lecture'),
                        'seminar_hours': course_info.get('course_hrs_for_seminar'),
                        'lab_hours': course_info.get('course_hrs_for_labtime'),
                        'schedule': course_info.get('course_schedule')
                    },
                    metadata={
                        'migrated_at': str(datetime.utcnow()),
                        'original_data': course_info
                    }
                )
                print(f"  Migrated course: {course.code} - {course.name}")
        
        # Migrate exam schedules
        exam_file = Path("exam_schedules.json")
        if exam_file.exists():
            print("Migrating exam schedules...")
            with open(exam_file, 'r') as f:
                exam_data = json.load(f)
            
            # Store exam data in university metadata for now
            university.metadata = university.metadata or {}
            university.metadata['exam_schedules'] = exam_data
            university.metadata['exam_schedules_migrated_at'] = str(datetime.utcnow())
            db.commit()
            print("  Migrated exam schedules to university metadata")
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_json_to_database()
