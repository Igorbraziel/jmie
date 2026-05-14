from typing import List, Dict, Any
from scraper.sources.en.source_remoteok import RemoteOkScraper
from scraper.sources.en.remoteok_config import RemoteOkSearchParams
from scraper.sources.pt.source_gupy import GupyScraper
from scraper.sources.pt.gupy_config import GupySearchParams
from scraper.sources.multi_language.source_linkedin import LinkedInScraper
from scraper.sources.multi_language.linkedin_config import LinkedInSearchParams

class ScraperOrchestrator:
    """
    Orchestrator for managing and executing specialized job scrapers.
    Each job board has its own dedicated method to allow for fine-grained control
    over search parameters and execution flow.
    """

    def __init__(self):
        # Initialize scrapers with their respective source names and languages
        self.remoteok_scraper = RemoteOkScraper(source_name="Remote.ok EN", source_language="en")
        self.linkedin_en_scraper = LinkedInScraper(source_name="LinkedIn EN", source_language="en")
        self.linkedin_pt_scraper = LinkedInScraper(source_name="LinkedIn PT", source_language="pt")
        self.gupy_scraper = GupyScraper()

    def run_remoteok(self, search_params: RemoteOkSearchParams) -> Dict[str, List[Any]]:
        """
        Executes the Remote.ok scraper.
        
        Args:
            search_params: RemoteOkSearchParams dataclass containing tags and location.
            
        Returns:
            A dictionary with 'jobs' and 'companies' lists.
        """
        print(f"🚀 Orchestrating Remote.ok scrape | Params: {search_params.to_dict()}")
        return self.remoteok_scraper.scrape_jobs_and_companies(search_params)

    def run_linkedin(self, search_params: LinkedInSearchParams, language: str = "en") -> Dict[str, List[Any]]:
        """
        Executes the LinkedIn scraper for a specific language market.
        
        Args:
            search_params: LinkedInSearchParams dataclass.
            language: The market language ('en' or 'pt').
            
        Returns:
            A dictionary with 'jobs' and 'companies' lists.
        """
        print(f"🚀 Orchestrating LinkedIn ({language.upper()}) scrape | Params: {search_params.to_dict()}")
        scraper = self.linkedin_en_scraper if language == "en" else self.linkedin_pt_scraper
        return scraper.scrape_jobs_and_companies(search_params)

    def run_gupy(self, search_params: GupySearchParams) -> Dict[str, List[Any]]:
        """
        Executes the Gupy scraper.
        
        Args:
            search_params: GupySearchParams dataclass containing jobName, limit, etc.
            
        Returns:
            A dictionary with 'jobs' and 'companies' lists.
        """
        print(f"🚀 Orchestrating Gupy scrape | Params: {search_params.to_dict()}")
        return self.gupy_scraper.scrape_jobs_and_companies(search_params)

    def run_all_sequentially(self, 
                             remoteok_params: RemoteOkSearchParams, 
                             linkedin_en_params: LinkedInSearchParams, 
                             linkedin_pt_params: LinkedInSearchParams, 
                             gupy_params: GupySearchParams) -> Dict[str, List[Any]]:
        """
        Utility method to run all scrapers sequentially. 
        Note: In a production Airflow environment, it is recommended to run these 
        as separate tasks for better observability and retry management.
        """
        results = {"jobs": [], "companies": []}
        
        for run_func, params in [
            (self.run_remoteok, remoteok_params),
            (lambda p: self.run_linkedin(p, "en"), linkedin_en_params),
            (lambda p: self.run_linkedin(p, "pt"), linkedin_pt_params),
            (self.run_gupy, gupy_params)
        ]:
            data = run_func(params)
            results["jobs"].extend(data.get("jobs", []))
            results["companies"].extend(data.get("companies", []))
            
        return results
