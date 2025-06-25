import requests
import json
import re
from bs4 import BeautifulSoup as bs
from time import sleep
from tqdm import tqdm
from typing import Optional, Dict, Any
from bs4.element import Tag
from datetime import datetime
from .base import BaseScraper
from database.models import get_db
from database.services import (
    UniversityService, FacultyService, SubjectService, 
    CourseService, ExamService, SyncService
)
import os

ROOT_URL = "https://apps.ualberta.ca"
MAIN_URL = "https://apps.ualberta.ca/catalogue"
EXAM_URL = "https://www.ualberta.ca/api/datalist/spreadsheet/1kM0k0LenS9Z9LFH6F9qfbr7lyThRa0phTadDCs_MA-c/Sheet1"
DELAY_TIME = int(os.getenv('SCRAPING_DELAY', 2))

class UAlbertaScraper(BaseScraper):
    def __init__(self):
        self.session = requests.Session()
        self.university_code = 'ualberta'
        self.university_name = 'University of Alberta'
        
    def _get_db_services(self):
        """Get database services"""
        db = next(get_db())
        return {
            'university': UniversityService(db),
            'faculty': FacultyService(db),
            'subject': SubjectService(db),
            'course': CourseService(db),
            'exam': ExamService(db),
            'sync': SyncService(db),
            'db': db
        }

    def get_faculties(self):
        """Scrape and store faculties in database"""
        services = self._get_db_services()
        try:
            # Get or create university
            university = services['university'].get_or_create_university(
                code=self.university_code,
                name=self.university_name,
                website_url="https://www.ualberta.ca",
                api_config={"base_url": ROOT_URL, "catalog_url": MAIN_URL}
            )
            
            # Start sync logging
            sync_log = services['sync'].log_sync_start(university.id, 'faculties')
            
            catalog_page = self.session.get(MAIN_URL).text
            course_soup = bs(catalog_page, 'lxml')
            faculty_div = course_soup.find('div', {'class': 'col col-md-6 col-lg-5 offset-lg-2'})
            
            if not isinstance(faculty_div, Tag):
                services['sync'].log_sync_complete(sync_log.id, 'failed', error_details={'error': 'Faculty div not found'})
                return {}
            
            faculties = faculty_div.find_all('li') if hasattr(faculty_div, 'find_all') else []
            faculty_data = {}
            processed_count = 0
            
            for faculty in tqdm(faculties, desc="Processing faculties"):
                if not isinstance(faculty, Tag):
                    continue
                sleep(DELAY_TIME)
                
                faculty_a = faculty.find('a') if hasattr(faculty, 'find') else None
                if not (isinstance(faculty_a, Tag) and hasattr(faculty_a, 'text') and hasattr(faculty_a, 'get')):
                    continue
                
                faculty_title, faculty_link = [str(faculty_a.text), faculty_a.get('href')]
                if ' - ' not in faculty_title:
                    continue
                
                faculty_code, faculty_name = faculty_title.split(' - ', 1)
                faculty_link = ROOT_URL + faculty_link
                
                # Store in database
                db_faculty = services['faculty'].upsert_faculty(
                    university_id=university.id,
                    code=faculty_code,
                    name=faculty_name,
                    website_url=faculty_link,
                    metadata={'scraped_at': str(datetime.utcnow())}
                )
                
                faculty_data[faculty_code] = {
                    "faculty_name": faculty_name,
                    "faculty_link": faculty_link,
                    "id": db_faculty.id
                }
                processed_count += 1
            
            services['sync'].log_sync_complete(sync_log.id, 'success', processed_count)
            return faculty_data
            
        except Exception as e:
            services['sync'].log_sync_complete(sync_log.id, 'failed', error_details={'error': str(e)})
            raise
        finally:
            services['db'].close()

    def get_subjects(self, faculty_data=None):
        """Scrape and store subjects in database"""
        services = self._get_db_services()
        try:
            university = services['university'].get_university_by_code(self.university_code)
            if not university:
                raise ValueError("University not found")
            
            if not faculty_data:
                faculty_data = self._get_faculty_data_from_db(services, university.id)
            
            sync_log = services['sync'].log_sync_start(university.id, 'subjects')
            subject_data = {}
            processed_count = 0
            
            for faculty_code, faculty_info in tqdm(faculty_data.items(), desc="Processing faculties for subjects"):
                sleep(DELAY_TIME)
                faculty_link = faculty_info["faculty_link"]
                faculty_page = self.session.get(faculty_link).text
                subject_soup = bs(faculty_page, 'lxml')
                
                content_div = subject_soup.find('div', {'class': 'content'})
                if not isinstance(content_div, Tag):
                    continue
                
                subject_div = content_div.find('div', {'class': 'container'}) if hasattr(content_div, 'find') else None
                if not isinstance(subject_div, Tag):
                    continue
                
                subject_div_list = subject_div.find('ul') if hasattr(subject_div, 'find') else None
                if not isinstance(subject_div_list, Tag):
                    continue
                
                subjects = subject_div_list.find_all('li') if hasattr(subject_div_list, 'find_all') else []
                
                for subject in subjects:
                    if not isinstance(subject, Tag):
                        continue
                    
                    subject_a = subject.find('a') if hasattr(subject, 'find') else None
                    if not (isinstance(subject_a, Tag) and hasattr(subject_a, 'text') and hasattr(subject_a, 'get')):
                        continue
                    
                    try:
                        subject_title, subject_link = [str(subject_a.text), subject_a.get('href')]
                        if ' - ' not in subject_title:
                            continue
                        
                        subject_code, subject_name = subject_title.split(' - ', 1)
                        subject_link = ROOT_URL + subject_link
                        
                        if subject_code not in subject_data:
                            # Store in database
                            db_subject = services['subject'].upsert_subject(
                                university_id=university.id,
                                code=subject_code,
                                name=subject_name,
                                website_url=subject_link,
                                faculty_associations=[faculty_code],
                                metadata={'scraped_at': str(datetime.utcnow())}
                            )
                            
                            subject_data[subject_code] = {
                                "name": subject_name,
                                "link": subject_link,
                                "faculties": [faculty_code],
                                "id": db_subject.id
                            }
                            processed_count += 1
                        else:
                            # Update faculty associations
                            if faculty_code not in subject_data[subject_code]["faculties"]:
                                subject_data[subject_code]["faculties"].append(faculty_code)
                                
                                # Update in database
                                services['subject'].upsert_subject(
                                    university_id=university.id,
                                    code=subject_code,
                                    name=subject_name,
                                    website_url=subject_link,
                                    faculty_associations=subject_data[subject_code]["faculties"],
                                    metadata={'scraped_at': str(datetime.utcnow())}
                                )
                    
                    except Exception as e:
                        continue
            
            services['sync'].log_sync_complete(sync_log.id, 'success', processed_count)
            return subject_data
            
        except Exception as e:
            services['sync'].log_sync_complete(sync_log.id, 'failed', error_details={'error': str(e)})
            raise
        finally:
            services['db'].close()

    def get_courses(self, subject_data=None):
        """Scrape and store courses in database"""
        services = self._get_db_services()
        try:
            university = services['university'].get_university_by_code(self.university_code)
            if not university:
                raise ValueError("University not found")
            
            if not subject_data:
                subject_data = self._get_subject_data_from_db(services, university.id)
            
            sync_log = services['sync'].log_sync_start(university.id, 'courses')
            course_data = {}
            processed_count = 0
            
            for subject_code, subject_info in tqdm(subject_data.items(), desc="Processing subjects for courses"):
                sleep(DELAY_TIME)
                subject_url = subject_info["link"]
                subject_page = self.session.get(subject_url).text 
                course_soup = bs(subject_page, 'lxml')
                courses = course_soup.find_all('div', class_='course first')
                
                for course in courses:
                    if not isinstance(course, Tag):
                        continue
                    
                    h2_tag = course.find('h2', class_='flex-grow-1') if hasattr(course, 'find') else None
                    if not (isinstance(h2_tag, Tag) and hasattr(h2_tag, 'text')):
                        continue
                    
                    h2_text = h2_tag.text.strip().split('\n')[0]
                    if ' - ' not in h2_text:
                        continue
                    
                    course_code, course_name = h2_text.split(' - ', 1)
                    
                    # Extract additional course data
                    a_tag = course.find('a') if hasattr(course, 'find') else None
                    href = a_tag.get('href') if isinstance(a_tag, Tag) and a_tag.get('href') else None
                    course_link = ROOT_URL + str(href) if isinstance(href, str) else None
                    
                    b_tag = course.find('b') if hasattr(course, 'find') else None
                    course_weight = b_tag.text[2:][:2].strip() if isinstance(b_tag, Tag) and hasattr(b_tag, 'text') else None
                    
                    p_tag = course.find('p') if hasattr(course, 'find') else None
                    try:            
                        course_description = p_tag.text.split('Prerequisite')[0] if isinstance(p_tag, Tag) and hasattr(p_tag, 'text') else "There is no available course description."
                    except:
                        course_description = "There is no available course description."
                    
                    try:
                        course_prerequisites = p_tag.text.split('Prerequisite')[1] if isinstance(p_tag, Tag) and hasattr(p_tag, 'text') else None
                    except:
                        course_prerequisites = None
                    
                    # Determine course level
                    level = 'junior' if course_code.split(' ')[1].startswith('1') else 'senior'
                    course_code_clean = course_code.replace(" ", "")
                    
                    # Store in database
                    db_course = services['course'].upsert_course(
                        university_id=university.id,
                        subject_id=subject_info["id"],
                        code=course_code_clean,
                        name=course_name,
                        description=course_description,
                        credit_hours=float(course_weight) if course_weight and course_weight.isdigit() else None,
                        level=level,
                        prerequisites=course_prerequisites,
                        website_url=course_link,
                        metadata={
                            'scraped_at': str(datetime.utcnow()),
                            'original_code': course_code
                        }
                    )
                    
                    course_data[course_code_clean] = {
                        'course_name': course_name,
                        'course_link': course_link,
                        'course_description': course_description,
                        'course_weight': course_weight,
                        'course_prerequisites': course_prerequisites,
                        'level': level,
                        'id': db_course.id
                    }
                    processed_count += 1
            
            services['sync'].log_sync_complete(sync_log.id, 'success', processed_count)
            return course_data
            
        except Exception as e:
            services['sync'].log_sync_complete(sync_log.id, 'failed', error_details={'error': str(e)})
            raise
        finally:
            services['db'].close()

    def get_exam_schedules(self):
        """Scrape and store exam schedules in database"""
        services = self._get_db_services()
        try:
            university = services['university'].get_university_by_code(self.university_code)
            if not university:
                raise ValueError("University not found")
            
            sync_log = services['sync'].log_sync_start(university.id, 'exam_schedules')
            
            response = self.session.get(EXAM_URL)
            if response.status_code == 200:
                exam_schedules = response.json()
                
                # Store raw exam data in university metadata for now
                # TODO: Parse and normalize exam data into proper course sections and exam schedules
                services['university'].get_or_create_university(
                    code=self.university_code,
                    name=self.university_name,
                    metadata={
                        'exam_schedules': exam_schedules,
                        'exam_schedules_updated_at': str(datetime.utcnow())
                    }
                )
                
                services['sync'].log_sync_complete(sync_log.id, 'success', len(exam_schedules) if isinstance(exam_schedules, list) else 1)
                return exam_schedules
            else:
                services['sync'].log_sync_complete(sync_log.id, 'failed', error_details={'error': f'HTTP {response.status_code}'})
                return None
                
        except Exception as e:
            services['sync'].log_sync_complete(sync_log.id, 'failed', error_details={'error': str(e)})
            raise
        finally:
            services['db'].close()

    def scrape_all(self):
        """Scrape all data and store in database"""
        faculty_data = self.get_faculties()
        subject_data = self.get_subjects(faculty_data)
        course_data = self.get_courses(subject_data)
        exam_schedules = self.get_exam_schedules()
        
        return {
            'faculties': faculty_data,
            'subjects': subject_data,
            'courses': course_data,
            'exam_schedules': exam_schedules
        }

    def _get_faculty_data_from_db(self, services, university_id):
        """Get faculty data from database"""
        faculties = services['faculty'].get_faculties_by_university(university_id)
        return {
            f.code: {
                "faculty_name": f.name,
                "faculty_link": f.website_url,
                "id": f.id
            }
            for f in faculties
        }

    def _get_subject_data_from_db(self, services, university_id):
        """Get subject data from database"""
        subjects = services['subject'].get_subjects_by_university(university_id)
        return {
            s.code: {
                "name": s.name,
                "link": s.website_url,
                "faculties": s.faculty_associations or [],
                "id": s.id
            }
            for s in subjects
        }
