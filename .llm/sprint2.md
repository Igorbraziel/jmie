# Sprint 2 — Data Ingestion Pipeline (Weeks 3–4)

## Overview
Sprint 2 focuses on building the complete data ingestion layer (Layer 1) of JMIE. By the end of this sprint, the system will scrape job postings from multiple sources, validate them, store raw data in S3, and load processed metadata into PostgreSQL.

**Duration:** Weeks 3–4 (2 weeks)
**Status:** Ready for implementation

---

## Sprint 2 Deliverables & Acceptance Criteria

| Deliverable | Acceptance Criteria |
|---|---|
| **Scraper module** | Minimum 2 job board sources; retry logic with exponential backoff; graceful failure handling (no crash on network error) |
| **Airflow DAG** | `scrape → validate → S3-write` task chain; manual trigger successful; DAG visible in Airflow UI |
| **PostgreSQL schema** | `jobs`, `companies`, `sources` tables with primary keys and indexes; Alembic migration written and applied |
| **S3-to-Postgres loader** | Raw metadata loader task tested end-to-end; data flows from S3 → PostgreSQL |
| **Sprint Deliverable** | DAG populates S3 and PostgreSQL daily with 50+ new job records per run |

---

## Phase 1: Database Design & Schema (Days 1–2)

### Step 1.1: Design PostgreSQL Schema

Define three core tables that will store job metadata. Reference the canonical job posting schema from the PRD (§3.1).

**Tables to create:**

1. **`sources`** — Job board registry
   - `id` (PK)
   - `name` (VARCHAR, e.g., "LinkedIn EN", "Gupy PT")
   - `url` (VARCHAR, base URL)
   - `country` (VARCHAR, e.g., "US", "BR")
   - `language` (CHAR(2), "en" or "pt")
   - `created_at`, `updated_at`

2. **`companies`** — Employer deduplication
   - `id` (PK)
   - `name` (VARCHAR, unique)
   - `website` (VARCHAR, nullable)
   - `industry` (VARCHAR, nullable)
   - `created_at`

3. **`jobs`** — Job postings
   - `id` (PK, UUID or bigint)
   - `source_id` (FK → `sources.id`)
   - `company_id` (FK → `companies.id`)
   - `title` (VARCHAR)
   - `description` (TEXT, raw job posting HTML/text)
   - `url` (VARCHAR, unique per source)
   - `salary_min`, `salary_max` (NUMERIC, nullable)
   - `currency` (CHAR(3), nullable)
   - `location` (VARCHAR)
   - `job_type` (VARCHAR, e.g., "full-time", "contract")
   - `posted_date` (DATE or TIMESTAMP)
   - `scraped_at` (TIMESTAMP)
   - `raw_data` (JSONB, metadata from scraper)
   - `created_at`, `updated_at`

Add indexes on: `source_id`, `company_id`, `url`, `posted_date`, `created_at`.

### Step 1.2: Create Alembic Migration

1. **Create initial migration** via `uv` in the local DB environment:
   ```bash
   cd db
   uv run alembic revision --autogenerate -m "initial_schema"
   ```

2. **Edit the migration file** (`db/versions/00XX_initial_*.py`) to include `sources`, `companies`, `jobs` table definitions with constraints and indexes.

3. **Apply migration** using the dedicated `db-migrations` service profile:
   ```bash
   # Run the migrations container from the project root
   cd ..
   docker compose --profile migrations up db-migrations
   ```

4. **Verify schema** in PostgreSQL:
   ```bash
   docker exec -it jmie-postgres-app psql -U jmie_user -d jmie_db -c "\dt"
   ```

### Step 1.3: Seed Source Data

Create a seed migration or manual SQL insert to populate the `sources` table with at least 2 job boards:

**Example sources to seed:**
- `LinkedIn EN` (source_id=1) — country="US", language="en"
- `Gupy PT` (source_id=2) — country="BR", language="pt"
- `Remote.ok EN` — country="Global", language="en"
- `ProgramaThor PT` — country="BR", language="pt"

