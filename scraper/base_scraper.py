import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import Timeout, ConnectionError, HTTPError, RequestException
from typing import Optional
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

        adapter = HTTPAdapter(max_retries=retry_strategy)

        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return session

    def _safe_request(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Dict | None = None,
        headers: Dict | None = None,
        timeout: int = 15,
        use_session: bool = True,
    ) -> Optional[requests.Response]:
        """
        Execute an HTTP request with standardised error handling.

        Args:
            url:         Target URL.
            method:      HTTP verb (default ``GET``).
            params:      Query-string parameters.
            headers:     Extra request headers.
            timeout:     Request timeout in seconds (default 15).
            use_session: Use ``self.session`` when ``True`` (default),
                         otherwise use a plain ``requests`` call.

        Returns:
            The :class:`requests.Response` object on success, or ``None``
            if any network / HTTP error occurs.
        """
        requester = self.session if use_session else requests
        try:
            response = requester.request(
                method, url, params=params, headers=headers, timeout=timeout
            )
            response.raise_for_status()
            return response

        except Timeout:
            print(f"⏱️  Timeout Error: {url} took too long to respond.")
        except ConnectionError:
            print(f"🔌 Connection Error: Could not connect to {url}.")
        except HTTPError as http_err:
            status_code = http_err.response.status_code
            print(f"🌐 HTTP Error {status_code}: {http_err}")
        except RequestException as req_err:
            print(f"⚠️  Critical Request Error: {req_err}")
        except Exception as exc:
            print(f"🐛 Unexpected System Error: {exc}")

        return None

    @abstractmethod
    def fetch(self, search_params: Any) -> Any:
        """Fetch raw HTML or JSON from the job board."""
        pass

    @abstractmethod
    def parse(self, content: str | Dict) -> Any:
        """Parse the HTML or JSON content."""
        pass

    @abstractmethod
    def scrape_jobs_and_companies(self, search_params: Any) -> Any:
        """The main flow of execution"""
        pass