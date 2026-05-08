from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional

class Location(Enum):
    BRAZIL = "Brazil"
    UNITED_STATES = "United States"

class GeoId(Enum):
    BRAZIL = "106057199"
    UNITED_STATES = "103644278"

class TimePosted(Enum):
    PAST_24_HOURS = "r86400"
    PAST_WEEK = "r604800"
    PAST_MONTH = "r2592000"
    ANY_TIME = ""

class WorkType(Enum):
    ON_SITE = "1"
    REMOTE = "2"
    HYBRID = "3"

class ExperienceLevel(Enum):
    INTERNSHIP = "1"
    ENTRY_LEVEL = "2"
    ASSOCIATE = "3"
    MID_SENIOR_LEVEL = "4"
    DIRECTOR = "5"
    EXECUTIVE = "6"

@dataclass
class LinkedInBaseDataclass:
    def to_dict(self) -> dict:
        """Converts the dataclass to a dictonary"""
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class LinkedInSearchParams(LinkedInBaseDataclass):
    "typed map for LinkedIn's API parameters."
    keywords: str
    location: str
    geoId: str
    f_TPR: Optional[str] = TimePosted.PAST_24_HOURS.value
    f_WT: Optional[str] = None
    f_E: Optional[str] = None
    start: int = 0

@dataclass
class LinkedInJob(LinkedInBaseDataclass):
    title: str
    description: str
    url: str
    location: str
    job_type: str
    scraped_at: str
    posted_time_raw: str
    source_name: str

@dataclass
class LinkedInCompany(LinkedInBaseDataclass):
    name: str
    industry: str