# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**JMIE (Job Market Intelligence Engine)** is an end-to-end automated ML pipeline system that scrapes, analyzes, and exposes market intelligence about technology job skills across English and Portuguese-speaking markets. It demonstrates cloud-agnostic MLOps best practices using a multi-cloud architecture (Oracle Cloud for compute, AWS S3 for storage, GCP for image registry).

**Current Status:** Early-stage development (Sprint 1 in progress). The repository contains the full PRD and project architecture, with only a minimal Python stub currently implemented.

## Architecture Overview

The system is organized into **four processing layers** that operate as a unified pipeline:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LAYER 1       │    │   LAYER 2       │    │   LAYER 3       │    │   LAYER 4       │
│ Data Scraping   │───▶│ NLP Processing  │───▶│ Hybrid Storage  │───▶│  API & Frontend │
│                 │    │                 │    │                 │    │                 │
│ • Airflow DAG   │    │ • XLM-RoBERTa   │    │ • PostgreSQL    │    │ • FastAPI RAG   │
│ • Scrapers      │    │   NER (PT+EN)   │    │ • Qdrant (VecDB)│    │ • React SPA     │
│ • AWS S3 Lake   │    │ • MLflow        │    │                 │    │ • Nginx Proxy   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Layer Details

- **Layer 1 (Data Scraping):** Apache Airflow DAGs orchestrate Python scrapers that fetch job postings from multiple boards (English: LinkedIn, Remote.ok; Portuguese: Gupy, Catho, InfoJobs). Raw data is normalized to a canonical JSON schema with language tagging and stored in AWS S3.

- **Layer 2 (NLP Processing):** Bilingual Named Entity Recognition (NER) using fine-tuned XLM-RoBERTa extracts structured skill entities (LANGUAGE, FRAMEWORK, CLOUD_PLATFORM, DATABASE, TOOL, CERTIFICATION, SOFT_SKILL, EXPERIENCE_LEVEL) from job descriptions. Multilingual embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, 768-dim) enable semantic similarity search. Model registry and versioning via MLflow.

- **Layer 3 (Hybrid Storage):** PostgreSQL stores normalized entity extractions and skill trend aggregations. Qdrant (vector database) indexes job embedding vectors using HNSW for efficient ANN retrieval.

- **Layer 4 (API & Frontend):** FastAPI REST API exposes a 5-stage RAG pipeline: encode query → dense vector ANN search → PostgreSQL skill trends → assemble context → synthesize response. React 18 + TypeScript SPA provides dashboard (trending skills, trend lines) and RAG interface. Full OpenTelemetry/Arize Phoenix observability for RAG pipeline inspection.

## Directory Structure

```
jmie/
├── dags/                    # Apache Airflow DAG definitions (orchestration)
├── scraper/                 # Data ingestion layer (Python scrapers)
│   ├── sources/en/         # English-language job board scrapers
│   └── sources/pt/         # Portuguese-language job board scrapers
├── nlp/                     # NLP processing (NER, embeddings, MLflow)
├── api/                     # FastAPI application (RAG query pipeline, endpoints)
├── frontend/                # React 18 + TypeScript SPA
├── db/                      # PostgreSQL schema, Alembic migrations, test seeds
├── mlflow/                  # MLflow tracking server Docker config
├── phoenix/                 # Arize Phoenix observability config
├── infrastructure/          # Cloud provider setup (Oracle VM, AWS IAM, GCP registry)
├── tests/                   # Unit & integration tests (en/pt splits)
├── docs/                    # MkDocs documentation (GitHub Pages deployment)
├── .github/workflows/       # CI/CD pipelines (lint, build, test, deploy)
├── pyproject.toml           # Project metadata, dependencies (uv-managed)
├── uv.lock                  # Unified lock file for all dependencies
├── docker-compose.yml       # Base service definitions (9 services)
├── docker-compose.dev.yml   # Development overrides (source builds, volume mounts)
├── docker-compose.prod.yml  # Production overrides (registry images, real creds)
├── .env.example             # Template for environment variables
├── .gitignore               # VCS exclusions (.env.prod, __pycache__, etc.)
└── CLAUDE.md               # This file
```

