from scraper.base_scraper import BaseScraper
from typing import List, Dict, Any


class LinkedInScraper(BaseScraper):
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_ENDPOINT_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    def __init__(self, source_name: str, source_language: str):
        super().__init__(source_name, source_language)
        
    
    def fetch(self, keyword: str | None = None) -> str:
        """Fetch raw HTML or JSON from the job board."""
        # 3. Work Type (Remote vs. On-Site)

        # f_WT: Filters by the work model. You can comma-separate them (e.g., "2,3" for remote and hybrid).

        # 1 = On-site

        # 2 = Remote

        # 3 = Hybrid

        # 4. Experience Level

        # f_E: Filters by seniority.

        # 1 = Internship

        # 2 = Entry level

        # 3 = Associate

        # 4 = Mid-Senior level

        # 5 = Director

        # 6 = Executive
        query_params = {
            "keywords": keyword,
            "location": "United States",
            "geoId": "103644278", # geoId from US
            "start": 0, # First page
            "f_TPR": "r86400", # This means we will only get jobs from the past 24 hours
        }
        try:
            response = self.session.get(url=LinkedInScraper.BASE_URL, params=query_params, timeout=60)
            response.raise_for_status()

            html_data = response.text
            print(html_data, "url:", response.url)

        except Exception as e:
            print(f"Unexpected error while scraping from {self.source_name}. {e}")

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse the content into structured job posting dicts"""
        pass


if __name__ == "__main__":
    linkedin_scraper = LinkedInScraper(source_name="linkedin", source_language="EN")
    linkedin_scraper.fetch(keyword="data engineer")