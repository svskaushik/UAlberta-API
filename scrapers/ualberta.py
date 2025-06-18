import requests
import json
import re
from bs4 import BeautifulSoup as bs
from time import sleep
from tqdm import tqdm
from .base import BaseScraper
from typing import Optional
from bs4.element import Tag

ROOT_URL = "https://apps.ualberta.ca"
MAIN_URL = "https://apps.ualberta.ca/catalogue"
EXAM_URL = "https://www.ualberta.ca/api/datalist/spreadsheet/1kM0k0LenS9Z9LFH6F9qfbr7lyThRa0phTadDCs_MA-c/Sheet1"
DELAY_TIME = 2

class UAlbertaScraper(BaseScraper):
    def __init__(self):
        self.session = requests.Session()
        self.data_dir = './data/ualberta/'

    def write_to_file(self, name_of_file, data):
        with open(f'{self.data_dir}{name_of_file}.json', 'w') as file:
            json.dump(data, file)

    def get_faculties(self):
        catalog_page = self.session.get(MAIN_URL).text
        course_soup = bs(catalog_page, 'lxml')
        faculty_div = course_soup.find('div', {'class': 'col col-md-6 col-lg-5 offset-lg-2'})
        if not isinstance(faculty_div, Tag):
            return {}
        faculties = faculty_div.find_all('li') if hasattr(faculty_div, 'find_all') else []
        faculty_data = dict()
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
            faculty_data[faculty_code] = {
                "faculty_name": faculty_name,
                "faculty_link": faculty_link
            }
        self.write_to_file('faculties', faculty_data)
        return faculty_data

    def get_subjects(self, faculty_data):
        subject_data = dict()
        for faculty_code, faculty_value in tqdm(faculty_data.items(), desc="Processing faculties for subjects"):
            sleep(DELAY_TIME)
            faculty_link = faculty_data[faculty_code]["faculty_link"]
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
                    subject_data[subject_code] = {}
                    subject_data[subject_code]["name"] = subject_name
                    subject_data[subject_code]['link'] = subject_link
                    subject_data[subject_code]['faculties'] = []
                except ValueError:
                    continue
                except Exception:
                    continue
        for faculty_code, faculty_value in tqdm(faculty_data.items(), desc="Associating subjects with faculties"):
            sleep(DELAY_TIME)
            faculty_link = faculty_data[faculty_code]["faculty_link"]
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
                subject_title, subject_link = [str(subject_a.text), subject_a.get('href')]
                if ' - ' not in subject_title:
                    continue
                subject_code, subject_name = subject_title.split(' - ', 1)
                subject_link = ROOT_URL + subject_link
                subject_data[subject_code]["name"] = subject_name
                subject_data[subject_code]["link"] = subject_link
                subject_data[subject_code]["faculties"].append(faculty_code)
        self.write_to_file('subjects', subject_data)
        return subject_data

    def get_courses(self, subject_data):
        course_data = dict()
        for subject_code, values in tqdm(subject_data.items(), desc="Processing subjects for courses"):
            sleep(DELAY_TIME)
            subject_url = subject_data[subject_code]["link"]
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
                a_tag = course.find('a') if hasattr(course, 'find') else None
                href = a_tag.get('href') if isinstance(a_tag, Tag) and a_tag.get('href') else None
                course_link = ROOT_URL + str(href) if isinstance(href, str) else None
                b_tag = course.find('b') if hasattr(course, 'find') else None
                course_weight = b_tag.text[2:][:2].strip() if isinstance(b_tag, Tag) and hasattr(b_tag, 'text') else None
                try:
                    course_fee_index = b_tag.text[2:].split('fi')[1].split(')')[0].strip() if isinstance(b_tag, Tag) and hasattr(b_tag, 'text') else None
                except:
                    course_fee_index = None
                # course_schedule extraction
                course_schedule = None
                if courses and isinstance(courses[0], Tag):
                    b_tag0 = courses[0].find('b') if hasattr(courses[0], 'find') else None
                    if isinstance(b_tag0, Tag) and hasattr(b_tag0, 'text'):
                        try:
                            course_schedule = b_tag0.text[2:].split('fi')[1].split('(')[1].split(',')[0]
                        except:
                            course_schedule = None
                p_tag = course.find('p') if hasattr(course, 'find') else None
                try:            
                    course_description = p_tag.text.split('Prerequisite')[0] if isinstance(p_tag, Tag) and hasattr(p_tag, 'text') else "There is no available course description."
                except:
                    course_description = "There is no available course description."
                try:
                    course_hrs_for_lecture = b_tag.text[2:].split('fi')[1].split('(')[1].split(',')[1].split('-')[0].strip(' )') if isinstance(b_tag, Tag) and hasattr(b_tag, 'text') else None
                except:
                    course_hrs_for_lecture = None
                try:
                    course_hrs_for_seminar = b_tag.text[2:].split('fi')[1].split('(')[1].split(',')[1].split('-')[1] if isinstance(b_tag, Tag) and hasattr(b_tag, 'text') else None
                except:
                    course_hrs_for_seminar = None
                try:    
                    course_hrs_for_labtime = b_tag.text[2:].split('fi')[1].split('(')[1].split(',')[1].split('-')[2].strip(')') if isinstance(b_tag, Tag) and hasattr(b_tag, 'text') else None
                except:
                    course_hrs_for_labtime = None
                try:
                    course_prerequisites = p_tag.text.split('Prerequisite')[1] if isinstance(p_tag, Tag) and hasattr(p_tag, 'text') else None
                except:
                    course_prerequisites = None
                if course_code.split(' ')[1].startswith('1'):
                    course_type = 'Junior'
                else:
                    course_type = 'Senior'
                course_code = course_code.replace(" ", "")
                course_data[course_code] = {
                    'course_name': course_name,
                    'course_link': course_link,
                    'course_description': course_description,
                    'course_weight': course_weight,
                    'course_fee_index': course_fee_index,
                    'course_schedule': course_schedule,
                    'course_hrs_for_lecture': course_hrs_for_lecture,
                    'course_hrs_for_seminar': course_hrs_for_seminar,
                    'course_hrs_for_labtime': course_hrs_for_labtime,
                    'course_prerequisites': course_prerequisites
                }
        self.write_to_file('courses', course_data)
        return course_data

    def get_exam_schedules(self):
        response = self.session.get(EXAM_URL)
        if response.status_code == 200:
            exam_schedules = response.json()
            with open(f'{self.data_dir}exam_schedules.json', 'w') as file:
                json.dump(exam_schedules, file, indent=4)
            return exam_schedules
        else:
            return None

    def scrape_all(self):
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