## Key Architectural Patterns

### 1. **Monorepo with Layer Separation**
Each of the four pipeline layers is a self-contained directory with its own dependencies, tests, and Docker service. This enables independent development, testing, and deployment while maintaining clear contracts between layers.

### 2. **Language-Split Sources**
Job board scrapers are organized as `scraper/sources/en/` (LinkedIn, Remote.ok) and `scraper/sources/pt/` (Gupy, Catho, InfoJobs). Adding new market-specific sources is trivial—just add a new module under the appropriate language folder.

### 3. **MLflow Model Registry as Source of Truth**
The Airflow NER task always loads the `Production` alias from MLflow—no manual environment variable management or version pinning. Model promotion to Production happens through the MLflow UI; CI/CD and production inference both reference the same immutable version.

### 4. **Bilingual Entity Schema**
All 8 entity types (LANGUAGE, FRAMEWORK, CLOUD_PLATFORM, DATABASE, TOOL, CERTIFICATION, SOFT_SKILL, EXPERIENCE_LEVEL) share the same label space across both languages. Portuguese surface forms (e.g., *Sênior*) map to English equivalents (e.g., `EXPERIENCE_LEVEL`).

### 5. **Compose Override Pattern**
A single base `docker-compose.yml` at the root defines all 9 services (Airflow, PostgreSQL, Qdrant, FastAPI, React, MLflow, Phoenix, Redis, Nginx). Environment-specific overrides in `docker-compose.dev.yml` (source builds, volume mounts, mock data) and `docker-compose.prod.yml` (registry images, real credentials, `restart: always`) prevent drift.

### 6. **Typed FastAPI Client in Frontend**
All backend API calls go through a single Axios client at `frontend/src/api/client.ts`, generated or hand-coded to match the FastAPI OpenAPI spec. TypeScript ensures integration contracts are validated at build time.

### 7. **OpenTelemetry/Phoenix Tracing**
Every `POST /query` request is instrumented as an OpenTelemetry trace with named spans for each of the 5 RAG pipeline stages. Traces are emitted to Arize Phoenix (`:6006`) for full retrospective observability of retrieval quality and latency.

### 8. **`uv` as Workspace Manager**
A single root-level `uv.lock` pins all transitive dependencies across `api/`, `nlp/`, `scraper/`, `dags/`, and `tests/`. This eliminates version drift between services and replaces `pip` entirely. All local and CI/CD development uses `uv` commands.

### 9. **Three-Tier CI/CD Strategy**
- `ci.yml` — Fast lint + unit tests, runs on every push to any branch
- `integration.yml` — Medium-speed integration tests, runs on PRs only
- `cd.yml` — Full build, push to registry, deploy to Oracle VM; runs on main merges only

## Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Orchestration** | Apache Airflow 2.x | DAG-based workflow; scheduled daily at 02:00 UTC |
| **Data Ingestion** | Python, requests, BeautifulSoup4 | HTML parsing with exponential backoff retry logic |
| **Language Detection** | `langdetect` | Bilingual classification (en/pt) at ingest time |
| **Storage** | AWS S3 + PostgreSQL 15 | S3 for raw data lake; PostgreSQL for structured metadata |
| **NLP Framework** | PyTorch + Hugging Face Transformers | CPU-only inference; no GPU required |
| **NER Model** | XLM-RoBERTa-base (fine-tuned) | Bilingual; F1 ≥ 0.80 per language |
| **Embeddings** | paraphrase-multilingual-MiniLM-L12-v2 | 768-dim; native PT+EN support |
| **Vector DB** | Qdrant | HNSW indexing; persistent Docker volume |
| **Experiment Tracking** | MLflow 2.x | Model Registry with Production alias promotion |
| **API** | FastAPI + Pydantic v2 | Async; Bearer token auth; OpenTelemetry instrumentation |
| **Frontend** | React 18 + TypeScript + Vite | Tailwind CSS; Recharts; React Query; Axios |
| **Observability** | Arize Phoenix | OpenTelemetry traces; RAG pipeline span capture |
| **Documentation** | MkDocs + Material theme | Markdown; GitHub Pages deployment via CI/CD |
| **Package Management** | `uv` | Workspace-aware; single lock file for all services |
| **Containerization** | Docker + Docker Compose | 9-service stack; multi-platform (amd64 + arm64) |
| **CI/CD** | GitHub Actions | Three separate workflows; automated deployment to Oracle VM |
| **Compute** | Oracle Cloud Always Free VM | 4 OCPU, 24 GB RAM, ARM64; $0/month perpetually |

