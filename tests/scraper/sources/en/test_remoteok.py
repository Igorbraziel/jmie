import pytest
from unittest.mock import MagicMock, patch
from scraper.sources.en.source_remoteok import RemoteOkScraper
from scraper.sources.en.remoteok_config import RemoteOkSearchParams, RemoteOkJob, RemoteOkCompany

@pytest.fixture
def remoteok_scraper():
    return RemoteOkScraper(source_name="Remote.ok EN", source_language="en")

@pytest.fixture
def sample_remoteok_job_data():
    return {
        "position": "Python Developer",
        "description": "<p>We are looking for a Python Developer. Please mention the word 'BANANA' to show they're human.</p>",
        "url": "https://remoteok.com/job/1",
        "salary_min": "50000",
        "salary_max": "80000",
        "location": "Worldwide",
        "date": "2024-05-14T10:00:00Z",
        "company": "RemoteTech",
        "tags": ["python", "backend"]
    }

def test_remoteok_fetch(remoteok_scraper, sample_remoteok_job_data):
    mock_response = MagicMock()
    # Remote OK API returns a list where the first element is legal info
    mock_response.json.return_value = [
        {"legal": "info"},
        sample_remoteok_job_data
    ]
    
    with patch.object(remoteok_scraper, "_safe_request", return_value=mock_response):
        params = RemoteOkSearchParams(tags=["python"], location="anywhere")
        result = remoteok_scraper.fetch(params)
        
        assert len(result) == 1
        assert result[0]["position"] == "Python Developer"

def test_remoteok_parse_html_description(remoteok_scraper):
    html = "<p>Line 1</p><p>Please mention the word 'BANANA' to show they're human.</p>"
    # Note: _parse_html_description handles latin-1 encoding fixed to utf-8
    # But in the test we can pass a string that it can "re-encode"
    cleaned = remoteok_scraper._parse_html_description(html)
    assert "Line 1" in cleaned
    assert "Please mention the word" not in cleaned

def test_remoteok_parse(remoteok_scraper, sample_remoteok_job_data):
    parsed = remoteok_scraper.parse(sample_remoteok_job_data)
    
    job = parsed["job"]
    company = parsed["company"]
    
    assert isinstance(job, RemoteOkJob)
    assert job.title == "Python Developer"
    assert "Please mention the word" not in job.description
    assert job.salary_min == "50000"
    assert job.job_type == "REMOTE"
    
    assert isinstance(company, RemoteOkCompany)
    assert company.name == "RemoteTech"

def test_remoteok_scrape_jobs_and_companies(remoteok_scraper, sample_remoteok_job_data):
    with patch.object(remoteok_scraper, "fetch", return_value=[sample_remoteok_job_data]):
        params = RemoteOkSearchParams(tags=["python"], location="anywhere")
        result = remoteok_scraper.scrape_jobs_and_companies(params)
        
        assert "jobs" in result
        assert "companies" in result
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["title"] == "Python Developer"
        assert result["companies"][0]["name"] == "RemoteTech"
