from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class RemoteOkSearchParams:
    tags: List[str]
    location: str

    def normalize_tags(self) -> str:
        """Normalize the tags into a single comma separeted string, required by Remote OK."""
        return ",".join(self.tags)

    def to_dict(self) -> Dict:
        search_params_dict = {}

        for k, v in asdict(self).items():
            if v is not None:
                search_params_dict[k] = v if k != "tags" else self.normalize_tags()

        return search_params_dict
    
@dataclass
class RemoteOkBaseDataclass:
    def to_dict(self) -> dict:
        """Converts the dataclass to a dictonary"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
@dataclass
class RemoteOkJob(RemoteOkBaseDataclass):
    title: str
    description: str
    url: str
    salary_min: float
    salary_max: float
    location: str
    job_type: str
    posted_date: str
    scraped_at: str
    source_name: str
    
@dataclass
class RemoteOkCompany(RemoteOkBaseDataclass):
    name: str