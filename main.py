import json
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from api.endpoints import router as api_router
from database.models import db_manager

app = FastAPI(
    title="Multi-University Data API",
    description="API for course, faculty, subject and class schedules from multiple universities.",
    version="2.0.0",
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    db_manager.create_tables()

app.include_router(api_router)

# Legacy endpoints for backward compatibility (now deprecated)
def open_and_return(file_name):
    """
    Open the file and return what's in it.
    """
    try:
        with open(file_name, "r") as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        return {"error": "Data not found. Please use the new database-backed endpoints at /api/{university}/"}

@app.get("/", tags=["Endpoints"])
def endpoints():
    """
    All the available endpoints
    """
    return {
        "message": "Welcome to the Multi-University Data API",
        "new_endpoints": {
            "/api/{university}/faculties": "Get faculties for a university",
            "/api/{university}/subjects": "Get subjects for a university", 
            "/api/{university}/courses": "Get courses for a university (with pagination and search)",
            "/api/{university}/courses/{course_code}": "Get specific course details",
            "/api/{university}/exam_schedules": "Get exam schedules",
            "/api/{university}/scrape_all": "Trigger data scraping (POST)",
            "/api/{university}/sync_status": "Get synchronization status"
        },
        "supported_universities": ["ualberta"],
        "legacy_endpoints": {
            "note": "Legacy endpoints are deprecated. Please use /api/{university}/ endpoints instead.",
            "endpoints": [
                "/faculties",
                "/subjects", 
                "/courses"
            ]
        }
    }

# Legacy endpoints (deprecated but maintained for backward compatibility)
@app.get("/faculties", tags=["Legacy"], deprecated=True)
def get_faculties_legacy():
    """
    DEPRECATED: Use /api/ualberta/faculties instead
    """
    faculty_file = "data/ualberta/faculties.json"
    faculties = open_and_return(faculty_file)
    return [faculties]

@app.get("/faculties/{faculty_code}", tags=["Legacy"], deprecated=True)
def get_faculty_legacy(faculty_code: str):
    """
    DEPRECATED: Use /api/ualberta/faculties instead
    """
    faculty_file = "data/ualberta/faculties.json"
    faculties = open_and_return(faculty_file)
    if isinstance(faculties, dict) and "error" in faculties:
        return faculties
    faculty_code = faculty_code.upper()
    if faculty_code not in faculties:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculties[faculty_code]

@app.get("/subjects", tags=["Legacy"], deprecated=True)
def get_subjects_legacy():
    """
    DEPRECATED: Use /api/ualberta/subjects instead
    """
    subject_file = "data/ualberta/subjects.json"
    subjects = open_and_return(subject_file)
    return [subjects]

@app.get("/subjects/{subject_code}", tags=["Legacy"], deprecated=True)
def get_subject_legacy(subject_code: str):
    """
    DEPRECATED: Use /api/ualberta/subjects instead
    """
    subject_file = "data/ualberta/subjects.json"
    subjects = open_and_return(subject_file)
    if isinstance(subjects, dict) and "error" in subjects:
        return subjects
    if subject_code not in subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subjects[subject_code]

@app.get("/courses", tags=["Legacy"], deprecated=True)
def get_courses_legacy():
    """
    DEPRECATED: Use /api/ualberta/courses instead
    """
    course_file = "data/ualberta/courses.json"
    courses = open_and_return(course_file)
    return [courses]

@app.get("/courses/{course_code}", tags=["Legacy"], deprecated=True)
def get_course_legacy(course_code: str):
    """
    DEPRECATED: Use /api/ualberta/courses/{course_code} instead
    """
    course_file = "data/ualberta/courses.json"
    courses = open_and_return(course_file)
    if isinstance(courses, dict) and "error" in courses:
        return courses
    course_code = course_code.upper()
    if course_code not in courses:
        raise HTTPException(status_code=404, detail="Course not found. Make sure there is no space (e.g. CMPUT401 and not CMPUT 401)")
    return courses[course_code]

if __name__ == "__main__":
    port = int(os.getenv('API_PORT', 8000))
    host = os.getenv('API_HOST', '0.0.0.0')
    uvicorn.run(app, host=host, port=port)