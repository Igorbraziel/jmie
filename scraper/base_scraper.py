import requests
import random
from urllib3.util.retry import Retry

from abc import ABC, abstractmethod

from typing import List, Dict, Any

class BaseScraper(ABC):
    """Abtract class for all job board scrapers"""
    def __init__(self, source_name: str, source_language: str):
        self.source_name = source_name
        self.source_language = source_language
        self.session = self._create_resilient_session()

    @staticmethod
    def _create_resilient_session() -> requests.Session:
        session = requests.Session()

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
        ]

        session.headers.update({
            "User-Agent": random.choice(user_agents),
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        })
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            allowed_methods=['GET'],
            status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True
        )

        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)

        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    @abstractmethod
    def fetch(self, search_params: Any) -> Any:
        """Fetch raw HTML or JSON from the job board."""
        pass

    @abstractmethod
    def parse(self, html_content: str) -> Any:
        """Parse the HTML content."""
        pass