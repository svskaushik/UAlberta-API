from fastapi import APIRouter, HTTPException
from scrapers.registry import SCRAPER_REGISTRY

router = APIRouter()

@router.get("/api/{university}/faculties")
def get_faculties(university: str):
    scraper = SCRAPER_REGISTRY.get(university)
    if not scraper:
        raise HTTPException(status_code=404, detail="University not supported")
    faculties = scraper.get_faculties()
    return faculties

@router.get("/api/{university}/subjects")
def get_subjects(university: str):
    scraper = SCRAPER_REGISTRY.get(university)
    if not scraper:
        raise HTTPException(status_code=404, detail="University not supported")
    # Faculties are needed to get subjects
    faculties = scraper.get_faculties()
    subjects = scraper.get_subjects(faculties)
    return subjects

@router.get("/api/{university}/courses")
def get_courses(university: str):
    scraper = SCRAPER_REGISTRY.get(university)
    if not scraper:
        raise HTTPException(status_code=404, detail="University not supported")
    faculties = scraper.get_faculties()
    subjects = scraper.get_subjects(faculties)
    courses = scraper.get_courses(subjects)
    return courses

@router.get("/api/{university}/exam_schedules")
def get_exam_schedules(university: str):
    scraper = SCRAPER_REGISTRY.get(university)
    if not scraper:
        raise HTTPException(status_code=404, detail="University not supported")
    exam_schedules = scraper.get_exam_schedules()
    return exam_schedules

@router.post("/api/{university}/scrape_all")
def scrape_all(university: str):
    scraper = SCRAPER_REGISTRY.get(university)
    if not scraper:
        raise HTTPException(status_code=404, detail="University not supported")
    result = scraper.scrape_all()
    return result
