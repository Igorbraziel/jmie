import time
import random
from typing import List, Dict, Any
from datetime import datetime, timezone

from scraper.base_scraper import BaseScraper
from scraper.sources.multi_language.linkedin_config import LinkedInSearchParams, LinkedInJob, LinkedInCompany, Location, GeoId, TimePosted, WorkType, ExperienceLevel

from bs4 import BeautifulSoup
from requests.exceptions import Timeout, ConnectionError, HTTPError, RequestException

class LinkedInScraper(BaseScraper):
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_ENDPOINT_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/"

    def __init__(self, source_name: str, source_language: str):
        super().__init__(source_name, source_language)

    def _parse_job_overview_html(self, html_content: str, job_url: str) -> Dict[str, Dict[str, Any]] | None:
        soup = BeautifulSoup(html_content, 'html.parser')

        title_element = soup.find('h2', class_='top-card-layout__title')
        title = title_element.text.strip() if title_element else ""
    
        description_element = soup.find('div', class_='show-more-less-html__markup')
        description = description_element.get_text(separator='\n').strip() if description_element else ""

        if not description:
            return None

        company_element = soup.find('a', class_='topcard__org-name-link')
        company_name = company_element.text.strip() if company_element else ""

        location_element = soup.find('span', class_='topcard__flavor--bullet')
        location = location_element.text.strip() if location_element else ""

        posted_element = soup.find('span', class_='posted-time-ago__text')
        posted_time_raw = posted_element.text.strip() if posted_element else None

        job_type = None
        industry = None

        criteria_items = soup.find_all('li', class_='description__job-criteria-item')

        for item in criteria_items:
            header_element = item.find('h3', class_='description__job-criteria-subheader')
            value_element = item.find('span', class_='description__job-criteria-text')

            if header_element and value_element:
                header = header_element.text.strip().lower()
                value = value_element.text.strip()

                if 'employment type' in header:
                    job_type = value
                elif 'industries' in header:
                    industry = value

        return {
            "job": LinkedInJob(
                title=title,
                description=description,
                url=job_url,
                location=location,
                job_type=job_type,
                scraped_at=datetime.now(timezone.utc).isoformat(),
                posted_time_raw=posted_time_raw, # It is a raw string ('1 hour ago' for example)
                source_name=self.source_name
            ),
            "company": LinkedInCompany(
                name=company_name,
                industry=industry 
            )
        }

    def scrape_jobs_and_companies(self, search_params: LinkedInSearchParams) -> Dict[str, List[LinkedInJob | LinkedInCompany]]:
        """Perform the entire scrape and return the jobs and companies in the right format."""
        html_content = self.fetch(search_params)
        job_ids = self.parse(html_content)

        job_list = []
        company_list = []

        for job_id in job_ids:
            time.sleep(random.uniform(2.0, 4.0))

            job_overview_url = LinkedInScraper.JOB_ENDPOINT_URL + job_id
            response = self.session.get(job_overview_url)

            html_content = response.text

            response_dict = self._parse_job_overview_html(html_content, job_url=job_overview_url)
            if not response_dict:
                continue

            linkedin_job = response_dict.get("job")
            linkedin_company = response_dict.get("company")
            
        
            job_list.append(linkedin_job.to_dict())
            company_list.append(linkedin_company.to_dict())

        return {
            "jobs": job_list,
            "companies": company_list
        }
        
    def fetch(self, search_params: LinkedInSearchParams) -> str:
        """Fetch raw HTML or JSON from the job board."""
        try:
            response = self.session.get(url=LinkedInScraper.BASE_URL, params=search_params.to_dict(), timeout=60)
            response.raise_for_status()
            print(f"HTML content successfully fetched from LinkedIn!")
            return response.text

        except Timeout:
            print("⏱️ Timeout Error: The job board took too long to respond.")
            return []

        except ConnectionError:
            print("🔌 Connection Error: Could not connect to the server.")
            return []

        except HTTPError as http_err:
            status_code = http_err.response.status_code
            print(f"🌐 HTTP Error {status_code}: {http_err}")    
            return []

        except RequestException as req_err:
            print(f"⚠️ Critical Request Error: {req_err}")
            return []

        except Exception as e:
            print(f"🐛 Unexpected System Error: {e}")
            return []

    def parse(self, html_content: str) -> List[str]:
        """Parse the HTML content."""
        job_ids = []
        soup = BeautifulSoup(html_content, 'html.parser')

        job_cards = soup.find_all('a', class_='base-card__full-link')
        
        for card in job_cards:
            try:
                href = card.get('href')

                if not href or not isinstance(href, str):
                    continue

                clean_url = href.split('?')[0]
                job_id = clean_url.split('-')[-1]

                if job_id.isdigit():
                    job_ids.append(job_id)
                else:
                    print(f"⚠️ Skipped invalid ID: {job_id}")

            except Exception as e:
                print(f"Error parsing job card: {e}")
        
        print(f"Found {len(job_ids)} job IDs.")
        return job_ids


if __name__ == "__main__":
    linkedin_us_scraper = LinkedInScraper(source_name="LinkedIn EN", source_language="en")
    us_search_params = LinkedInSearchParams(
        keywords="data engineer",
        location=Location.UNITED_STATES.value,
        geoId=GeoId.UNITED_STATES.value
    )

    linkedin_br_scraper = LinkedInScraper(source_name="LinkedIn PT", source_language="pt")
    br_search_params = LinkedInSearchParams(
        keywords='"engenheiro de dados" OR "data engineer"',
        location=Location.BRAZIL.value,
        geoId=GeoId.BRAZIL.value
    )

    linkedin_us_scraper.scrape_jobs_and_companies(us_search_params)
    linkedin_br_scraper.scrape_jobs_and_companies(br_search_params)




