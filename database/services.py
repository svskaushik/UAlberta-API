from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, case
from database.models import (
    University, Faculty, Subject, Course, Term, 
    CourseSection, ExamSchedule, Instructor, SyncLog
)
import json
from datetime import datetime

# Import cache utilities with fallback
try:
    from utils.cache import cached_course_search, course_search_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    # Create dummy decorator if cache is not available
    def cached_course_search(cache_enabled: bool = True):
        def decorator(func):
            return func
        return decorator

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
    
    def get_courses_summary_by_university(self, university_id: int, limit: int = 100, offset: int = 0) -> List[Course]:
        """Get courses summary (only essential fields) for a university with pagination"""
        return self.db.query(Course.id, Course.code, Course.name).filter(
            Course.university_id == university_id
        ).offset(offset).limit(limit).all()
    
    @cached_course_search(cache_enabled=CACHE_AVAILABLE)
    def search_courses_summary(self, university_id: int, query: str, limit: int = 50) -> List[Course]:
        """Search courses summary by name or code (only essential fields)"""
        return self.db.query(Course.id, Course.code, Course.name).filter(
            and_(
                Course.university_id == university_id,
                or_(
                    Course.name.ilike(f'%{query}%'),
                    Course.code.ilike(f'%{query}%')
                )
            )
        ).limit(limit).all()

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
    
    def search_courses_summary_by_faculty(self, university_id: int, query: str, faculty_code: Optional[str] = None, limit: int = 50) -> List[Course]:
        """Search courses summary by name or code with optional faculty filter"""
        base_query = self.db.query(Course.id, Course.code, Course.name).join(Subject).filter(
            and_(
                Course.university_id == university_id,
                or_(
                    Course.name.ilike(f'%{query}%'),
                    Course.code.ilike(f'%{query}%')
                )
            )
        )
        
        if faculty_code:
            # Filter by faculty association
            base_query = base_query.filter(
                Subject.faculty_associations.contains([faculty_code])
            )
        
        return base_query.limit(limit).all()
    
    @cached_course_search(cache_enabled=CACHE_AVAILABLE)
    def search_courses_summary_optimized(self, university_id: int, query: str, limit: int = 50) -> List[Course]:
        """
        Optimized course search with relevance ranking.
        Prioritizes exact matches, then prefix matches, then partial matches.
        """
        query_upper = query.upper()
        
        # Build the query with ranking/ordering for better relevance
        results = self.db.query(Course.id, Course.code, Course.name).filter(
            Course.university_id == university_id
        ).filter(
            or_(
                Course.code.ilike(f'{query_upper}%'),  # Code starts with query
                Course.code.ilike(f'%{query_upper}%'),  # Code contains query
                Course.name.ilike(f'{query}%'),         # Name starts with query  
                Course.name.ilike(f'%{query}%')         # Name contains query
            )
        ).order_by(
            # Order by relevance: exact code match first, then code prefix, then name prefix, then partial matches
            case(
                (Course.code == query_upper, 1),
                (Course.code.ilike(f'{query_upper}%'), 2), 
                (Course.name.ilike(f'{query}%'), 3),
                else_=4
            ),
            Course.code,  # Secondary sort by code for consistency
            Course.name
        ).limit(limit).all()
        
        return results
    
    def search_courses_summary_by_faculty_optimized(self, university_id: int, query: str, faculty_code: Optional[str] = None, limit: int = 50) -> List[Course]:
        """
        Optimized course search with faculty filter and relevance ranking.
        """
        query_upper = query.upper()
        
        base_query = self.db.query(Course.id, Course.code, Course.name).join(Subject).filter(
            Course.university_id == university_id
        ).filter(
            or_(
                Course.code.ilike(f'{query_upper}%'),
                Course.code.ilike(f'%{query_upper}%'), 
                Course.name.ilike(f'{query}%'),
                Course.name.ilike(f'%{query}%')
            )
        )
        
        if faculty_code:
            base_query = base_query.filter(
                Subject.faculty_associations.contains([faculty_code])
            )
        
        return base_query.order_by(
            case(
                (Course.code == query_upper, 1),
                (Course.code.ilike(f'{query_upper}%'), 2),
                (Course.name.ilike(f'{query}%'), 3), 
                else_=4
            ),
            Course.code,
            Course.name
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
                         errors_count: int = 0, error_details: Optional[Dict] = None):
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
