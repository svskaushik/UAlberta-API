import requests
import json
import re
from bs4 import BeautifulSoup as bs
from time import sleep, time
from tqdm import tqdm
from typing import Optional
from bs4.element import Tag


ROOT_URL = "https://apps.ualberta.ca"
MAIN_URL = "https://apps.ualberta.ca/catalogue"
LOGIN_URL = "https://login.ualberta.ca/module.php/core/loginuserpass.php"
EXAM_URL = "https://www.ualberta.ca/api/datalist/spreadsheet/1kM0k0LenS9Z9LFH6F9qfbr7lyThRa0phTadDCs_MA-c/Sheet1"
DELAY_TIME = 2

session = requests.Session()

def write_to_file(name_of_file, data):
    """
    Writes scraped data a json file.
    """
    print(f"Writing data to {name_of_file}.json...")
    with open(f'./data/{name_of_file}.json', 'w') as file:
        json.dump(data, file)
    print(f"Data successfully written to {name_of_file}.json")


def get_faculties():
    """
    Returns the faculties offered at the university in the following format:
    {AR :  ['Faculty of Arts', 'https://apps.ualberta.ca/catalogue/faculty/ar'], 
    AU :  ['Augustana Faculty', 'https://apps.ualberta.ca/catalogue/faculty/au']}
    """
    print("Fetching faculties...")
    catalog_page = session.get(MAIN_URL).text
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
    write_to_file('faculties', faculty_data)
    print(f"Fetched {len(faculty_data)} faculties")
    return faculty_data


def get_subjects(faculty_data):
    """
    Gets the subjects available from the different faculties.
    Key   :  Value
    WKEXP :  {'name': 'Work Experience', 
               'link': 'https://apps.ualberta.ca/catalogue/course/wkexp', 
               'faculties': ['AH', 'AR', 'BC', 'EN', 'SC']}
    """
    print("Fetching subjects...")
    subject_data = dict()

    for faculty_code, faculty_value in tqdm(faculty_data.items(), desc="Processing faculties for subjects"):
        sleep(DELAY_TIME)
        faculty_link = faculty_data[faculty_code]["faculty_link"]
        faculty_page = session.get(faculty_link).text
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
        faculty_page = session.get(faculty_link).text
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
    write_to_file('subjects', subject_data)
    print(f"Fetched {len(subject_data)} subjects")
    return subject_data


def get_courses(subject_data):
    """
    Gets the courses in the different subjects of the different faculties.
    """
    print("Fetching courses...")
    course_data = dict()

    for subject_code, values in tqdm(subject_data.items(), desc="Processing subjects for courses"):
        sleep(DELAY_TIME)
        subject_url = subject_data[subject_code]["link"]
        subject_page = session.get(subject_url).text 
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
    write_to_file('courses', course_data)
    print(f"Fetched {len(course_data)} courses")
    return course_data


