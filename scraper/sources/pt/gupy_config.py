from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class GupyBaseDataclass:
    def to_dict(self) -> Dict:
        """converts a dataclass to a dictonary"""
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class GupySearchParams(GupyBaseDataclass):
    jobName: str
    limit: int
    offset: Optional[int] = 0

@dataclass
class GupyJob(GupyBaseDataclass):
    title: str
    description: str
    url: str
    location: str
    job_type: str
    posted_date: str
    scraped_at: str

@dataclass
class GupyCompany(GupyBaseDataclass):
    name: str
    website: str