**Seed via migration**:
```sql
INSERT INTO sources (name, url, country, language, created_at, updated_at)
VALUES
  ('LinkedIn EN', 'https://www.linkedin.com/jobs', 'US', 'en', NOW(), NOW()),
  ('Gupy PT', 'https://gupy.io', 'BR', 'pt', NOW(), NOW());
```

---

## Phase 2: Scraper Module Development (Days 3–5)

### Step 2.1: Define Base Scraper Class

Create `scraper/base.py` with a reusable abstract scraper class:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

class BaseScraper(ABC):
    """Abstract base class for all job board scrapers."""

    def __init__(self, source_id: int, language: str):
        self.source_id = source_id
        self.language = language
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @abstractmethod
    def fetch(self) -> List[str]:
        """Fetch raw HTML or JSON from the job board. Must return list of page contents."""
        pass

    @abstractmethod
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse raw content into structured job posting dicts."""
        pass

    def scrape(self) -> List[Dict[str, Any]]:
        """Main entry point: fetch → parse → normalize."""
        try:
            raw_content = self.fetch()
            jobs = []
            for content in raw_content:
                jobs.extend(self.parse(content))
            return self._normalize(jobs)
        except Exception as e:
            print(f"Scraper error for source {self.source_id}: {e}")
            return []

    def _normalize(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize parsed jobs to canonical schema."""
        return [
            {
                "source_id": self.source_id,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "description": job.get("description", ""),
                "url": job.get("url", ""),
                "location": job.get("location", ""),
                "job_type": job.get("job_type"),
                "posted_date": job.get("posted_date"),
                "raw_data": job,
            }
            for job in jobs
        ]
```

### Step 2.2: Implement LinkedIn EN Scraper

Create `scraper/sources/en/linkedin.py`:

```python
from scraper.base import BaseScraper
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re

class LinkedInScraper(BaseScraper):
    """Scrapes job postings from LinkedIn (English, US/Global)."""

    def __init__(self):
        super().__init__(source_id=1, language="en")
        self.base_url = "https://www.linkedin.com/jobs/search/"

    def fetch(self) -> List[str]:
        """Fetch LinkedIn job listings. Note: This is simplified; real impl uses Selenium."""
        # Placeholder: In production, use Selenium or LinkedIn API with proper auth.
        # This demonstrates the interface.
        try:
            response = self.session.get(
                self.base_url,
                params={"keywords": "software engineer", "location": "United States"},
                timeout=10,
            )
            response.raise_for_status()
            return [response.text]
        except Exception as e:
            print(f"LinkedIn fetch failed: {e}")
            return []

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse LinkedIn HTML into job records."""
        soup = BeautifulSoup(content, "html.parser")
        jobs = []

        # Placeholder parser logic:
        # In production, extract actual LinkedIn job cards.
        job_cards = soup.find_all("div", {"class": "base-card"})
        for card in job_cards:
            try:
                title = card.find("h3", {"class": "base-search-card__title"})
                company = card.find("h4", {"class": "base-search-card__subtitle"})
                link = card.find("a", {"class": "base-card__full-link"})

                jobs.append({
                    "title": title.text.strip() if title else "",
                    "company": company.text.strip() if company else "",
                    "url": link["href"] if link else "",
                    "location": "TBD",
                    "description": "",
                })
            except Exception as e:
                print(f"Parse error: {e}")
                continue

        return jobs
```

### Step 2.3: Implement Gupy PT Scraper

Create `scraper/sources/pt/gupy.py`:

```python
from scraper.base import BaseScraper
from typing import List, Dict, Any
import requests

class GupyScraper(BaseScraper):
    """Scrapes job postings from Gupy (Portuguese, Brazil)."""

    def __init__(self):
        super().__init__(source_id=2, language="pt")
        self.base_url = "https://gupy.io/api/jobs"

    def fetch(self) -> List[str]:
        """Fetch Gupy jobs via API."""
        try:
            response = self.session.get(
                self.base_url,
                params={"page": 1, "limit": 50},
                timeout=10,
            )
            response.raise_for_status()
            return [response.text]
        except Exception as e:
            print(f"Gupy fetch failed: {e}")
            return []

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse Gupy JSON API response."""
        import json
        try:
            data = json.loads(content)
            jobs = []
            for job in data.get("jobs", []):
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "url": job.get("url", ""),
                    "location": job.get("location", ""),
                    "description": job.get("description", ""),
                    "job_type": job.get("job_type"),
                    "posted_date": job.get("posted_at"),
                })
            return jobs
        except Exception as e:
            print(f"Gupy parse error: {e}")
            return []
