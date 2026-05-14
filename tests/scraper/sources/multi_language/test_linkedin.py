import pytest
from unittest.mock import MagicMock, patch
from scraper.sources.multi_language.source_linkedin import LinkedInScraper
from scraper.sources.multi_language.linkedin_config import LinkedInSearchParams, LinkedInJob, LinkedInCompany

@pytest.fixture
def linkedin_scraper():
    return LinkedInScraper(source_name="LinkedIn EN", source_language="en")

@pytest.fixture
def sample_linkedin_list_html():
    return """
    <ul>
        <li>
            <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/data-engineer-123456789">
                Job 1
            </a>
        </li>
        <li>
            <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/software-engineer-987654321?refId=abc">
                Job 2
            </a>
        </li>
    </ul>
    """

@pytest.fixture
def sample_linkedin_job_detail_html():
    return """
    <div class="top-card-layout">
        <h2 class="top-card-layout__title">Data Engineer</h2>
        <a class="topcard__org-name-link">Tech Corp</a>
        <span class="topcard__flavor--bullet">São Paulo, Brazil</span>
        <span class="posted-time-ago__text">1 hour ago</span>
    </div>
    <div class="show-more-less-html__markup">
        Job description content goes here.
    </div>
    <ul class="description__job-criteria-list">
        <li class="description__job-criteria-item">
            <h3 class="description__job-criteria-subheader">Employment type</h3>
            <span class="description__job-criteria-text">Full-time</span>
        </li>
        <li class="description__job-criteria-item">
            <h3 class="description__job-criteria-subheader">Industries</h3>
            <span class="description__job-criteria-text">Technology</span>
        </li>
    </ul>
    """

def test_linkedin_fetch(linkedin_scraper, sample_linkedin_list_html):
    mock_response = MagicMock()
    mock_response.text = sample_linkedin_list_html
    
    with patch.object(linkedin_scraper, "_safe_request", return_value=mock_response):
        params = LinkedInSearchParams(keywords="data", location="Brazil", geoId="123")
        result = linkedin_scraper.fetch(params)
        assert result == sample_linkedin_list_html

def test_linkedin_parse(linkedin_scraper, sample_linkedin_list_html):
    job_ids = linkedin_scraper.parse(sample_linkedin_list_html)
    assert len(job_ids) == 2
    assert "123456789" in job_ids
    assert "987654321" in job_ids

def test_linkedin_parse_job_overview_html(linkedin_scraper, sample_linkedin_job_detail_html):
    parsed = linkedin_scraper._parse_job_overview_html(sample_linkedin_job_detail_html, "https://linkedin.com/job/1")
    
    job = parsed["job"]
    company = parsed["company"]
    
    assert isinstance(job, LinkedInJob)
    assert job.title == "Data Engineer"
    assert "Job description content" in job.description
    assert job.location == "São Paulo, Brazil"
    assert job.job_type == "Full-time"
    
    assert isinstance(company, LinkedInCompany)
    assert company.name == "Tech Corp"
    assert company.industry == "Technology"

def test_linkedin_scrape_jobs_and_companies(linkedin_scraper, sample_linkedin_list_html, sample_linkedin_job_detail_html):
    with patch.object(linkedin_scraper, "fetch", return_value=sample_linkedin_list_html):
        with patch.object(linkedin_scraper, "parse", return_value=["123456789"]):
            mock_detail_response = MagicMock()
            mock_detail_response.text = sample_linkedin_job_detail_html
            
            # Mock session.get directly since LinkedInScraper uses self.session.get for individual jobs
            with patch.object(linkedin_scraper.session, "get", return_value=mock_detail_response):
                params = LinkedInSearchParams(keywords="data", location="Brazil", geoId="123")
                result = linkedin_scraper.scrape_jobs_and_companies(params)
                
                assert "jobs" in result
                assert "companies" in result
                assert len(result["jobs"]) == 1
                assert result["jobs"][0]["title"] == "Data Engineer"
                assert result["companies"][0]["name"] == "Tech Corp"