## Development Commands

### Setup

```bash
# Install Python 3.12+ and uv (package manager)
# Clone the repo
cd jmie

# Install all dependencies (uv manages all layers)
uv sync

# Copy environment template and configure for development
cp .env.example .env.dev
# Edit .env.dev with mock AWS/GCP credentials (commit-safe references)
```

### Running Services Locally

```bash
# Start all 9 Docker Compose services in development mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Key service endpoints:
# - FastAPI:     http://localhost:8000
# - React dev:   http://localhost:5173
# - Airflow:     http://localhost:8080
# - MLflow:      http://localhost:5000
# - Phoenix:     http://localhost:6006
# - Qdrant:      http://localhost:6333
# - PostgreSQL:  localhost:5432
```

### Code Quality

```bash
# Run linting and formatting checks
uv run ruff check .
uv run ruff format --check .

# Fix formatting issues
uv run ruff format .

# Type checking
uv run mypy api/ nlp/ scraper/

# Run all quality checks (CI equivalent)
uv run pytest tests/ -v
uv run ruff check .
uv run mypy api/ nlp/ scraper/
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run tests for a specific layer
uv run pytest tests/scraper/ -v
uv run pytest tests/nlp/ -v
uv run pytest tests/api/ -v

# Run a single test file
uv run pytest tests/nlp/test_ner.py -v

# Run tests with coverage
uv run pytest tests/ --cov=api --cov=nlp --cov=scraper --cov-report=html
```

### Building & Deployment

```bash
# Build Docker images for all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Push images to GCP Artifact Registry (requires authentication)
docker compose -f docker-compose.prod.yml push

# Deploy to Oracle VM (runs via GitHub Actions on main merge)
# Manual deployment: SSH to Oracle VM and run:
cd /opt/jmie && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d
```

### Database Migrations

```bash
# Create a new migration (from db/ directory)
cd db && alembic revision --autogenerate -m "migration_name"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Airflow Management

```bash
# Access Airflow UI at http://localhost:8080
# Manually trigger a DAG (if needed during development)
docker exec jmie-airflow airflow dags trigger scraping_workflow

