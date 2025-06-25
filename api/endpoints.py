from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from scrapers.registry import SCRAPER_REGISTRY
from database.models import get_db, Course
from database.services import (
    UniversityService, FacultyService, SubjectService, 
    CourseService, ExamService, SyncService
)
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Response models
class FacultyResponse(BaseModel):
    id: int
    code: str
    name: str
    website_url: Optional[str] = None
    dean_info: Optional[dict] = None
    
    class Config:
        from_attributes = True

class SubjectResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    website_url: Optional[str] = None
    faculty_associations: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

class CourseResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    credit_hours: Optional[float] = None
    level: Optional[str] = None
    prerequisites: Optional[str] = None
    website_url: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.get("/api/{university}/faculties", response_model=List[FacultyResponse])
def get_faculties(university: str, db: Session = Depends(get_db)):
    university_service = UniversityService(db)
    faculty_service = FacultyService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Get faculties from database
    faculties = faculty_service.get_faculties_by_university(uni.id)
    return faculties

@router.get("/api/{university}/subjects", response_model=List[SubjectResponse])
def get_subjects(university: str, db: Session = Depends(get_db)):
    university_service = UniversityService(db)
    subject_service = SubjectService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Get subjects from database
    subjects = subject_service.get_subjects_by_university(uni.id)
    return subjects

@router.get("/api/{university}/courses", response_model=List[CourseResponse])
def get_courses(
    university: str, 
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    university_service = UniversityService(db)
    course_service = CourseService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Get courses from database
    if search:
        courses = course_service.search_courses(uni.id, search, limit)
    else:
        courses = course_service.get_courses_by_university(uni.id, limit, offset)
    
    return courses

@router.get("/api/{university}/courses/{course_code}", response_model=CourseResponse)
def get_course(university: str, course_code: str, db: Session = Depends(get_db)):
    university_service = UniversityService(db)
    course_service = CourseService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Get specific course
    course = db.query(Course).filter(
        Course.university_id == uni.id,
        Course.code == course_code.upper()
    ).first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return course

@router.get("/api/{university}/exam_schedules")
def get_exam_schedules(university: str, db: Session = Depends(get_db)):
    university_service = UniversityService(db)
    exam_service = ExamService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # For now, return exam data from university meta
    # TODO: Implement proper exam schedule parsing and storage
    if uni.meta and 'exam_schedules' in uni.meta:
        return uni.meta['exam_schedules']
    
    return []

@router.post("/api/{university}/scrape_all")
def scrape_all(university: str, db: Session = Depends(get_db)):
    scraper = SCRAPER_REGISTRY.get(university)
    if not scraper:
        raise HTTPException(status_code=404, detail="University not supported")
    
    try:
        result = scraper.scrape_all()
        
        # Get sync logs for this operation
        university_service = UniversityService(db)
        sync_service = SyncService(db)
        uni = university_service.get_university_by_code(university)
        
        if uni:
            recent_syncs = sync_service.get_recent_syncs(uni.id, 5)
            result['sync_logs'] = [
                {
                    'data_type': log.data_type,
                    'status': log.sync_status,
                    'records_processed': log.records_processed,
                    'started_at': log.started_at,
                    'completed_at': log.completed_at
                }
                for log in recent_syncs
            ]
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@router.get("/api/{university}/sync_status")
def get_sync_status(university: str, db: Session = Depends(get_db)):
    university_service = UniversityService(db)
    sync_service = SyncService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Get recent sync logs
    recent_syncs = sync_service.get_recent_syncs(uni.id, 10)
    
    return {
        'university': university,
        'recent_syncs': [
            {
                'id': log.id,
                'data_type': log.data_type,
                'status': log.sync_status,
                'records_processed': log.records_processed,
                'errors_count': log.errors_count,
                'started_at': log.started_at,
                'completed_at': log.completed_at,
                'error_details': log.error_details
            }
            for log in recent_syncs
        ]
    }
