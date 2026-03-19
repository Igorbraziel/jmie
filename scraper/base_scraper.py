import requests
from urllib3.util.retry import Retry

from abc import ABC, abstractmethod

from typing import List, Dict, Any

class BaseScraper(ABC):
    """Abtract class for all job board scrapers"""
    def __init__(self, source_name: str, source_language: str):
        self.source_name = source_name
        self.source_language = source_language
        self.session = self._create_resilient_session()

    def get_source_info(self):
        pass

    @staticmethod
    def _create_resilient_session() -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            allowed_methods=['GET'],
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)

        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    @abstractmethod
    def fetch(self, keyword: str | None = None) -> List[str]:
        """Fetch raw HTML or JSON from the job board. Must return list of page contents."""
        pass

    @abstractmethod
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse the content into structured job posting dicts"""
        pass


    def scrape(self):
        """Main operation. Return the extracted jobs in the right format"""
        try:
            raw_content = self.fetch()
            jobs = []
            for content in raw_content:
                job_list = self.parse(content)
                jobs.extend(job_list)
            return self._normalize(jobs)
        except Exception as e:
            print(f'Error: {e}\n while scraping from source: {self.source_name}, language: {self.source_language}')
            return []

    def _normalize(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "source_id": self.source_id,
                "company_id": job.get("company_id"),
                "title": job.get("title"),
                "description": job.get("description"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "currency": job.get("currency"),
                "location": job.get("location"),
                "job_type": job.get("job_type"),
                "posted_date": job.get("posted_date"),
                "scraped_at": job.get("scraped_at"),
                "raw_data": job.get("raw_data"), 
            } for job in jobs
        ]