# View DAG logs
docker exec jmie-airflow airflow logs scraping_workflow <task_id> -n 100
```

### MLflow Model Management

```bash
# Access MLflow UI at http://localhost:5000
# Promote a run to Production via UI, or use CLI:
mlflow models transition-model-version-stage --model-name "ner-multilingual" --version <version> --stage Production
```

## Important Features & Guarantees

1. **MLflow Source of Truth:** The production NER inference task always loads from the `Production` alias in MLflow. Never hardcode model versions or reference S3 directly.

2. **Bilingual Entity Extraction:** All NER tags use English labels (e.g., `EXPERIENCE_LEVEL`) regardless of job description language. Portuguese models and training data are supported; output schema is unified.

3. **PostgreSQL Schema Versioned:** All schema changes go through Alembic migrations. Never execute raw SQL in production; always create a migration first.

4. **Qdrant Persistence:** Vector data is persisted to a Docker volume (`qdrant_data`). Restart safety is guaranteed; no in-memory-only operation.

5. **Rate Limiting & Backoff:** Web scrapers implement exponential backoff (max 3 retries, jitter) to respect job board rate limits. Failures are logged but don't crash the DAG; downstream tasks handle missing data gracefully.

6. **OpenTelemetry Instrumentation:** FastAPI endpoints emit traces to Phoenix. All RAG query stages are instrumented. Do not remove telemetry decorators; observability is critical for production debugging.

7. **Bearer Token Auth:** The FastAPI `/query` endpoint requires a Bearer token (issued via `/login` with API key). Never expose endpoints without auth checks.

8. **Multi-Language Support:** All user-facing strings and entity labels support both English and Portuguese. Use i18n patterns (not hardcoded strings) in the React frontend.

## Critical Files

- **`.llm/JMIE_PRD.md`** — Complete project requirements, data flow, milestones, and success criteria. Reference this for all architectural decisions.
- **`pyproject.toml`** — Project metadata and root dependencies. Use `uv add <package>` to add new dependencies; never edit manually.
- **`uv.lock`** — Single source of truth for all transitive dependencies. Commit this after any dependency change.
- **`.env.example`** — Template of all required environment variables. Update when adding new env vars; never commit `.env.prod`.
- **`docker-compose.yml`** — Base service definitions; shared by both dev and prod.
- **`docker-compose.dev.yml`** — Development overrides (source mounts, debug ports). Use with `-f docker-compose.yml -f docker-compose.dev.yml`.
- **`docker-compose.prod.yml`** — Production overrides (registry images, `restart: always`). Use with `-f docker-compose.yml -f docker-compose.prod.yml`.
- **`.github/workflows/ci.yml`** — Fast lint + unit test pipeline (every push).
- **`.github/workflows/integration.yml`** — Medium integration + e2e tests (PRs only).
- **`.github/workflows/cd.yml`** — Full build, push, deploy to Oracle VM (main merges only).

## Common Development Workflows

### Adding a New Scraper

1. Create a new module under `scraper/sources/en/` or `scraper/sources/pt/`.
2. Inherit from the base `Scraper` class (`scraper/base.py`).
3. Implement `fetch()` and `parse()` methods; return a list of normalized job posting dicts.
4. Add unit tests in `tests/scraper/sources/`.
5. Reference the new scraper in the Airflow DAG (`dags/scraping_workflow.py`).
6. Test locally with Docker Compose (mock data by default).

### Fine-Tuning the NER Model

1. Prepare labeled training data in `nlp/data/train_en.jsonl` and `nlp/data/train_pt.jsonl`.
2. Create a new training run in `nlp/train.py`; log metrics to MLflow.
3. Evaluate on held-out test sets (`nlp/data/test_en.jsonl`, `nlp/data/test_pt.jsonl`); target F1 ≥ 0.80 per language.
4. Use MLflow UI to compare runs and metrics per language.
5. Promote the best model to `Staging`, then to `Production` via MLflow UI.
6. The Airflow NER task automatically picks up the new Production model on next run.

### Adding a New API Endpoint

1. Create a Pydantic model for request/response in `api/models.py`.
2. Add the endpoint function in `api/routes/` with proper docstring (auto-generates OpenAPI docs).
3. Add Bearer token auth check using `Depends(verify_token)`.
4. Instrument with OpenTelemetry spans if it's a complex operation.
5. Add unit tests in `tests/api/test_routes.py`.
6. Frontend client in `frontend/src/api/client.ts` will auto-update from the OpenAPI spec.

### Deploying to Oracle VM

1. Ensure all commits are pushed to `main`.
2. GitHub Actions `cd.yml` workflow triggers automatically:
   - Builds Docker images for all services
   - Pushes to GCP Artifact Registry
   - SSHs to Oracle VM and runs `docker compose pull && docker compose up -d`
3. Verify deployment by accessing `https://<oracle-vm-ip>/` (Nginx reverse proxy).
4. Check logs: `ssh oracle-vm "docker logs -f jmie-api"`.

## Notes for Future Development

- **Roadmap:** The current code is at Sprint 1 (Foundation). Sprints 2–4 will build out each layer sequentially. Reference `.llm/JMIE_PRD.md` Section 6 for detailed milestone breakdown.
- **Cost Optimization:** All compute runs on Oracle Cloud Always Free VM ($0/mo). S3 costs ~$0.20/mo; GCP registry is free tier. Infrastructure decisions are intentional for cost efficiency.
- **Language Priorities:** English and Portuguese are primary. Future support for other languages should follow the same bilingual entity schema pattern.
- **Testing:** Target >80% code coverage for all layers. Integration tests validate the full DAG → Airflow → PostgreSQL → FastAPI flow.
- **Documentation:** MkDocs is the source of truth. Auto-deploy to GitHub Pages on main merges. Update frequently as features are built.