```

### Step 2.4: Create Scraper Factory & Orchestration

Create `scraper/orchestrator.py` to manage all scraper instances:

```python
from scraper.sources.en.linkedin import LinkedInScraper
from scraper.sources.pt.gupy import GupyScraper
from typing import List, Dict, Any
from datetime import datetime

class ScraperOrchestrator:
    """Manages execution of all scrapers."""

    def __init__(self):
        self.scrapers = [
            LinkedInScraper(),
            GupyScraper(),
        ]

    def run_all(self) -> List[Dict[str, Any]]:
        """Run all scrapers and aggregate results."""
        all_jobs = []
        for scraper in self.scrapers:
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            print(f"Scraper {scraper.source_id} collected {len(jobs)} jobs")

        return all_jobs
```

### Step 2.5: Unit Tests for Scrapers

Create `tests/scraper/sources/en/test_linkedin.py` and `tests/scraper/sources/pt/test_gupy.py`:

```python
import pytest
from scraper.sources.en.linkedin import LinkedInScraper

def test_linkedin_normalize():
    scraper = LinkedInScraper()
    raw = [{"title": "SWE", "company": "Google", "url": "http://..."}]
    normalized = scraper._normalize(raw)
    assert normalized[0]["source_id"] == 1
    assert normalized[0]["language"] == "en"

def test_linkedin_graceful_failure():
    scraper = LinkedInScraper()
    # Mock a network error
    scraper.session.get = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Network error"))
    result = scraper.scrape()
    assert result == []  # Graceful failure, not an exception
```

---

## Phase 3: S3 Integration (Days 5–6)

### Step 3.1: Add S3 Utilities

Create `scraper/storage.py`:

```python
import boto3
import json
from datetime import datetime
from typing import List, Dict, Any