def get_class_schedules(course_data):
    """
    Get the class schedules for a specific course in the different terms.
    """
    print("Fetching class schedules...")
    class_schedules = dict()

    for course_code, values in tqdm(course_data.items(), desc="Processing courses for class schedules"):
        sleep(DELAY_TIME)
        course_url = course_data[course_code]["course_link"]
        course_page = session.get(course_url).text 
        course_soup = bs(course_page, 'lxml')
        terms = course_soup.find_all('div', id='content-nav', class_='nav flex-nowrap')
        print(f"Processing {course_code} at {course_url}")
        class_schedules[course_code] = {}

        for term in terms:
            try:
                a_tag = term.find('a', class_='nav-link active') if hasattr(term, 'find') else None
                term_code = a_tag.text.strip() if isinstance(a_tag, Tag) and hasattr(a_tag, 'text') else None
                if not term_code:
                    print(f"No terms found for {course_code}")
                    continue
                term_code = term_code.replace(" Term ", "")  # Condensed Name: "Winter Term 2025" --> "Winter2025"
                print(f"Processing {term_code} for {course_code}")
            except Exception as e:
                print(f"No terms found for {course_code}")
                continue

            class_schedules[course_code][term_code] = {}
            class_types = course_soup.find_all('div', class_='mb-5')
            print(f"Found {len(class_types)} class types for {course_code} in {term_code}")

            for class_type in class_types:
                try:
                    h3_tag = class_type.find('h3') if hasattr(class_type, 'find') else None
                    class_type_name = h3_tag.text.strip() if isinstance(h3_tag, Tag) and hasattr(h3_tag, 'text') else None
                    if not class_type_name:
                        print(f"No class type name found for {course_code} in {term_code}")
                        continue
                except AttributeError:
                    print(f"No class type name found for {course_code} in {term_code}")
                    continue
                class_schedules[course_code][term_code][class_type_name] = []

                offered_classes = class_type.find_all('tr', attrs={'data-card-title': True}) if hasattr(class_type, 'find_all') else []

                for classes in offered_classes:
                    class_info = {}

                    section_td = classes.find('td', attrs={'data-card-title': 'Section'}) if hasattr(classes, 'find') else None
                    section_info = section_td.text.strip().split('\n') if isinstance(section_td, Tag) and hasattr(section_td, 'text') else []
                    class_code = section_info[-1].strip("()") if section_info else ''
                    class_name = section_info[0].strip() if section_info else ''

                    capacity_td = classes.find('td', attrs={'data-card-title': 'Capacity'}) if hasattr(classes, 'find') else None
                    capacity = capacity_td.text.strip() if isinstance(capacity_td, Tag) and hasattr(capacity_td, 'text') else ''

                    class_times_td = classes.find('td', attrs={'data-card-title': 'Class times'}) if hasattr(classes, 'find') else None
                    class_times = class_times_td.text.strip() if isinstance(class_times_td, Tag) and hasattr(class_times_td, 'text') else ''

                    date_pattern = r"(\d{4}-\d{2}-\d{2})"
                    time_pattern = r"(\d{2}:\d{2})"
                    try:
                        start_date, end_date = re.findall(date_pattern, class_times)
                    except:
                        start_date, end_date = ['NA', 'NA']
                    try:
                        start_time, end_time = re.findall(time_pattern, class_times)
                    except:
                        start_time, end_time = ['NA', 'NA']

                    days_pattern = r"\((.*?)\)"
                    days_match = re.search(days_pattern, class_times)
                    days = days_match.group(1) if days_match else 'NA'

                    class_info["class_code"] = class_code
                    class_info["class_name"] = class_name
                    class_info["capacity"] = capacity
                    class_info["days"] = days
                    class_info["start_date"] = start_date
                    class_info["end_date"] = end_date
                    class_info["start_time"] = start_time
                    class_info["end_time"] = end_time
                    class_info["room"] = 'Login to view Instructor(s) and Location'  # Placeholder as room info is behind a login

                    class_schedules[course_code][term_code][class_type_name].append(class_info)

    write_to_file('class_schedules', class_schedules)
    print("Class schedules fetching completed")

def get_exam_schedules():
    """
    Get the exam schedules for a specific course in the different terms and save them to a file.
    """
    print("Fetching exam schedules...")
    
    # Make a GET request to the URL
    response = session.get(EXAM_URL)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        exam_schedules = response.json()
        
        # Save the data to a file
        with open('exam_schedules.json', 'w') as file:
            json.dump(exam_schedules, file, indent=4)
        
        print("Exam schedules saved to exam_schedules.json")
    else:
        print("Failed to fetch exam schedules. Status code:", response.status_code)



def main():
    start_time = time()
    
    print("Starting scraping process...")
    
    print("Scraping Faculties...")
    faculty_data = get_faculties()

    print("Scraping Subjects...")
    subject_data = get_subjects(faculty_data)

    print("Scraping Courses...")
    course_data = get_courses(subject_data)

    print("Scraping exam schedules...")
    exam_schedules = get_exam_schedules()
    
    #print("Scraping Class Schedules...")
    #class_schedules = get_class_schedules(course_data)
    
    end_time = time()
    print(f"Scraping completed. Total time taken: {end_time - start_time:.2f} seconds")
    print("Check the data folder for scraped data.")


if __name__ == "__main__":
    main()