from datetime import datetime, timezone
from typing import Any, List, Dict

from scraper.base_scraper import BaseScraper
from scraper.sources.pt.gupy_config import GupySearchParams, GupyJob, GupyCompany

from pprint import pprint

class GupyScraper(BaseScraper):
    GUPY_API_URL = "https://employability-portal.gupy.io/api/v1/jobs"

    def __init__(self):
        super().__init__("Gupy PT", "pt")

    def fetch(self, search_params: GupySearchParams) -> List[Dict[str, Any]]:
        """Fetch raw JSON data from the Gupy job board."""
        response = self._safe_request(
            self.GUPY_API_URL,
            params=search_params.to_dict(),
        )
        json_data = response.json()
        return json_data["data"]

    def parse(self, content: Dict) -> Any:
        """Parse the JSON content."""
        city = content.get("city", "").strip()
        country = content.get("country", "").strip()

        if city:
            location = f"{city} / {country}"
        else:
            location = country

        return {
            "job": GupyJob(
                title=content.get("name", "").strip(),
                description=content.get("description", "").strip(),
                url=content.get("jobUrl", "").strip(),
                location=location,
                job_type=content.get("workplaceType", "").strip(),
                posted_date=content.get("publishedDate", "").strip(),
                scraped_at=datetime.now(timezone.utc).isoformat() 
            ),
            "company": GupyCompany(
                name=content.get("careerPageName", "").strip(),
                website=content.get("careerPageUrl", "").strip()
            )
        }

    def scrape_jobs_and_companies(self, search_params: GupySearchParams) -> Dict[str, List[GupyJob | GupyCompany]]:
        """Main workflow to scrape jobs and companies from Gupy based on the search parameters provided."""
        jobs: List[Dict[str, Any]] = []
        companies: List[Dict[str, Any]] = []
        scraped_list = self.fetch(search_params)

        for content in scraped_list:
            response_dict = self.parse(content)

            gupy_job = response_dict.get("job")
            gupy_company = response_dict.get("company")

            jobs.append(gupy_job.to_dict())
            companies.append(gupy_company.to_dict())

        return {
            "jobs": jobs,
            "companies": companies
        }

if __name__ == "__main__":
    gupy_scraper = GupyScraper()
    search_params = GupySearchParams(jobName="data engineer", limit=10)
    
    response = gupy_scraper.scrape_jobs_and_companies(search_params)
    jobs = response.get("jobs")
    companies = response.get("companies")

    pprint(jobs[-1])
    pprint(companies[-1])