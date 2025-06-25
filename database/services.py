from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from database.models import (
    University, Faculty, Subject, Course, Term, 
    CourseSection, ExamSchedule, Instructor, SyncLog
)
import json
from datetime import datetime

class UniversityService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_university(self, code: str, name: str, **kwargs) -> University:
        """Get existing university or create new one"""
        university = self.db.query(University).filter(University.code == code).first()
        if not university:
            university = University(code=code, name=name, **kwargs)
            self.db.add(university)
            self.db.commit()
            self.db.refresh(university)
        return university
    
    def get_university_by_code(self, code: str) -> Optional[University]:
        """Get university by code"""
        return self.db.query(University).filter(University.code == code).first()

class FacultyService:
    def __init__(self, db: Session):
        self.db = db
    
    def upsert_faculty(self, university_id: int, code: str, name: str, **kwargs) -> Faculty:
        """Insert or update faculty"""
        faculty = self.db.query(Faculty).filter(
            and_(Faculty.university_id == university_id, Faculty.code == code)
        ).first()
        
        if faculty:
            faculty.name = name
            for key, value in kwargs.items():
                setattr(faculty, key, value)
            faculty.updated_at = datetime.utcnow()
        else:
            faculty = Faculty(
                university_id=university_id,
                code=code,
                name=name,
                **kwargs
            )
            self.db.add(faculty)
        
        self.db.commit()
        self.db.refresh(faculty)
        return faculty
    
    def get_faculties_by_university(self, university_id: int) -> List[Faculty]:
        """Get all faculties for a university"""
        return self.db.query(Faculty).filter(Faculty.university_id == university_id).all()

class SubjectService:
    def __init__(self, db: Session):
        self.db = db
    
    def upsert_subject(self, university_id: int, code: str, name: str, **kwargs) -> Subject:
        """Insert or update subject"""
        subject = self.db.query(Subject).filter(
            and_(Subject.university_id == university_id, Subject.code == code)
        ).first()
        
        if subject:
            subject.name = name
            for key, value in kwargs.items():
                setattr(subject, key, value)
            subject.updated_at = datetime.utcnow()
        else:
            subject = Subject(
                university_id=university_id,
                code=code,
                name=name,
                **kwargs
            )
            self.db.add(subject)
        
        self.db.commit()
        self.db.refresh(subject)
        return subject
    
    def get_subjects_by_university(self, university_id: int) -> List[Subject]:
        """Get all subjects for a university"""
        return self.db.query(Subject).filter(Subject.university_id == university_id).all()

class CourseService:
    def __init__(self, db: Session):
        self.db = db
    
    def upsert_course(self, university_id: int, subject_id: int, code: str, name: str, **kwargs) -> Course:
        """Insert or update course"""
        course = self.db.query(Course).filter(
            and_(Course.university_id == university_id, Course.code == code)
        ).first()
        
        if course:
            course.name = name
            course.subject_id = subject_id
            for key, value in kwargs.items():
                setattr(course, key, value)
            course.updated_at = datetime.utcnow()
        else:
            course = Course(
                university_id=university_id,
                subject_id=subject_id,
                code=code,
                name=name,
                **kwargs
            )
            self.db.add(course)
        
        self.db.commit()
        self.db.refresh(course)
        return course
    
    def get_courses_by_university(self, university_id: int, limit: int = 100, offset: int = 0) -> List[Course]:
        """Get courses for a university with pagination"""
        return self.db.query(Course).filter(
            Course.university_id == university_id
        ).offset(offset).limit(limit).all()
    
    def search_courses(self, university_id: int, query: str, limit: int = 50) -> List[Course]:
        """Search courses by name or code"""
        return self.db.query(Course).filter(
            and_(
                Course.university_id == university_id,
                or_(
                    Course.name.ilike(f'%{query}%'),
                    Course.code.ilike(f'%{query}%'),
                    Course.description.ilike(f'%{query}%')
                )
            )
        ).limit(limit).all()

class ExamService:
    def __init__(self, db: Session):
        self.db = db
    
    def upsert_exam_schedule(self, course_section_id: int, exam_data: Dict[str, Any]) -> ExamSchedule:
        """Insert or update exam schedule"""
        exam = self.db.query(ExamSchedule).filter(
            ExamSchedule.course_section_id == course_section_id
        ).first()
        
        if exam:
            for key, value in exam_data.items():
                setattr(exam, key, value)
        else:
            exam = ExamSchedule(
                course_section_id=course_section_id,
                **exam_data
            )
            self.db.add(exam)
        
        self.db.commit()
        self.db.refresh(exam)
        return exam
    
    def get_exam_schedules_by_university(self, university_id: int) -> List[Dict[str, Any]]:
        """Get all exam schedules for a university"""
        return self.db.query(ExamSchedule).join(CourseSection).join(Course).filter(
            Course.university_id == university_id
        ).all()

class SyncService:
    def __init__(self, db: Session):
        self.db = db
    
    def log_sync_start(self, university_id: int, data_type: str) -> SyncLog:
        """Log the start of a sync operation"""
        sync_log = SyncLog(
            university_id=university_id,
            data_type=data_type,
            sync_status='in_progress',
            started_at=datetime.utcnow()
        )
        self.db.add(sync_log)
        self.db.commit()
        self.db.refresh(sync_log)
        return sync_log
    
    def log_sync_complete(self, sync_log_id: int, status: str, records_processed: int = 0, 
                         errors_count: int = 0, error_details: Dict = None):
        """Log the completion of a sync operation"""
        sync_log = self.db.query(SyncLog).filter(SyncLog.id == sync_log_id).first()
        if sync_log:
            sync_log.sync_status = status
            sync_log.records_processed = records_processed
            sync_log.errors_count = errors_count
            sync_log.error_details = error_details
            sync_log.completed_at = datetime.utcnow()
            self.db.commit()
    
    def get_recent_syncs(self, university_id: int, limit: int = 10) -> List[SyncLog]:
        """Get recent sync logs for a university"""
        return self.db.query(SyncLog).filter(
            SyncLog.university_id == university_id
        ).order_by(SyncLog.started_at.desc()).limit(limit).all()