class S3Storage:
    """Handle writing raw job data to AWS S3."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.s3_client = boto3.client("s3", region_name=region)
        self.bucket = bucket

    def write_jobs(self, jobs: List[Dict[str, Any]], source_id: int):
        """Write jobs to S3 in JSONL format, partitioned by date and source."""
        if not jobs:
            print(f"No jobs to write for source {source_id}")
            return

        date_str = datetime.utcnow().strftime("%Y/%m/%d")
        key = f"raw/source_id={source_id}/{date_str}/jobs.jsonl"

        content = "\n".join(json.dumps(job) for job in jobs)
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
        )
        print(f"Wrote {len(jobs)} jobs to s3://{self.bucket}/{key}")
```

### Step 3.2: Update Scraper Orchestrator with S3

Modify `scraper/orchestrator.py` to write to S3:

```python
from scraper.storage import S3Storage

class ScraperOrchestrator:
    def __init__(self, s3_bucket: str):
        self.scrapers = [LinkedInScraper(), GupyScraper()]
        self.s3 = S3Storage(bucket=s3_bucket)

    def run_all(self) -> List[Dict[str, Any]]:
        all_jobs = []
        for scraper in self.scrapers:
            jobs = scraper.scrape()
            self.s3.write_jobs(jobs, source_id=scraper.source_id)
            all_jobs.extend(jobs)
        return all_jobs
```

---

## Phase 4: Airflow DAG Development (Days 6–8)

### Step 4.1: Create Scraping DAG

Create `dags/scraping_workflow.py`:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.orchestrator import ScraperOrchestrator
from scraper.storage import S3Storage
import importlib

default_args = {
    "owner": "jmie-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "scraping_workflow",
    default_args=default_args,
    description="Daily job scraping pipeline",
    schedule_interval="0 2 * * *",  # Run daily at 02:00 UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
)

def run_scraper():
    """Execute all scrapers and write to S3."""
    s3_bucket = os.getenv("AWS_S3_BUCKET", "jmie-data-lake")
    orchestrator = ScraperOrchestrator(s3_bucket=s3_bucket)
    jobs = orchestrator.run_all()
    return {"total_jobs": len(jobs), "jobs": jobs}

def validate_jobs(ti):
    """Validate scraped data before loading."""
    task_output = ti.xcom_pull(task_ids="scrape")
    jobs = task_output.get("jobs", [])

    valid_count = 0
    for job in jobs:
        if job.get("title") and job.get("company") and job.get("url"):
            valid_count += 1

    print(f"Validated {valid_count}/{len(jobs)} jobs")
    return {"valid_count": valid_count, "total_count": len(jobs)}

def load_to_postgres(ti):
    """Load validated jobs from S3 to PostgreSQL."""
    validate_result = ti.xcom_pull(task_ids="validate")
    valid_count = validate_result.get("valid_count", 0)
    print(f"Loading {valid_count} jobs to PostgreSQL")
    # (Implement PostgreSQL loading in Phase 5)
    return {"loaded": valid_count}

# Define tasks
scrape_task = PythonOperator(
    task_id="scrape",
    python_callable=run_scraper,
    dag=dag,
)

validate_task = PythonOperator(
    task_id="validate",
    python_callable=validate_jobs,
    provide_context=True,
    dag=dag,
)

load_task = PythonOperator(
    task_id="load_to_postgres",
    python_callable=load_to_postgres,
    provide_context=True,
    dag=dag,
)

# Task dependencies
scrape_task >> validate_task >> load_task
```

### Step 4.2: Test DAG Syntax

```bash
cd dags
python -c "from scraping_workflow import dag; print('DAG loaded successfully')"
```

### Step 4.3: Trigger DAG Manually in Airflow UI

1. Navigate to `http://localhost:8080`
2. Find the `scraping_workflow` DAG in the list
3. Click the DAG name to open its detail view
4. Click the "Trigger DAG" button
5. Verify the tasks execute: `scrape` → `validate` → `load_to_postgres`

---

## Phase 5: S3-to-PostgreSQL Loader (Days 8–10)

### Step 5.1: Create PostgreSQL Loader Module

Create `scraper/postgres_loader.py`:

```python
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any
from datetime import datetime
import json

class PostgresLoader:
    """Load job data from S3/memory into PostgreSQL."""

    def __init__(self, host: str, database: str, user: str, password: str):
        self.conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
        )
        self.cursor = self.conn.cursor()

    def load_jobs(self, jobs: List[Dict[str, Any]]):
        """Bulk insert jobs into the database."""
        if not jobs:
            print("No jobs to load")
            return 0

        # Step 1: Ensure companies exist
        companies = set()
        for job in jobs:
            companies.add(job.get("company", "Unknown"))

        company_ids = self._ensure_companies(list(companies))

        # Step 2: Insert jobs
        values = []
        for job in jobs:
            company_id = company_ids.get(job.get("company"))
            values.append((
                job.get("source_id"),
                company_id,
                job.get("title"),
                job.get("description"),
                job.get("url"),
                job.get("location"),
                job.get("job_type"),
                job.get("posted_date"),
                datetime.utcnow(),
                json.dumps(job.get("raw_data", {})),
            ))

        insert_query = """
        INSERT INTO jobs (source_id, company_id, title, description, url, location, job_type, posted_date, scraped_at, raw_data)
        VALUES %s
        ON CONFLICT(url, source_id) DO NOTHING
        """

        result = execute_values(self.cursor, insert_query, values, fetch=True)
        self.conn.commit()
        return len(result) if result else 0

    def _ensure_companies(self, company_names: List[str]) -> Dict[str, int]:
        """Create companies if they don't exist, return {name: id} mapping."""
        result = {}
        for name in company_names:
            if not name:
                continue

            # Check if exists
            self.cursor.execute("SELECT id FROM companies WHERE name = %s", (name,))
            row = self.cursor.fetchone()

            if row:
                result[name] = row[0]
            else:
                # Insert new company
                self.cursor.execute(
                    "INSERT INTO companies (name, created_at) VALUES (%s, %s) RETURNING id",
                    (name, datetime.utcnow()),
                )
                result[name] = self.cursor.fetchone()[0]

        self.conn.commit()
        return result

    def close(self):
        self.cursor.close()
        self.conn.close()
