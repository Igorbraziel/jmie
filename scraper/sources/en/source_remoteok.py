from scraper.base_scraper import BaseScraper
from scraper.sources.en.remoteok_config import RemoteOkSearchParams

from typing import List, Dict, Any

from pprint import pprint

class RemoteOkScraper(BaseScraper):
    REMOTE_OK_API_URL = "https://remoteok.com/api"
    CUSTOM_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    def __init__(self, source_name: str, source_language: str):
        super().__init__(source_name, source_language)

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

        raw_data = response.json()
        jobs_list = raw_data[1:]

        pprint(jobs_list[0])
        print(f"✅ Successfully fetched {len(jobs_list)} jobs from Remote OK!")
        return jobs_list

    def parse(self, content: dict) -> List[Dict[str, Any]]:
        """Parse the JSON content."""
        parsed_jobs = []
        for job in content:
            pass

if __name__ == "__main__":
    remote_ok_scraper = RemoteOkScraper(source_name="Remote.ok EN", source_language="en")
    brazil_search_params = RemoteOkSearchParams(
        tags=["python"],
        location="brazil"
    )
    remote_ok_scraper.fetch(brazil_search_params)
