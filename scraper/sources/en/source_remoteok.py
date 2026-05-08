
import re
from datetime import timezone, datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scraper.base_scraper import BaseScraper
from scraper.sources.en.remoteok_config import RemoteOkSearchParams, RemoteOkJob, RemoteOkCompany

from pprint import pprint

class RemoteOkScraper(BaseScraper):
    """Scraper for Remote OK website. It fetches job listings based on the provided search parameters, parses the job details, and returns structured data for both jobs and companies."""
    REMOTE_OK_API_URL = "https://remoteok.com/api"
    CUSTOM_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    def __init__(self, source_name: str, source_language: str):
        super().__init__(source_name, source_language)
        
    def _parse_html_description(self, description: str) -> str:
        """Parses the job description from HTML format to raw text

        Args:
            description (str): HTML text

        Returns:
            str: raw text parsed from HTML
        """
        fixed = description.encode("latin-1").decode("utf-8")
        
        soup = BeautifulSoup(fixed, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        
        text = re.sub(
            r"Please mention the word.*?they're human\.",
            "",
            text,
            flags=re.DOTALL
        )
        
        return "\n".join(line for line in text.splitlines() if line.strip())
        

    def fetch(self, search_params: RemoteOkSearchParams) -> List[Dict[str, Any]]:
        """Fetch jobs list from the Remote OK API."""
        response = self._safe_request(
            url=self.REMOTE_OK_API_URL,
            params=search_params.to_dict(),
            headers=self.CUSTOM_HEADERS,
            timeout=15,
            use_session=False,
        )
        if response is None:
            return []

        jobs_list = []
        raw_data = response.json()
        if raw_data:
            jobs_list = raw_data[1:]

        print(f"✅ Successfully fetched {len(jobs_list)} jobs from Remote OK!")
        return jobs_list

    def parse(self, content: Dict) -> Dict[str, Dict[str, RemoteOkJob | RemoteOkCompany]]:
        """Parse the JSON content."""
        description = content.get("description")
        parsed_description = self._parse_html_description(description)
        return {
            "job": RemoteOkJob(
                title=content.get("position"),
                description=parsed_description,
                url=content.get("url"),
                salary_min=content.get("salary_min"),
                salary_max=content.get("salary_max"),
                location=content.get("location"),
                job_type="REMOTE", # Standard for RemoteOK
                posted_date=content.get("date"),
                scraped_at=datetime.now(timezone.utc).isoformat(),
                source_name=self.source_name
            ),
            "company": RemoteOkCompany(
                name=content.get("company")
            )
        }
            
    def scrape_jobs_and_companies(self, search_params: RemoteOkSearchParams) -> Dict[str, List[RemoteOkJob | RemoteOkCompany]]:
        """Main workflow to scrape jobs and companies from Remote OK based on the search parameters provided.

        Args:
            search_params (RemoteOkSearchParams): The search parameters to filter the Remote OK API results.
            example: RemoteOkSearchParams(tags=["python"], location="brazil")

        Returns:
            Dict[str, List[RemoteOkJob | RemoteOkCompany]]: A dictionary containing the scraped jobs and companies.
        """
        final_jobs: List[Dict[str, Any]] = []
        companies: List[Dict[str, Any]] = []
        
        jobs_list = self.fetch(search_params)
        for job in jobs_list:
            response_dict = self.parse(job)
            remoteok_job: RemoteOkJob = response_dict.get("job")
            remoteok_company: RemoteOkCompany = response_dict.get("company")
            
            final_jobs.append(remoteok_job.to_dict())
            companies.append(remoteok_company.to_dict())
            
        return {
            "jobs": final_jobs,
            "companies": companies
        }
        

if __name__ == "__main__":
    remote_ok_scraper = RemoteOkScraper(source_name="Remote.ok EN", source_language="en")
    brazil_search_params = RemoteOkSearchParams(
        tags=["python"],
        location="brazil"
    )
    us_search_params = RemoteOkSearchParams(
        tags=["software"],
        location="usa"
    )
    
    # br = remote_ok_scraper.scrape_jobs_and_companies(brazil_search_params)
    # br_jobs = br.get("jobs")
    # br_companies = br.get("companies")
    
    us = remote_ok_scraper.scrape_jobs_and_companies(us_search_params)
    us_jobs = us.get("jobs")
    us_companies = us.get("companies")
    pprint(us_jobs[:3])
    pprint(us_companies[:3])
    