```

### Step 5.2: Integrate Loader into DAG

Update `dags/scraping_workflow.py` to actually load into PostgreSQL:

```python
from scraper.postgres_loader import PostgresLoader
import os

def load_to_postgres(ti):
    """Load validated jobs from orchestrator output to PostgreSQL."""
    task_output = ti.xcom_pull(task_ids="scrape")
    jobs = task_output.get("jobs", [])

    # Initialize loader
    loader = PostgresLoader(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "jmie"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )

    try:
        loaded_count = loader.load_jobs(jobs)
        print(f"Loaded {loaded_count} jobs to PostgreSQL")
        return {"loaded": loaded_count}
    finally:
        loader.close()
```

### Step 5.3: Add Unique Index to Jobs Table

Create a migration to add a unique constraint preventing duplicate URL+source combinations:

```sql
ALTER TABLE jobs ADD CONSTRAINT unique_url_per_source UNIQUE (url, source_id);
```

### Step 5.4: Test End-to-End Locally

1. **Start Docker Compose stack**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

2. **Apply migrations**:
   ```bash
   docker compose --profile migrations -f docker-compose.yml -f docker-compose.dev.yml up db-migrations
   ```

3. **Seed sources**:
   ```bash
   docker exec jmie-postgres-app psql -U jmie_user -d jmie_db -c "INSERT INTO sources (name, url, country, language, created_at, updated_at) VALUES ('LinkedIn EN', 'https://linkedin.com', 'US', 'en', NOW(), NOW());"
   ```

4. **Trigger DAG manually**:
   ```bash
   docker exec jmie-airflow airflow dags trigger scraping_workflow
   ```

5. **Verify data in PostgreSQL**:
   ```bash
   docker exec jmie-postgres psql -U postgres -d jmie -c "SELECT COUNT(*) FROM jobs;"
   ```

6. **Verify data in S3**:
   ```bash
   aws s3 ls s3://jmie-data-lake/raw/ --recursive
   ```

---

## Phase 6: Testing & Documentation (Days 10–11)

### Step 6.1: Integration Tests

Create `tests/integration/test_scraping_pipeline.py`:

```python
import pytest
import os
from scraper.orchestrator import ScraperOrchestrator
from scraper.postgres_loader import PostgresLoader
from datetime import datetime

@pytest.fixture
def orchestrator():
    return ScraperOrchestrator(s3_bucket="jmie-data-lake-dev")

@pytest.fixture
def loader():
    return PostgresLoader(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "jmie"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )

def test_scraper_returns_jobs(orchestrator):
    """Test that orchestrator returns valid job records."""
    jobs = orchestrator.run_all()
    assert len(jobs) > 0
    for job in jobs:
        assert "title" in job
        assert "company" in job
        assert "source_id" in job

def test_postgres_loader(loader, orchestrator):
    """Test end-to-end: scrape -> load into PostgreSQL."""
    jobs = orchestrator.run_all()
    loaded = loader.load_jobs(jobs)
    assert loaded > 0

    # Verify in DB
    loader.cursor.execute("SELECT COUNT(*) FROM jobs WHERE source_id = %s", (1,))
    count = loader.cursor.fetchone()[0]
    assert count > 0
    loader.close()

def test_duplicate_url_handling(loader):
    """Test that duplicate URLs are rejected."""
    job1 = {
        "source_id": 1,
        "title": "SWE",
        "company": "Acme",
        "url": "https://example.com/job/123",
        "description": "Test",
    }
    job2 = {**job1}  # Same URL

    loaded = loader.load_jobs([job1, job2])
    assert loaded == 1  # Only one inserted
    loader.close()
```

### Step 6.2: Add Sprint 2 Tests to CI

Update `.github/workflows/ci.yml` to run scraper tests:

```yaml
- name: Run scraper tests
  run: uv run pytest tests/scraper/ tests/integration/ -v
```

### Step 6.3: Update Documentation

Add `docs/layer-1-scraping.md`:

```markdown
# Layer 1: Data Scraping

## Overview
Layer 1 orchestrates daily job board scraping, validation, and storage.

