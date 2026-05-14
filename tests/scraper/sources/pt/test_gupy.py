import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from scraper.sources.pt.source_gupy import GupyScraper
from scraper.sources.pt.gupy_config import GupySearchParams, GupyJob, GupyCompany

@pytest.fixture
def gupy_scraper():
    return GupyScraper()

@pytest.fixture
def sample_gupy_job_data():
    return {
        "name": "Software Engineer",
        "description": "<p>Job Description</p>",
        "jobUrl": "https://gupy.io/job/123",
        "city": "São Paulo",
        "country": "Brazil",
        "workplaceType": "remote",
        "publishedDate": "2024-05-14T10:00:00.000Z",
        "careerPageName": "Tech Company",
        "careerPageUrl": "https://techcompany.gupy.io"
    }

def test_gupy_fetch(gupy_scraper, sample_gupy_job_data):
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [sample_gupy_job_data]}
    
    with patch.object(gupy_scraper, "_safe_request", return_value=mock_response):
        params = GupySearchParams(jobName="engineer", limit=10)
        result = gupy_scraper.fetch(params)
        
        assert len(result) == 1
        assert result[0]["name"] == "Software Engineer"

def test_gupy_parse(gupy_scraper, sample_gupy_job_data):
    parsed = gupy_scraper.parse(sample_gupy_job_data)
    
    job = parsed["job"]
    company = parsed["company"]
    
    assert isinstance(job, GupyJob)
    assert job.title == "Software Engineer"
    assert job.location == "São Paulo / Brazil"
    assert job.job_type == "remote"
    
    assert isinstance(company, GupyCompany)
    assert company.name == "Tech Company"
    assert company.website == "https://techcompany.gupy.io"

def test_gupy_parse_no_city(gupy_scraper, sample_gupy_job_data):
    sample_gupy_job_data["city"] = ""
    parsed = gupy_scraper.parse(sample_gupy_job_data)
    assert parsed["job"].location == "Brazil"

def test_gupy_scrape_jobs_and_companies(gupy_scraper, sample_gupy_job_data):
    with patch.object(gupy_scraper, "fetch", return_value=[sample_gupy_job_data]):
        params = GupySearchParams(jobName="engineer", limit=10)
        result = gupy_scraper.scrape_jobs_and_companies(params)
        
        assert "jobs" in result
        assert "companies" in result
        assert len(result["jobs"]) == 1
        assert len(result["companies"]) == 1
        assert result["jobs"][0]["title"] == "Software Engineer"
        assert result["companies"][0]["name"] == "Tech Company"
