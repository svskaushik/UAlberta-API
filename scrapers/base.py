from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    def get_faculties(self):
        pass

    @abstractmethod
    def get_courses(self):
        pass

    @abstractmethod
    def get_subjects(self):
        pass

    @abstractmethod
    def get_exam_schedules(self):
        pass

    @abstractmethod
    def scrape_all(self):
        """Scrape and update all data files for this university."""
        pass