## Architecture
- **Scrapers**: Modular Python classes for each job board
- **Orchestrator**: Manages all scraper instances
- **Storage**: S3 + PostgreSQL persistence
- **Orchestration**: Apache Airflow DAG scheduled daily at 02:00 UTC

## Adding a New Scraper
1. Create a new module under `scraper/sources/{language}/{board}.py`
2. Inherit from `BaseScraper`
3. Implement `fetch()` and `parse()` methods
4. Add unit tests in `tests/scraper/sources/`
5. Register in `ScraperOrchestrator`

## Monitoring
- Airflow UI: `http://localhost:8080`
- S3 data: `s3://jmie-data-lake/raw/`
- PostgreSQL: `psql -d jmie -c "SELECT COUNT(*) FROM jobs;"`
```

---

## Phase 7: Acceptance & Sign-Off (Day 12)

### Step 7.1: Verify All Acceptance Criteria

| Criterion | Status | Evidence |
|---|---|---|
| **2+ scrapers** | ✓ | LinkedIn EN + Gupy PT in `scraper/sources/` |
| **Retry logic** | ✓ | `HTTPAdapter` with exponential backoff in `BaseScraper` |
| **Graceful failure** | ✓ | `try/except` in `scrape()` returns empty list on error |
| **DAG defined** | ✓ | `dags/scraping_workflow.py` with 3 tasks |
| **Manual trigger works** | ✓ | DAG runs successfully from Airflow UI |
| **PostgreSQL schema** | ✓ | Tables: `sources`, `companies`, `jobs` with indexes |
| **Alembic migration** | ✓ | Migration applied successfully |
| **S3-to-Postgres loader** | ✓ | `PostgresLoader` tested end-to-end |
| **50+ records daily** | ✓ | DAG produces ≥50 jobs per run |

### Step 7.2: Performance Baseline

Run a full DAG cycle and measure:

```bash
# Time the scraping
time docker exec jmie-airflow airflow tasks run scraping_workflow scrape $(date +%Y-%m-%d)

# Check job counts
docker exec jmie-postgres psql -U postgres -d jmie -c "SELECT COUNT(*) FROM jobs WHERE scraped_at >= NOW() - INTERVAL '1 hour';"

# Check S3 size
aws s3 ls s3://jmie-data-lake/raw/ --summarize --human-readable
```

### Step 7.3: Mark Sprint 2 Complete

- [ ] All acceptance criteria verified
- [ ] Code reviewed and merged to `main`
- [ ] Integration tests passing in CI
- [ ] Documentation updated in `docs/`
- [ ] Commit message: `Sprint 2: Data Ingestion Pipeline complete`

---

## Rollover to Sprint 3

At the end of Sprint 2, the output of Layer 1 (S3-stored raw job data + PostgreSQL metadata) becomes the **input** to Sprint 3 (Layer 2: NLP Processing). Ensure:

- PostgreSQL is seeded with ≥50 recent jobs daily
- S3 contains daily partitioned JSONL files
- All job records have `description` field populated (required for NER in Sprint 3)

Sprint 3 will read from PostgreSQL `jobs.description` and extract bilingual named entities using XLM-RoBERTa.

---

## Commands Reference

```bash
# Local development setup
uv sync
cp .env.example .env.dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Database
docker exec jmie-postgres psql -U postgres -d jmie -c "SELECT * FROM sources;"
cd db && alembic upgrade head
cd db && alembic revision --autogenerate -m "migration_name"

# Scraper testing
uv run pytest tests/scraper/ -v
uv run pytest tests/integration/test_scraping_pipeline.py -v

# Airflow
docker exec jmie-airflow airflow dags list
docker exec jmie-airflow airflow dags trigger scraping_workflow
docker exec jmie-airflow airflow logs scraping_workflow scrape -n 50

# S3 verification
aws s3 ls s3://jmie-data-lake/raw/ --recursive
aws s3 cp s3://jmie-data-lake/raw/source_id=1/2025/01/01/jobs.jsonl - | head -5

# CI/CD
git push origin main  # Triggers ci.yml + cd.yml
```

---

**Sprint 2 Duration:** 2 weeks (10 working days)
**Ready to begin:** Yes — All prerequisites from Sprint 1 are complete.
