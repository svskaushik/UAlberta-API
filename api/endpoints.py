from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
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
class CourseSummaryResponse(BaseModel):
    """Lightweight course response for dropdowns and listings"""
    id: int
    code: str
    name: str
    
    class Config:
        from_attributes = True

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

@router.get("/api/{university}/courses")
def get_courses(
    university: str, 
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    summary: bool = Query(False, description="Return only essential fields (id, code, name) for better performance"),
    db: Session = Depends(get_db)
) -> Union[List[CourseSummaryResponse], List[CourseResponse]]:
    university_service = UniversityService(db)
    course_service = CourseService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Get courses from database
    if summary:
        # Use optimized queries for summary mode
        if search:
            courses = course_service.search_courses_summary(uni.id, search, limit)
        else:
            courses = course_service.get_courses_summary_by_university(uni.id, limit, offset)
        # Convert query results to CourseSummaryResponse format
        return [CourseSummaryResponse(id=row[0], code=row[1], name=row[2]) for row in courses]
    else:
        # Use full queries for detailed mode
        if search:
            courses = course_service.search_courses(uni.id, search, limit)
        else:
            courses = course_service.get_courses_by_university(uni.id, limit, offset)
        # Convert Course objects to CourseResponse
        return [CourseResponse.model_validate(course) for course in courses]

@router.get("/api/{university}/courses/search", response_model=List[CourseSummaryResponse])
def search_courses_for_dropdown(
    university: str,
    q: str = Query(..., min_length=1, description="Search query for course code or name"),
    faculty_code: Optional[str] = Query(None, description="Filter by faculty code"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Optimized endpoint for course search in dropdowns.
    Returns only essential fields (id, code, name) for better performance.
    Supports filtering by faculty for more targeted results.
    """
    university_service = UniversityService(db)
    course_service = CourseService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Search courses with optimized query and optional faculty filter
    if faculty_code:
        courses = course_service.search_courses_summary_by_faculty(uni.id, q, faculty_code, limit)
    else:
        courses = course_service.search_courses_summary(uni.id, q, limit)
    
    # Convert query results to CourseSummaryResponse format
    return [CourseSummaryResponse(id=row[0], code=row[1], name=row[2]) for row in courses]

@router.get("/api/{university}/courses/search/optimized", response_model=List[CourseSummaryResponse])
def search_courses_optimized(
    university: str,
    q: str = Query(..., min_length=1, description="Search query for course code or name"),
    faculty_code: Optional[str] = Query(None, description="Filter by faculty code"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Enhanced course search with intelligent ranking and relevance scoring.
    Prioritizes exact matches, then prefix matches, then partial matches.
    Returns results ordered by relevance for better user experience.
    """
    university_service = UniversityService(db)
    course_service = CourseService(db)
    
    # Get university
    uni = university_service.get_university_by_code(university)
    if not uni:
        raise HTTPException(status_code=404, detail="University not supported")
    
    # Use optimized search methods with relevance ranking
    if faculty_code:
        courses = course_service.search_courses_summary_by_faculty_optimized(uni.id, q, faculty_code, limit)
    else:
        courses = course_service.search_courses_summary_optimized(uni.id, q, limit)
    
    # Convert query results to CourseSummaryResponse format
    return [CourseSummaryResponse(id=row[0], code=row[1], name=row[2]) for row in courses]

# Cache management endpoints
@router.get("/api/admin/cache/stats")
def get_cache_stats():
    """Get cache performance statistics"""
    try:
        from utils.cache import course_search_cache
        return {
            "memory_cache": course_search_cache.get_stats(),
            "cache_enabled": True
        }
    except ImportError:
        return {
            "memory_cache": {"error": "Cache not available"},
            "cache_enabled": False
        }

@router.post("/api/admin/cache/clear")
def clear_cache():
    """Clear all cached search results"""
    try:
        from utils.cache import course_search_cache
        course_search_cache.clear()
        return {"message": "Cache cleared successfully"}
    except ImportError:
        return {"message": "Cache not available"}

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
