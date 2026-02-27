# Project Requirements Document
## Job Market Intelligence Engine (JMIE)

> **Version:** 1.0 · **Status:** Active — In Development · **Project Code:** JMIE-2025
> **Domain:** MLOps / Data Engineering / NLP · **Cloud Target:** AWS (CLF-C02 aligned)
> Prepared by: Senior AI Product Manager & Lead MLOps Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture & Data Flow](#2-system-architecture--data-flow)
3. [Core Features & Requirements](#3-core-features--requirements)
4. [Infrastructure & Cloud Strategy](#4-infrastructure--cloud-strategy)
5. [Project Structure](#5-project-structure)
6. [Milestones & Sprints](#6-milestones--sprints)
7. [Out of Scope](#7-out-of-scope)

---

## 1. Executive Summary

### 1.1 The Problem

The modern technology job market generates thousands of new job postings every day, each containing dense, semi-structured text that describes the skills, tools, and qualifications employers actually value. For job seekers, career coaches, hiring managers, and workforce analysts, this data is invaluable — yet it remains almost entirely inaccessible at scale. Manually reading and cataloguing job descriptions is impractical. Existing third-party job analytics platforms are expensive, opaque in their methodology, and rarely expose raw query interfaces for custom analysis.

Three core problems drive this project:

- **Signal fragmentation:** Skill demand signals are locked inside unstructured free text spread across hundreds of job boards, with no consistent schema.
- **Latency:** By the time labor market reports are published (often quarterly), the underlying demand data is already stale for fast-moving tech stacks.
- **Query rigidity:** Existing tools offer static dashboards with pre-defined filters. There is no way to ask nuanced, natural-language questions such as *"What cloud skills are most commonly paired with Rust in senior backend roles?"*

### 1.2 The Solution

The Job Market Intelligence Engine (JMIE) is a fully automated, containerized, end-to-end ML pipeline that solves all three problems simultaneously. It operates across three primary layers:

- **Automated daily ingestion:** A Python scraping layer, orchestrated by Apache Airflow, fetches fresh job descriptions from public job boards and lands raw data in an AWS S3 data lake. Market data is never more than 24 hours old.
- **Intelligent skill extraction (NLP layer):** A fine-tuned Named Entity Recognition (NER) model, built on PyTorch and Hugging Face, processes each ingested job description and extracts structured skill entities (e.g., programming languages, frameworks, cloud platforms, certifications). Extracted metadata is persisted to PostgreSQL for analytical queries. Semantic vector embeddings of each job description are indexed into Qdrant for similarity-based retrieval.
- **Natural language query API (RAG layer):** A FastAPI-powered REST API exposes a Retrieval-Augmented Generation interface. Users submit natural language queries; the engine retrieves semantically relevant job descriptions from Qdrant, augments the query context, and synthesizes a coherent, evidence-grounded response about market trends.

> **Primary Goal:** Build the cheapest possible production-grade ML system that reinforces AWS CLF-C02 concepts, demonstrates a hybrid data architecture, and creates a genuinely useful market intelligence tool.

### 1.3 Primary Success Criteria

1. The Airflow DAG runs daily without manual intervention and successfully processes >95% of scraped postings.
2. The NER model achieves F1 > 0.80 on a held-out set of 500 manually annotated job descriptions.
3. The RAG API returns a meaningful, grounded response to any natural language market query within 5 seconds (p95 latency).
4. Total AWS monthly infrastructure cost stays under **$30 USD** in steady-state operation.
5. The project architecture maps explicitly to at least 6 AWS CLF-C02 service categories.

---

## 2. System Architecture & Data Flow

### 2.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    LAYER 1      │    │    LAYER 2      │    │    LAYER 3      │    │    LAYER 4      │
│  Data Ingestion │───▶│ NLP Processing  │───▶│ Hybrid Storage  │───▶│   API Serving   │
│                 │    │                 │    │                 │    │                 │
│ • Scrapers      │    │ • HuggingFace   │    │ • PostgreSQL    │    │ • FastAPI       │
│ • Airflow DAG   │    │   NER Model     │    │   (structured)  │    │   RAG Pipeline  │
│ • AWS S3 Lake   │    │ • Embeddings    │    │ • Qdrant        │    │ • Bearer Auth   │
│ • IAM / CW      │    │ • Batch Infer.  │    │   (vectors)     │    │ • GitHub Actions  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │                      │
         └──────────────────────┴──────────────────────┴──────────────────────┘
                    ALL SERVICES CONTAINERIZED VIA DOCKER COMPOSE ON AWS EC2 t3.medium
```

### 2.2 Detailed Data Flow: Step-by-Step

#### Step 1 — Job Description Scraping (Daily Trigger)

An Apache Airflow DAG, scheduled at **02:00 UTC daily**, triggers Python scraping tasks. Each task targets a specific job board using `requests` for HTTP and `BeautifulSoup` for HTML parsing.

Scraped records are normalized into the following JSON schema:

```json
{
  "job_id":              "string (SHA256 of source_url)",
  "title":               "string",
  "company":             "string",
  "location":            "string",
  "date_posted":         "ISO-8601 date",
  "raw_description_text":"string",
  "source_url":          "string"
}
```

Each batch is written as a gzip-compressed JSONL file to:

```
s3://jmie-datalake/raw/YYYY/MM/DD/batch_<timestamp>.jsonl.gz
```

The Airflow task is marked complete only after a successful S3 `PutObject` confirmation.

#### Step 2 — NER Skill Extraction (Triggered Post-Scrape)

A downstream Airflow task reads the raw JSONL batch from S3. Each `raw_description_text` is passed through a Hugging Face token-classification pipeline backed by a fine-tuned DistilBERT-based NER model.

**Entity types extracted:**

| Label | Examples |
|---|---|
| `LANGUAGE` | Python, Rust, Go, TypeScript |
| `FRAMEWORK` | FastAPI, React, PyTorch, Spring |
| `CLOUD_PLATFORM` | AWS, GCP, Azure, Kubernetes |
| `DATABASE` | PostgreSQL, Redis, MongoDB |
| `TOOL` | Docker, Terraform, Airflow |
| `CERTIFICATION` | AWS SAA, CKA, PMP |
| `SOFT_SKILL` | Communication, Leadership |
| `EXPERIENCE_LEVEL` | Senior, 5+ years, Lead |

Extracted entities → **PostgreSQL** `skills_extracted` table.
Full description → **768-dim embedding** → upserted into **Qdrant** `job_postings` collection.

#### Step 3 — Structured Aggregation (PostgreSQL)

Post-NER, an Airflow SQL operator refreshes the `skill_trends_daily` materialized view:

```sql
SELECT
  skill_name,
  skill_type,
  DATE(extracted_at)   AS trend_date,
  job_category,
  experience_level,
  COUNT(*)             AS mention_count
FROM skills_extracted
GROUP BY skill_name, skill_type, trend_date, job_category, experience_level;
```

#### Step 4 — Vector Index Maintenance (Qdrant)

- HNSW indexing for high-recall ANN search
- Upsert is idempotent — re-processing the same `job_id` overwrites, never duplicates
- Weekly retention sweep: delete vectors for postings older than **90 days**

#### Step 5 — FastAPI RAG Request Handling

Five-stage pipeline on every `POST /query` request:

```
① Encode user query → dense vector (same model as ingestion)
② ANN search Qdrant → top-K=10 semantically similar job descriptions
③ Query PostgreSQL skill_trends_daily → corroborating frequency counts
④ Assemble structured prompt context (retrieved docs + quantitative data)
⑤ Synthesize natural language response → return JSON with answer + cited evidence
```

> **Note:** The RAG layer is optional for the generative step. If no generative backend is configured, the API returns retrieved documents directly as a retrieval-only engine.

---

## 3. Core Features & Requirements

### 3.1 Data Engineering Requirements

| ID | Requirement | Specification |
|---|---|---|
| DE-01 | Scraper Resilience | Retry logic: 3 attempts, exponential backoff. Failed sources must not block the DAG. |
| DE-02 | Schema Versioning | S3 landing schema version-tagged. Breaking changes require new prefix path (e.g., `/v2/raw/`). |
| DE-03 | Deduplication | Each `job_id` checked before PostgreSQL insert. Duplicates skipped with log entry — never re-inserted. |
| DE-04 | S3 Partitioning | Partitioned by `year/month/day` to support future Athena/Glue integration and minimize list costs. |
| DE-05 | DAG Monitoring | Email or Slack webhook alerting on task failure. Success/failure status logged to dedicated S3 audit prefix. |
| DE-06 | Airflow Isolation | Airflow runs in Docker Compose with its own PostgreSQL metadata DB, separate from the application DB. |
| DE-07 | Configurable Sources | Job source URLs managed via external YAML config or environment variables. No URL hard-coding in task code. |

### 3.2 Data Science & NLP Requirements

| ID | Requirement | Specification |
|---|---|---|
| DS-01 | Model Selection | Lightweight transformer (DistilBERT or equivalent). CPU-only. No GPU dependency in base architecture. |
| DS-02 | Entity Schema | Minimum 8 entity types: `LANGUAGE`, `FRAMEWORK`, `CLOUD_PLATFORM`, `DATABASE`, `TOOL`, `SOFT_SKILL`, `EXPERIENCE_LEVEL`, `CERTIFICATION`. |
| DS-03 | Training Data | Minimum 2,000 annotated sentences. Annotation via Label Studio or compatible open-source tool. |
| DS-04 | Model Evaluation | Token-level F1 ≥ 0.80 per entity class on 20% held-out validation split before production promotion. |
| DS-05 | Embedding Consistency | Sentence embedding model (e.g., `all-MiniLM-L6-v2`) version-pinned and identical at ingestion and query time. |
| DS-06 | Batch Inference | Minimum batch size of 32 samples per forward pass. No record-by-record inference. |
| DS-07 | Model Artifact Storage | Model weights stored in `s3://jmie-models/` with versioned filenames. Production version controlled by `$MODEL_VERSION` env var. |
| DS-08 | Inference Logging | Each run logs: `model_version`, `batch_size`, `total_records`, `inference_duration_s`, `entity_counts_by_type`. |

### 3.3 MLOps & Backend Requirements

| ID | Requirement | Specification |
|---|---|---|
| MLOPS-01 | Containerization | Every component runs as a Docker container via a single `docker-compose.yml` at project root. |
| MLOPS-02 | CI/CD Pipeline | GitHub Actions: lint+test on every push; Docker build+push on merge to `main`; SSH-triggered redeploy on EC2. |
| MLOPS-03 | Environment Config | All secrets via `.env` file. No secrets committed. `.env.example` documents all required variables. |
| MLOPS-04 | FastAPI Endpoints | `GET /health`, `GET /skills/trending`, `GET /skills/search?q=`, `POST /query`. |
| MLOPS-05 | API Authentication | Bearer token required on all non-health endpoints. Keys stored as hashed values in `api_keys` table. |
| MLOPS-06 | Request Validation | All endpoints use Pydantic v2 models. Invalid requests return structured `422 Unprocessable Entity`. |
| MLOPS-07 | Logging Standard | Structured JSON logging via `structlog`. All logs include: `timestamp`, `service_name`, `level`, `request_id`, `message`. |
| MLOPS-08 | Data Persistence | PostgreSQL and Qdrant data mounted to named Docker volumes. Backup scripts included in weekly maintenance DAG. |

---

## 4. Infrastructure & Cloud Strategy

### 4.1 AWS Service Mapping

| AWS Service | Role in JMIE | CLF-C02 Domain |
|---|---|---|
| **EC2 t3.medium** | Primary compute host. Runs all Docker containers via Docker Compose. | Compute |
| **Amazon S3** | Immutable data lake for raw JSONL, processed batches, model artifacts, and DAG audit logs. Versioning enabled on model prefix. | Storage |
| **RDS for PostgreSQL** *(optional)* | Managed PostgreSQL alternative. `db.t3.micro` is Free Tier eligible. Use only if containerized DB shows instability. | Databases |
| **AWS IAM** | EC2 instance role grants least-privilege S3 + CloudWatch access. No long-lived access keys on the instance. | Security & Identity |
| **Amazon CloudWatch** | EC2 CPU/memory metrics. Custom metrics for DAG success/failure rate via `PutMetricData` API. | Monitoring |
| **S3 Lifecycle Policies** | Transition raw data >30 days to S3-IA. Delete files >90 days. Controls ongoing storage cost automatically. | Cost Optimization |

### 4.2 Cost Control Strategy

#### Compute (EC2)
- **Instance:** `t3.medium` (2 vCPU, 4 GB RAM) — ~$30/month On-Demand, ~$19/month with 1-year Reserved Instance
- **Stop/start schedule:** Lambda + EventBridge stops the instance at 22:00 UTC and starts at 07:00 UTC (weekdays only). Reduces active hours from 720 → ~250/month, cutting EC2 cost by ~**65%**
- No load balancer required. Direct security group port mapping is sufficient for a single-instance deployment

#### Storage (S3)
- S3 Standard is free for the first 5 GB. Lifecycle rules must be configured from Day 1
- Estimated volume: ~50 MB/day of raw JSONL → max ~4.5 GB at 90-day retention (<$0.15/month)
- Model artifacts (<500 MB total) transition to Intelligent-Tiering after 30 days

#### Database
- Default: containerized PostgreSQL on the same EC2 host → **zero additional AWS cost**
- RDS is optional/fallback only

#### Data Transfer
- All services within `us-east-1`. Intra-region EC2→S3 data transfer is **free**
- Cross-region transfer must be avoided entirely

### 4.3 Docker Compose Services

| Service | Image | Port(s) | Description |
|---|---|---|---|
| `airflow-scheduler` | `apache/airflow:2.x` | `8080` | Airflow web UI and scheduler. DAG definitions from mounted `./dags` volume. |
| `airflow-worker` | `apache/airflow:2.x` | — | Celery/sequential executor worker. Runs scraping, NER, and embedding tasks. |
| `postgres-app` | `postgres:15` | `5432` | Application DB: job metadata, extracted skills, API keys. |
| `postgres-airflow` | `postgres:15` | `5433` | Airflow metadata DB. Isolated from application data. |
| `qdrant` | `qdrant/qdrant:latest` | `6333`, `6334` | Vector DB. Port 6333 = REST API, 6334 = gRPC. Data persisted via named volume. |
| `fastapi-app` | `jmie/api:latest` | `8000` | Custom FastAPI image. RAG query, trending skills, and health endpoints. |

### 4.4 Network & Security Configuration

- **Security group inbound rules:** `8080` (Airflow UI — restrict to known IPs), `8000` (FastAPI), `22` (SSH — developer IPs only). All other ports blocked.
- **Internal services** (Qdrant `:6333`, PostgreSQL `:5432/:5433`) are NOT exposed on the EC2 host. Internal Docker bridge networking only.
- **IAM permissions** scoped to: `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `cloudwatch:PutMetricData` — restricted to the `jmie-datalake` bucket ARN only. No wildcard `*` resource permissions.
- **HTTPS** deferred to a future sprint. HTTP is acceptable given the non-PII nature of the data.

---

## 5. Project Structure

The repository follows a monorepo layout with strict separation between pipeline stages, infrastructure configuration, ML artifacts, and the API application layer.

```
jmie/
│
├── .github/workflows/ci_cd.yml                  # CI/CD pipeline definition (lint → build → deploy)
├── docker-compose.yml              # Single-command full-stack orchestration
├── .env.example                    # Template documenting all required environment variables
├── .gitignore
├── README.md                       # Setup guide, architecture overview, API docs
│
├── dags/                           # Apache Airflow DAG definitions
│   ├── jmie_daily_pipeline.py      # Main DAG: scrape → NER → embed → aggregate
│   ├── jmie_maintenance.py         # Weekly DAG: Qdrant sweep, volume backup, cleanup
│   └── utils/
│       ├── s3_helpers.py           # S3 read/write utility functions
│       ├── db_helpers.py           # PostgreSQL connection pool + query helpers
│       └── alerting.py             # Slack/email alert wrappers for task failure
│
├── scraper/                        # Data ingestion layer
│   ├── __init__.py
│   ├── base_scraper.py             # Abstract base class with retry logic + backoff
│   ├── sources/
│   │   ├── source_a.py             # Scraper implementation for Job Board A
│   │   └── source_b.py             # Scraper implementation for Job Board B
│   ├── normalizer.py               # Raw HTML → canonical JSON schema
│   ├── deduplicator.py             # job_id hash check before DB/S3 write
│   └── config/
│       └── sources.yaml            # Job board URLs and scraping parameters
│
├── nlp/                            # NLP processing layer
│   ├── __init__.py
│   ├── ner/
│   │   ├── train.py                # Fine-tuning script for DistilBERT NER model
│   │   ├── evaluate.py             # F1 evaluation on held-out validation split
│   │   ├── predict.py              # Batch inference pipeline (min batch=32)
│   │   ├── entity_schema.py        # Entity label definitions and validation
│   │   └── annotation/
│   │       ├── export_to_labelstudio.py  # Converts raw text to Label Studio import format
│   │       └── import_from_labelstudio.py # Parses Label Studio annotations → training data
│   ├── embeddings/
│   │   ├── encoder.py              # Sentence-transformer wrapper (version-pinned)
│   │   └── qdrant_client.py        # Qdrant upsert, search, and collection management
│   └── registry/
│       └── model_loader.py         # Loads model version from $MODEL_VERSION → S3 pull
│
├── api/                            # FastAPI application layer
│   ├── Dockerfile                  # Multi-stage build for the fastapi-app service
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app factory, middleware registration
│   ├── routers/
│   │   ├── health.py               # GET /health — liveness probe
│   │   ├── skills.py               # GET /skills/trending, GET /skills/search
│   │   └── query.py                # POST /query — RAG pipeline entrypoint
│   ├── rag/
│   │   ├── pipeline.py             # 5-stage RAG orchestrator
│   │   ├── retriever.py            # Qdrant ANN search wrapper
│   │   ├── augmenter.py            # PostgreSQL context enrichment
│   │   └── synthesizer.py          # Generative response synthesis
│   ├── models/
│   │   ├── requests.py             # Pydantic v2 request schemas
│   │   └── responses.py            # Pydantic v2 response schemas
│   ├── auth/
│   │   └── api_key.py              # Bearer token validation middleware
│   └── core/
│       ├── config.py               # Settings loaded from environment variables
│       ├── database.py             # SQLAlchemy async session factory
│       └── logging.py              # structlog JSON logging configuration
│
├── db/                             # Database schema management
│   ├── migrations/                 # Alembic migration scripts
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       └── 002_add_skill_trends_view.py
│   ├── schema.sql                  # Reference DDL for all tables and views
│   └── seeds/
│       └── test_data.sql           # Minimal seed data for local development
│
├── infrastructure/                 # AWS and deployment configuration
│   ├── ec2_bootstrap.sh            # User-data script: Docker install, env setup
│   ├── iam_policy.json             # Least-privilege IAM policy document
│   ├── s3_lifecycle.json           # S3 lifecycle rules (IA transition, deletion)
│   ├── eventbridge_schedule.json   # EC2 stop/start schedule definition
│   └── cloudwatch_dashboard.json   # CloudWatch dashboard JSON template
│
├── tests/                          # Test suite
│   ├── unit/
│   │   ├── test_scraper.py         # Scraper normalization and deduplication logic
│   │   ├── test_ner_predict.py     # NER batch inference correctness
│   │   └── test_api_routes.py      # FastAPI endpoint unit tests (mocked deps)
│   ├── integration/
│   │   ├── test_pipeline_e2e.py    # Full DAG run against a local test environment
│   │   └── test_rag_query.py       # RAG pipeline with live Qdrant + PostgreSQL
│   └── fixtures/
│       ├── sample_job_postings.json
│       └── annotated_ner_samples.json
│
├── notebooks/                      # Exploratory & experimental notebooks (not production)
│   ├── 01_eda_job_descriptions.ipynb
│   ├── 02_ner_training_experiments.ipynb
│   └── 03_rag_response_quality_eval.ipynb
│
└── scripts/                        # Operational one-off scripts
    ├── backup_volumes.sh           # Docker volume backup to S3
    ├── restore_volumes.sh          # Restore volumes from S3 backup
    ├── seed_api_key.py             # Generate and hash a new API key into the DB
    └── retrain_ner.sh              # End-to-end NER retrain + S3 upload workflow
```

### 5.1 Key Architectural Decisions in the File Structure

**Monorepo with clear layer separation.** Each of the four pipeline layers (`dags/`, `scraper/`, `nlp/`, `api/`) maps directly to the architecture diagram, making it easy to reason about data flow and assign ownership.

**Single `docker-compose.yml` at root.** One command (`docker compose up -d`) starts the entire stack. No developer needs to know about individual service configurations to get a working environment.

**`config/sources.yaml` in `scraper/`.** New job board sources can be added without touching any Python. This directly satisfies requirement DE-07.

**`nlp/registry/model_loader.py`.** Centralizes the model version resolution logic. The `$MODEL_VERSION` environment variable is the single control plane for which NER weights are loaded across all workers.

**`db/migrations/` with Alembic.** Versioned schema migrations ensure that any developer cloning the repo can reproduce the exact database state with a single `alembic upgrade head` command.

**`infrastructure/` as code.** All AWS configuration (IAM policy, S3 lifecycle, EventBridge schedule) is stored as JSON/shell files. This makes the AWS setup reproducible and auditable without clicking through the console.

**`tests/` split into `unit/` and `integration/`.** Unit tests run on every push (fast, no infrastructure needed). Integration tests run only on merge to `main` in the CI pipeline, requiring a live test environment.

---

## 6. Milestones & Sprints

Each sprint is two weeks with a defined, demonstrable deliverable. Sprints are strictly sequential.

### Sprint 1 — Infrastructure Foundations *(Weeks 1–2)*

| Deliverable | Acceptance Criteria |
|---|---|
| EC2 provisioned | Ubuntu 22.04 LTS, Docker + Docker Compose installed, SSH access verified |
| S3 bucket created | Versioning enabled, lifecycle rules configured, IAM role attached to EC2 |
| Docker Compose scaffolded | All 6 services defined (placeholder images); `docker compose up` succeeds |
| GitHub repo initialized | `.gitignore`, `.env.example` committed; CI pipeline linting on every push |
| **Sprint Deliverable** | All containers start; S3 accessible from EC2 via instance role (no static credentials) |

### Sprint 2 — Data Ingestion Pipeline *(Weeks 3–4)*

| Deliverable | Acceptance Criteria |
|---|---|
| Scraper module | Minimum 2 job board sources; retry logic; graceful failure handling |
| Airflow DAG | `scrape → validate → S3-write` task chain; manual trigger successful |
| PostgreSQL schema | `jobs`, `companies`, `sources` tables with indexes; Alembic migration applied |
| S3-to-Postgres loader | Raw metadata loader task tested end-to-end |
| **Sprint Deliverable** | DAG populates S3 and PostgreSQL daily with 50+ new job records per run |

### Sprint 3 — NLP: NER & Embeddings *(Weeks 5–6)*

| Deliverable | Acceptance Criteria |
|---|---|
| Annotation dataset | 2,000+ labeled sentences in Label Studio; exported to training format |
| NER model fine-tuned | F1 score measured and documented per entity class; weights uploaded to S3 |
| NER Airflow task | Batch inference writes to `skills_extracted` table |
| Embedding pipeline | Sentence vectors upserted into Qdrant `job_postings` collection |
| **Sprint Deliverable** | End-to-end pipeline produces structured skill rows in PG and searchable vectors in Qdrant for every scraped job |

### Sprint 4 — FastAPI & RAG Query Layer *(Weeks 7–8)*

| Deliverable | Acceptance Criteria |
|---|---|
| FastAPI skeleton | All 4 endpoints scaffold with Pydantic v2 models |
| Auth middleware | Bearer token validation tested; 401 on missing/invalid token |
| `/skills/trending` | Returns real data from `skill_trends_daily` materialized view |
| `POST /query` | Full 5-stage RAG pipeline executes; returns JSON with answer + cited evidence |
| **Sprint Deliverable** | Callable API that accepts a natural language query and returns a grounded market trend response |

### Sprint 5 — MLOps Hardening & CI/CD *(Weeks 9–10)*

| Deliverable | Acceptance Criteria |
|---|---|
| CI/CD extended | Docker image built and pushed to registry on merge to `main` |
| Auto-deploy stage | SSH deploy triggers `docker compose pull && up -d` on EC2 |
| CloudWatch metrics | Custom DAG success/failure metrics visible in dashboard |
| EC2 schedule | EventBridge + Lambda stop/start schedule active and verified |
| Airflow alerting | Email/Slack alert fires on DAG task failure |
| Volume backups | Backup script runs in weekly maintenance DAG; verified S3 upload |
| **Sprint Deliverable** | Zero-touch deployment — a `git push` to `main` triggers a full production redeployment with no manual SSH |

---

## 7. Out of Scope

The following items are explicitly excluded from JMIE v1.0. Any scope change request during active sprints requires formal discussion and a documented decision.

### 7.1 User Interface

- No front-end web application, dashboard, or visualization layer (Streamlit, Grafana, Metabase, etc.). All interaction is via the REST API or the Airflow web UI.
- No interactive query builder, chart rendering, or data export feature.

### 7.2 Advanced ML Capabilities

- Salary prediction, job recommendation systems, or any model beyond NER is out of scope.
- LLM fine-tuning: The generative component uses a pre-trained model. Fine-tuning the generative model is not in scope.
- Real-time streaming ingestion (Kafka, Kinesis): All ingestion is batch-based on a daily schedule.
- Multi-language support: The NER model is English-only.

### 7.3 Enterprise Infrastructure

- Kubernetes orchestration (EKS, GKE, bare-metal K8s): Docker Compose is the target deployment tool.
- Managed Airflow (AWS MWAA): Starts at ~$250/month. Incompatible with the cost constraint.
- Multi-region deployment, disaster recovery, or high-availability configurations.
- Data warehouse integration (Redshift, BigQuery, Snowflake).

### 7.4 Compliance & Legal

- Legal review of job board scraping terms of service is a real-world prerequisite but is outside this PRD's scope. The project assumes scraping is limited to publicly accessible listings.
- GDPR, CCPA, or other data privacy frameworks. No personal data (candidate profiles, resumes) is collected or stored.
- SOC 2 compliance, penetration testing, or formal security audit.

### 7.5 Productization

- Multi-tenancy, user account management, or billing/subscription features.
- SLA guarantees, 99.9% uptime commitments, or on-call incident response.
- Mobile application or browser extension development.

---

## Tech Stack Summary

| Category | Technology | Version / Notes |
|---|---|---|
| **Orchestration** | Apache Airflow | 2.x · Docker Compose service |
| **Ingestion** | Python requests + BeautifulSoup4 | Standard library HTTP + HTML parsing |
| **Storage — Raw** | AWS S3 | Partitioned JSONL · Lifecycle rules |
| **ML Framework** | PyTorch + Hugging Face Transformers | CPU-only inference |
| **NER Model** | DistilBERT fine-tuned | F1 ≥ 0.80 target |
| **Embeddings** | `all-MiniLM-L6-v2` | 768-dim · sentence-transformers |
| **Vector DB** | Qdrant | HNSW index · containerized |
| **Relational DB** | PostgreSQL 15 | Containerized (RDS optional) |
| **API Framework** | FastAPI + Pydantic v2 | Async · Bearer auth |
| **Containerization** | Docker + Docker Compose | Single-host deployment |
| **CI/CD** | GitHub Actions | Lint → Build → Push → Deploy |
| **Hosting** | AWS EC2 t3.medium | Ubuntu 22.04 LTS |
| **Monitoring** | AWS CloudWatch | Custom metrics + EC2 health |
| **Identity** | AWS IAM | Least-privilege instance role |

---

*Document Control: JMIE PRD v1.0 · Approved for Sprint 1 · Senior AI PM & Lead MLOps Engineering*
