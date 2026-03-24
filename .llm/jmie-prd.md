# Project Requirements Document
## Job Market Intelligence Engine (JMIE)

> **Version:** 2.0 · **Status:** Active — In Development · **Project Code:** JMIE-2025
> **Domain:** MLOps / Data Engineering / NLP / Agentic AI · **Cloud Strategy:** Multi-Cloud (Oracle + AWS + GCP)
> Prepared by: Senior AI Product Manager & Lead MLOps Engineering
>
> **v2.0 Changes:** Hybrid Agentic Architecture introduced — four AI Agents (Sprints 3–6) layered above the deterministic Airflow/PostgreSQL backbone. Multi-Model Tiered Strategy defined (Llama → Gemini → DeepSeek). Lightweight agent framework mandates per sprint. Heavy multi-agent roleplay frameworks (CrewAI) explicitly banned.
>
> **v1.6 Changes:** `uv` adopted as Python package manager across all services and CI/CD

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture & Data Flow](#2-system-architecture--data-flow)
3. [Core Features & Requirements](#3-core-features--requirements)
4. [Infrastructure & Cloud Strategy](#4-infrastructure--cloud-strategy)
5. [Project Structure](#5-project-structure)
6. [Milestones & Sprints](#6-milestones--sprints)
7. [Out of Scope](#7-out-of-scope)
8. [Cost, AI Infrastructure & Multi-Model Strategy](#8-cost-ai-infrastructure--multi-model-strategy)

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

> **Primary Goal:** Build the cheapest possible production-grade ML system on a multi-cloud architecture (Oracle Cloud for compute, AWS S3 for storage, GCP for image registry and API serving), demonstrating a hybrid data architecture and reinforcing cloud-agnostic MLOps best practices.

### 1.3 Primary Success Criteria

1. The Airflow DAG runs daily without manual intervention and successfully processes >95% of scraped postings.
2. The NER model achieves F1 > 0.80 on a held-out validation set, measured **separately** for English and Portuguese corpora.
3. The RAG API returns a meaningful, grounded response to any natural language market query (in EN or PT) within 5 seconds (p95 latency).
4. Total infrastructure cost stays under **$3 USD/month** in steady-state (Oracle VM: $0 · AWS S3: ~$0.20 · GCP: ~$0 within free tier · LLM API: $0 within Gemini AI Studio free tier).
5. The system runs 24/7 without manual intervention on the Oracle Cloud Always Free VM.
6. All MLflow experiment runs, model versions, and production promotions are traceable via the MLflow UI without manual S3 inspection.
7. A `git push` to `main` triggers a full automated redeployment of the FastAPI service with zero manual steps.
8. All four AI Agents operate strictly within their designated analytical role — no Agent writes directly to S3, PostgreSQL, or triggers downstream Airflow tasks autonomously.

---

## 2. System Architecture & Data Flow

### 2.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    LAYER 1      │    │    LAYER 2      │    │    LAYER 3      │    │    LAYER 4      │
│  Data Ingestion │───▶│ NLP Processing  │───▶│ Hybrid Storage  │───▶│   API Serving   │
│                 │    │                 │    │                 │    │                 │
│ • Scrapers      │    │ • XLM-RoBERTa   │    │ • PostgreSQL    │    │ • FastAPI       │
│ • Airflow DAG   │    │   NER (PT+EN)   │    │   (structured)  │    │   RAG Pipeline  │
│ • AWS S3 Lake   │    │ • Multilingual  │    │ • Qdrant        │    │ • Bearer Auth   │
│ • IAM / CW      │    │   Embeddings    │    │   (vectors)     │    │ • GitHub Actions│
│                 │    │ • MLflow        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │                      │
         └──────────────────────┴──────────────────────┴──────────────────────┘
         ALL PIPELINE SERVICES ON ORACLE CLOUD FREE VM (4 OCPU · 24 GB RAM · Always Free)
FastAPI + REACT → GCP ARTIFACT REGISTRY · RAW DATA → AWS S3 · DOCS → GITHUB PAGES · PT + EN
```

### 2.2 Detailed Data Flow: Step-by-Step

#### Step 1 — Job Description Scraping (Daily Trigger)

An Apache Airflow DAG, scheduled at **02:00 UTC daily**, triggers Python scraping tasks. Each task targets a specific job board using `requests` for HTTP and `BeautifulSoup` for HTML parsing. Sources include both **English-language** boards (e.g., LinkedIn US, Remote.ok) and **Portuguese-language** boards (e.g., Gupy, Catho, InfoJobs BR).

A lightweight `langdetect` pass at ingestion time auto-tags each posting before storage.

Scraped records are normalized into the following JSON schema:

```json
{
  "job_id":              "string (SHA256 of source_url)",
  "title":               "string",
  "company":             "string",
  "location":            "string",
  "date_posted":         "ISO-8601 date",
  "raw_description_text":"string",
  "source_url":          "string",
  "language":            "string (en | pt)"
}
```

Each batch is written as a gzip-compressed JSONL file to:

```
s3://jmie-datalake/raw/YYYY/MM/DD/batch_<timestamp>.jsonl.gz
```

The Airflow task is marked complete only after a successful S3 `PutObject` confirmation.

#### Step 2 — NER Skill Extraction (Triggered Post-Scrape)

A downstream Airflow task reads the raw JSONL batch from S3. Each `raw_description_text` is passed through a Hugging Face token-classification pipeline backed by a fine-tuned **XLM-RoBERTa** NER model — a multilingual transformer that handles Portuguese and English natively in the same model weights.

The model version used is resolved at runtime from the **MLflow Model Registry** (Production stage alias), replacing manual `$MODEL_VERSION` env var management.

**Entity types extracted (bilingual):**

| Label | English Examples | Portuguese Examples |
|---|---|---|
| `LANGUAGE` | Python, Rust, Go | Python, Java, Kotlin |
| `FRAMEWORK` | FastAPI, React, Spring | FastAPI, Django, Angular |
| `CLOUD_PLATFORM` | AWS, GCP, Azure | AWS, Google Cloud, Azure |
| `DATABASE` | PostgreSQL, Redis | PostgreSQL, MySQL, MongoDB |
| `TOOL` | Docker, Terraform | Docker, Jenkins, Git |
| `CERTIFICATION` | AWS SAA, CKA | AWS, Google Cloud cert |
| `SOFT_SKILL` | Leadership, Communication | Liderança, Comunicação |
| `EXPERIENCE_LEVEL` | Senior, 5+ years | Sênior, Pleno, Júnior |

Extracted entities → **PostgreSQL** `skills_extracted` table.
Full description → **768-dim embedding** → upserted into **Qdrant** `job_postings` collection.

#### Step 3 — Structured Aggregation (PostgreSQL)

Post-NER, an Airflow SQL operator refreshes the `skill_trends_daily` materialized view. The `language` column enables filtering trends by market (Brazilian PT vs. global EN):

```sql
SELECT
  skill_name,
  skill_type,
  DATE(extracted_at)   AS trend_date,
  job_category,
  experience_level,
  language,
  COUNT(*)             AS mention_count
FROM skills_extracted
GROUP BY skill_name, skill_type, trend_date, job_category, experience_level, language;
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

**Phoenix Observability:** Every execution of this five-stage pipeline emits an OpenTelemetry trace to the Arize Phoenix server. Each stage is captured as a span with its own latency, inputs, and outputs — enabling full end-to-end visibility of retrieval quality, context relevance, and response faithfulness directly in the Phoenix UI.

### 2.3 Two-Tier Execution Model — Deterministic vs. Agentic

> **Architectural mandate (v2.0):** Airflow and PostgreSQL must remain strictly deterministic. AI Agents act exclusively as the non-deterministic analytical layer and are never permitted to write directly to S3, PostgreSQL, or trigger DAG tasks autonomously.

```
DETERMINISTIC TIER (Airflow + PostgreSQL)        NON-DETERMINISTIC TIER (AI Agents)
─────────────────────────────────────────        ────────────────────────────────────
• Scrape raw HTML  →  AWS S3                     • NER Annotation Assistant (Sprint 3)
• Load JSONL batches  →  PostgreSQL              • Smart Search Agent / Agentic RAG (Sprint 4)
• Refresh materialized views                     • Diagnostic Agent / Scraper Monitor (Sprint 5)
• Emit Slack / email alerts (alerting.py)        • Reporter Agent / Market Intelligence (Sprint 6)
• NEVER calls an LLM directly                    • Reads structured data produced by the left tier
• NEVER produces non-deterministic output        • Returns text or strictly typed JSON only
                                                 • NEVER writes to S3 or PostgreSQL directly
                                                 • NEVER triggers downstream DAG tasks
```

**Why this boundary is non-negotiable:**
- Airflow DAGs must be **idempotent and re-runnable**. LLM non-determinism inside a DAG task breaks this guarantee.
- PostgreSQL is the system of record. Agent hallucinations must never corrupt it — agents only read aggregated views.
- Token cost is impossible to bound if an Agent can recursively spawn further Agent calls. Hard limits (`max_iterations = 3` in Sprint 4) and the Raw SDK pattern (Sprints 5–6) enforce this structurally.

| Agent | Sprint | Framework | Hard Constraint |
|---|---|---|---|
| NER Annotation Assistant | 3 | PydanticAI | Typed JSON only — schema validation, no free-form output |
| Smart Search / Agentic RAG | 4 | LangGraph or Raw SDK | `max_iterations = 3` hard cap |
| Diagnostic Agent | 5 | Raw SDK | Human-in-the-Loop; no autonomous self-healing |
| Reporter Agent | 6 | Raw SDK | Single-shot LLM call; no tool loops |

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
| DE-08 | Language Detection | A `langdetect` pass runs on each scraped posting immediately after normalization. The detected language (`en` or `pt`) is stored in the `language` field before S3 write. Detection failures default to `en` with a warning log. |
| DE-09 | Bilingual Sources | Scraper must cover minimum 2 English-language sources and 2 Portuguese-language sources (e.g., Gupy, Catho). Sources are configured separately in `sources.yaml` under `en:` and `pt:` keys. |

### 3.2 Data Science & NLP Requirements

| ID | Requirement | Specification |
|---|---|---|
| DS-01 | Model Selection | **XLM-RoBERTa-base** for NER (multilingual, strong PT+EN performance). CPU-only. No GPU dependency. DistilBERT is explicitly replaced due to English-only limitation. |
| DS-02 | Entity Schema | Minimum 8 entity types across both languages: `LANGUAGE`, `FRAMEWORK`, `CLOUD_PLATFORM`, `DATABASE`, `TOOL`, `SOFT_SKILL`, `EXPERIENCE_LEVEL`, `CERTIFICATION`. Portuguese surface forms (e.g., *Sênior*, *Liderança*) must map to the same label space as English equivalents. |
| DS-03 | Training Data | Minimum **2,000 annotated English** + **1,500 annotated Portuguese** sentences. Both corpora annotated in Label Studio under separate projects but exported to a unified training format. |
| DS-04 | Model Evaluation | Token-level F1 ≥ 0.80 measured **per language** on separate held-out splits. A model that passes EN but fails PT must not be promoted to production. |
| DS-05 | Embedding Consistency | Multilingual embedding model: **`paraphrase-multilingual-MiniLM-L12-v2`** (768-dim, supports PT+EN natively). Version-pinned and identical at ingestion and query time. Replaces `all-MiniLM-L6-v2` (English-only). |
| DS-06 | Batch Inference | Minimum batch size of 32 samples per forward pass. No record-by-record inference. |
| DS-07 | MLflow Experiment Tracking | Every NER training run must log to MLflow: `model_architecture`, `language_mix`, `epochs`, `learning_rate`, `f1_en`, `f1_pt`, `f1_overall`, training dataset size, and a full confusion matrix artifact. |
| DS-08 | MLflow Model Registry | Trained model weights are registered in the MLflow Model Registry under the `jmie-ner` registered model name. Promotion workflow: `None → Staging → Production`. The Airflow inference task always loads the `Production` alias — no manual env var management. |
| DS-09 | Inference Logging | Each run logs: `model_version`, `mlflow_run_id`, `batch_size`, `total_records`, `inference_duration_s`, `entity_counts_by_type`, `language_distribution`. |

### 3.3 MLOps & Backend Requirements

| ID | Requirement | Specification |
|---|---|---|
| MLOPS-01 | Containerization | Every component runs as a Docker container via a single `docker-compose.yml` at project root, including the MLflow tracking server. |
| MLOPS-02 | CI/CD Pipeline | GitHub Actions with three job tiers: (1) lint + unit tests on every push to any branch; (2) integration tests on pull requests to `main`; (3) multi-platform Docker build + push to GCP Artifact Registry + SSH deploy to Oracle VM on merge to `main` only. |
| MLOPS-11 | Environment Split | Two runtime environments: `development` (local machine, mock scrapers, hot-reload, debug logging) and `production` (Oracle VM, real data, immutable images, structured JSON logs). Controlled via `ENV` env var and Docker Compose override files. |
| MLOPS-12 | Docker Compose Overrides | Three Compose files: `docker-compose.yml` (shared base), `docker-compose.dev.yml` (local overrides: source builds, volume mounts, mock scraper, Vite dev server), `docker-compose.prod.yml` (prod overrides: registry images, `restart: always`, real credentials). Never mix override files across environments. |
| MLOPS-13 | Branch Strategy | Two long-lived branches: `dev` (active development, triggers lint + unit tests only) and `main` (production, triggers full build + deploy pipeline). All feature work branches from `dev`. PRs from `dev → main` are the only path to production. |
| MLOPS-14 | Environment Variables | Three env files: `.env.dev` (local dev, fake credentials, committed as example only), `.env.prod` (real credentials, stored on Oracle VM only, never committed), `.env.example` (template documenting every variable, always committed and kept up to date). |
| MLOPS-15 | Package Management | `uv` is the sole Python package manager across all services (FastAPI, Airflow tasks, NLP training, scraper). No `pip`, `pip-compile`, or `virtualenv` calls anywhere in the codebase. Each Python service has a `pyproject.toml` + `uv.lock` lockfile committed to the repository. Dockerfiles install dependencies with `uv sync --frozen --no-dev` in production and `uv sync --frozen` in development. The CI runner installs `uv` via the official installer before any test step. |
| MLOPS-03 | Environment Config | All secrets via environment-specific `.env` files (`.env.dev` / `.env.prod`). No real credentials ever committed. `.env.example` documents every required variable with descriptions and safe placeholder values. |
| MLOPS-04 | FastAPI Endpoints | `GET /health`, `GET /skills/trending?lang=en\|pt`, `GET /skills/search?q=&lang=`, `GET /skills/cooccurrence?skill=&lang=`, `POST /query` (accepts queries in EN or PT). |
| MLOPS-05 | API Authentication | Bearer token required on all non-health endpoints. Keys stored as hashed values in `api_keys` table. |
| MLOPS-06 | Request Validation | All endpoints use Pydantic v2 models. Invalid requests return structured `422 Unprocessable Entity`. |
| MLOPS-07 | Logging Standard | Structured JSON logging via `structlog`. All logs include: `timestamp`, `service_name`, `level`, `request_id`, `message`. |
| MLOPS-08 | Data Persistence | PostgreSQL and Qdrant data mounted to named Docker volumes. Backup scripts included in weekly maintenance DAG. MLflow backend store also persisted to a named volume. |
| MLOPS-09 | RAG Observability | Arize Phoenix runs as a Docker Compose service (`:6006`). The FastAPI RAG pipeline instruments every `POST /query` call using the `opentelemetry-sdk` and `arize-phoenix` client. Each trace captures spans for: query encoding, Qdrant ANN search (with retrieved doc IDs and scores), PostgreSQL augmentation, prompt assembly, and synthesis. Phoenix UI is restricted to trusted IPs only. |
| MLOPS-10 | Project Documentation | All project documentation is written in Markdown under the `docs/` folder using MkDocs with the Material theme. A GitHub Actions job builds and deploys the static site to GitHub Pages on every merge to `main`. The live docs site is publicly accessible at `https://USERNAME.github.io/jmie`. |

### 3.4 Frontend Requirements

| ID | Requirement | Specification |
|---|---|---|
| FE-01 | Framework | React 18 with TypeScript. Bootstrapped with Vite. No Create React App. |
| FE-02 | Styling | Tailwind CSS for utility-first styling. No custom CSS frameworks or UI kits — keeps the bundle lean and the design fully controlled. |
| FE-03 | Charting | Recharts for all data visualisations — natively composable with React, zero external dependencies beyond the library itself. |
| FE-04 | State Management | React Query (TanStack Query) for all server-state fetching, caching, and background refetching. No Redux or Zustand needed at this scale. |
| FE-05 | API Client | A typed Axios client auto-generated from the FastAPI OpenAPI spec (`/openapi.json`). All API calls go through this client — no raw `fetch` calls scattered across components. |
| FE-06 | Routing | React Router v6. Three primary routes: `/` (Dashboard), `/query` (RAG Interface), `/skills` (Search & Comparison). |
| FE-07 | Authentication | API key stored in `localStorage` on first login. Passed as `Authorization: Bearer <key>` header on every request via an Axios interceptor. A `/login` route handles key entry and validation. |
| FE-08 | Language Toggle | A global language toggle (`EN` / `PT`) stored in React context. All API calls include the selected `lang` query parameter automatically. Charts and labels update to reflect the active language market. |
| FE-09 | Containerisation | React app built as a static bundle (`npm run build`) and served by an Nginx container on port `3000`. The Nginx config proxies `/api/*` requests to the `fastapi-app` service internally — no CORS configuration needed. |
| FE-10 | Multi-platform Build | The Nginx + React Docker image must be built as multi-platform (`linux/amd64,linux/arm64`) via `docker buildx` for compatibility with the Oracle ARM VM. |
| FE-11 | Responsive Design | All three views must be fully usable on screens ≥ 768px (tablet and desktop). Mobile support is a nice-to-have, not a requirement. |
| FE-12 | Error States | All API error states (401, 422, 500, network timeout) must be handled gracefully with a visible, non-technical error message. No raw JSON error objects exposed to the user. |

### 3.5 Frontend View Specifications

#### View 1 — Trending Skills Dashboard (`/`)

The landing page. Shows the current state of the job market at a glance.

- **Top Skills Bar Chart** — horizontal bar chart of the top 20 skills by mention count for the selected time window (7d / 30d / 90d). Filterable by `skill_type` (LANGUAGE, FRAMEWORK, CLOUD_PLATFORM, etc.) via a segmented control.
- **Skill Trend Line Chart** — line chart showing week-over-week mention counts for up to 5 user-selected skills. Skills are added via a typeahead search input.
- **Language Market Toggle** — switches all charts between EN (global) and PT (Brazilian) data. Both can be shown overlaid for direct comparison.
- **Last Updated Badge** — shows the timestamp of the most recent successful DAG run, sourced from the `/health` endpoint metadata.

#### View 2 — RAG Query Interface (`/query`)

The natural language query experience. The core differentiating feature of the product.

- **Query Input** — a large, prominent text area with placeholder examples in both EN and PT. A language selector sits beside the input. Submit on Enter or button click.
- **Response Panel** — displays the synthesised natural language answer with markdown rendering (via `react-markdown`). Streamed token-by-token if the generative backend supports streaming; otherwise displayed on completion.
- **Evidence Panel** — collapsible section below the answer showing the top-K retrieved job postings that grounded the response. Each card shows: job title, company, date posted, matched skills (highlighted), and a link to the source URL.
- **Query History** — a sidebar showing the last 10 queries in the current session. Click any previous query to reload its result. Stored in `sessionStorage` — clears on tab close.
- **Phoenix Trace Link** — a small "View trace →" link in the response footer that deep-links directly to the corresponding trace in the Phoenix UI (`:6006`). Only visible when Phoenix is reachable.

#### View 3 — Skill Search & Comparison (`/skills`)

A tool for investigating specific skills and comparing them side by side.

- **Skill Search** — a full-text search input backed by `GET /skills/search?q=`. Results show skill name, category, total mentions, and trend direction (↑ ↓ →) as a chip list.
- **Comparison Table** — select up to 4 skills from search results to add to a comparison table. Columns: skill name, category, total mentions (7d / 30d / 90d), rank, language split (EN % vs PT %). Sortable by any column.
- **Co-occurrence Chips** — for each selected skill, show the top 5 skills most frequently appearing alongside it in the same job posting, sourced from a `GET /skills/cooccurrence?skill=` endpoint (new endpoint added to FastAPI in Sprint 6).
- **Export Button** — downloads the current comparison table as a CSV file. Client-side generation via `papaparse` — no backend involvement.

---

## 4. Infrastructure & Cloud Strategy

### 4.1 Multi-Cloud Architecture Overview

JMIE uses three cloud providers, each doing the single job it is best and cheapest at:

| Provider | Role | Cost |
|---|---|---|
| **Oracle Cloud** | Primary compute — runs all Docker Compose services 24/7 on the Always Free VM | **$0/month forever** |
| **AWS** | Data lake (S3) and monitoring (CloudWatch) — industry-standard storage, reinforces CLF-C02 study | **~$0.20/month** |
| **GCP** | Docker image registry (Artifact Registry) and optional public API hosting (Cloud Run) | **~$0/month** (within free tier) |

This is not arbitrary multi-cloud sprawl — each provider is doing precisely what it offers for free or near-free. The compute cost problem that makes AWS EC2 expensive simply does not exist with Oracle's Always Free tier.

### 4.2 Oracle Cloud Always Free VM

The Oracle Cloud Always Free tier provides a VM that is more powerful than the AWS `t3.medium` originally specified, at zero cost and with no expiry date.

#### VM Specifications

| Resource | Always Free Allocation | JMIE Requirement |
|---|---|---|
| Shape | `VM.Standard.A1.Flex` (ARM) | ✅ |
| OCPUs | 4 | 4 (use all) |
| RAM | 24 GB | ~8 GB peak during NER inference |
| Boot disk | 200 GB Block Storage | ~40 GB estimated |
| Public IP | 1 static IP | ✅ Required |
| Region | 1 home region (choose closest) | `sa-saopaulo-1` recommended for BR |

#### Important — ARM Architecture

The Oracle Free VM runs on **ARM64 processors** (Ampere A1), not x86. All Docker images must be built as multi-platform to run both locally (x86) and on the VM (ARM64):

```bash
# Build and push a multi-platform image from your local machine
docker buildx build   --platform linux/amd64,linux/arm64   -t REGION-docker.pkg.dev/PROJECT/jmie/api:latest   --push ./api
```

All base images used by JMIE (Python, PostgreSQL, Qdrant, Airflow, MLflow) publish official ARM64 variants — no compatibility issues.

#### VM Setup Procedure

```bash
# 1. SSH into your new Oracle VM
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_ORACLE_PUBLIC_IP

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# 4. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 5. Clone your repository
git clone https://github.com/YOUR_USERNAME/jmie.git
cd jmie
cp .env.example .env
nano .env  # fill in real values

# 6. Start the full stack
docker compose up -d

# 7. Configure auto-start on VM reboot
sudo crontab -e
# Add: @reboot sleep 30 && cd /home/ubuntu/jmie && docker compose up -d
```

#### Oracle Cloud Firewall Configuration

Oracle has two firewall layers — both must be configured. Missing either one is the most common setup mistake.

**Layer 1 — Oracle VCN Security List** (in the Oracle Cloud Console):

```
Ingress Rules:
  Port 22    TCP    Source: YOUR_HOME_IP/32    (SSH — restrict to your IP)
  Port 8000  TCP    Source: 0.0.0.0/0          (FastAPI — public)
  Port 3000  TCP    Source: 0.0.0.0/0          (React frontend — public)
  Port 8080  TCP    Source: YOUR_HOME_IP/32    (Airflow UI — restrict)
  Port 5000  TCP    Source: YOUR_HOME_IP/32    (MLflow UI — restrict)
  Port 6006  TCP    Source: YOUR_HOME_IP/32    (Phoenix UI — restrict)
```

**Layer 2 — OS iptables** (run inside the VM):

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 6006 -j ACCEPT
sudo netfilter-persistent save
```

### 4.3 AWS Service Mapping (Storage & Monitoring Only)

AWS is used exclusively for S3 and CloudWatch. No EC2, no RDS, no managed services that incur meaningful cost.

| AWS Service | Role in JMIE | CLF-C02 Domain |
|---|---|---|
| **Amazon S3** | Immutable data lake for raw JSONL, processed batches, MLflow artifact store, and DAG audit logs. Versioning enabled on model prefix. | Storage |
| **AWS IAM** | IAM user with programmatic access keys scoped to the S3 bucket only. Keys stored as environment variables on the Oracle VM — never committed to the repository. | Security & Identity |
| **Amazon CloudWatch** | Custom metrics for DAG success/failure rate pushed from the Oracle VM via the AWS SDK `PutMetricData` call. | Monitoring |
| **S3 Lifecycle Policies** | Transition raw data >30 days to S3-IA. Delete files >90 days. Keeps storage cost near zero automatically. | Cost Optimization |

> **Note on CLF-C02:** Even though EC2 is no longer used, the project still meaningfully exercises S3, IAM, and CloudWatch — three of the most tested service categories on the exam. The architectural decision to use Oracle for compute while keeping AWS for storage is itself a valid topic for the Cloud Concepts domain (multi-cloud strategy, vendor lock-in avoidance).

### 4.4 GCP Service Mapping (Registry & Optional API Hosting)

| GCP Service | Role in JMIE | Cost |
|---|---|---|
| **Artifact Registry** | Stores versioned Docker images for `fastapi-app`. GitHub Actions pushes a new image on every merge to `main`. | 0.5 GB free · $0.10/GB after |
| **Cloud Run** *(optional)* | Serverless hosting for the FastAPI container as a publicly accessible endpoint. Scales to zero when idle. | 2M requests/month free · then $0.40/M |

#### When to use Cloud Run vs. direct Oracle VM

| Scenario | Recommendation |
|---|---|
| Personal use, querying from your own machine | Expose FastAPI directly on the Oracle VM public IP (`http://IP:8000`) |
| Portfolio demo, sharing the API with others | Deploy to Cloud Run for a clean public HTTPS URL (`https://jmie-api-xxx.run.app`) |
| Production / always-on public API | Cloud Run — handles scaling, zero-downtime deploys, and HTTPS automatically |

### 4.5 Cost Summary

| Component | Provider | Monthly Cost |
|---|---|---|
| VM — 4 OCPU, 24 GB RAM, 200 GB disk | Oracle Cloud | **$0 forever** |
| Static public IP | Oracle Cloud | **$0** |
| S3 raw data + model artifacts | AWS | **~$0.20** |
| CloudWatch custom metrics | AWS | **$0** (free tier permanent) |
| Artifact Registry storage | GCP | **$0** (within 0.5 GB free) |
| Cloud Run (if used) | GCP | **$0** (within free tier for personal use) |
| Arize Phoenix (self-hosted) | Oracle VM | **$0** (open-source, runs on-VM) |
| MkDocs + GitHub Pages | GitHub | **$0** (static site, free hosting) |
| React frontend (Nginx container) | Oracle VM | **$0** (runs on-VM, no extra service) |
| **Total** | | **~$0.20/month** |

### 4.6 Docker Compose Services

| Service | Image | Port(s) | Description |
|---|---|---|---|
| `airflow-scheduler` | `apache/airflow:2.x` | `8080` | Airflow web UI and scheduler. DAG definitions from mounted `./dags` volume. |
| `airflow-worker` | `apache/airflow:2.x` | — | Celery/sequential executor worker. Runs scraping, NER, and embedding tasks. |
| `postgres-app` | `postgres:15` | `5432` | Application DB: job metadata, extracted skills, API keys. |
| `postgres-airflow` | `postgres:15` | `5433` | Airflow metadata DB. Isolated from application data. |
| `qdrant` | `qdrant/qdrant:latest` | `6333`, `6334` | Vector DB. Port 6333 = REST API, 6334 = gRPC. Data persisted via named volume. |
| `fastapi-app` | `jmie/api:latest` | `8000` | Custom FastAPI image. RAG query, trending skills, and health endpoints. |
| `mlflow` | `ghcr.io/mlflow/mlflow:latest` | `5000` | MLflow tracking server. Experiment history, model registry, and artifact store. Backend store and artifact root both persisted to named Docker volumes (artifact root optionally backed by S3). |
| `phoenix` | `arizephoenix/phoenix:latest` | `6006` | Arize Phoenix LLM/RAG observability server. Receives OpenTelemetry traces from the FastAPI RAG pipeline. Stores trace history in a named Docker volume. UI restricted to trusted IPs. |
| `frontend` | `jmie/frontend:latest` | `3000` | Nginx serving the React SPA static build. Proxies `/api/*` to `fastapi-app` internally. Public-facing alongside the API. |
| `db-migrations` | `jmie/db:latest` | — | Database migrations container. Runs Alembic to apply schema updates and seed scripts, then exits. Invoked via the `migrations` Docker profile. |

### 4.7 Network & Security Configuration (Summary)

- **Oracle VCN Security List + OS iptables:** Both layers must allow ports `3000` (React frontend — public), `8000` (FastAPI — public), `8080` (Airflow — your IP only), `5000` (MLflow — your IP only), `6006` (Phoenix — your IP only), `22` (SSH — your IP only). See §4.2 for exact configuration commands.
- **Internal Docker services** (Qdrant `:6333`, PostgreSQL `:5432/:5433`) bind to the Docker bridge network only — never exposed on the host public interface.
- **AWS IAM credentials:** An IAM user (not a role, since Oracle VM cannot assume AWS roles) with `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `cloudwatch:PutMetricData` permissions scoped to the `jmie-datalake` bucket ARN. Keys stored in `.env` on the Oracle VM only. Never committed to the repository.
- **GCP credentials:** A GCP Service Account with `roles/artifactregistry.writer` bound to the `jmie` repository. JSON key stored as a GitHub Actions secret (`GCP_SA_KEY`) and as an environment variable on the Oracle VM for `docker compose pull`.
- **HTTPS:** Cloud Run provides automatic HTTPS when used. Direct Oracle VM access uses HTTP — acceptable for personal use given non-PII data.

---

## 5. Project Structure

The repository follows a monorepo layout with strict separation between pipeline stages, infrastructure configuration, ML artifacts, and the API application layer.

```
jmie/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Runs on every push: install uv → lint (ruff, eslint) → unit tests (pytest, vitest)
│       ├── integration.yml         # Runs on PRs to main: spins up dev stack in CI runner + integration tests
│       ├── cd.yml                  # Runs on merge to main: multi-platform build → push → SSH deploy to Oracle VM
│       └── docs.yml                # Runs on merge to main: mkdocs build → deploy to GitHub Pages
├── docker-compose.yml              # Single-command full-stack orchestration
├── .env.example                    # Template documenting all required environment variables
├── .gitignore
├── README.md                       # Setup guide, architecture overview, API docs
│
├── dags/                           # Apache Airflow DAG definitions
│   ├── jmie_daily_pipeline.py      # Main DAG: scrape → detect lang → NER → embed → aggregate
│   ├── jmie_maintenance.py         # Weekly DAG: Qdrant sweep, volume backup, cleanup
│   └── utils/
│       ├── s3_helpers.py           # S3 read/write utility functions
│       ├── db_helpers.py           # PostgreSQL connection pool + query helpers
│       └── alerting.py             # Slack/email alert wrappers for task failure
│
├── scraper/                        # Data ingestion layer
│   ├── pyproject.toml              # Scraper dependencies (requests, beautifulsoup4, langdetect)
│   ├── __init__.py
│   ├── base_scraper.py             # Abstract base class with retry logic + backoff
│   ├── sources/
│   │   ├── en/
│   │   │   ├── source_linkedin.py  # LinkedIn US scraper
│   │   │   └── source_remoteok.py  # Remote.ok scraper
│   │   └── pt/
│   │       ├── source_gupy.py      # Gupy (BR) scraper
│   │       └── source_catho.py     # Catho (BR) scraper
│   ├── normalizer.py               # Raw HTML → canonical JSON schema (adds `language` field)
│   ├── lang_detector.py            # langdetect wrapper; classifies en|pt; defaults to en on failure
│   ├── deduplicator.py             # job_id hash check before DB/S3 write
│   └── config/
│       └── sources.yaml            # Job board URLs keyed by language: en: [...] pt: [...]
│
├── nlp/                            # NLP processing layer
│   ├── pyproject.toml              # NLP package dependencies (torch, transformers, sentence-transformers)
│   ├── __init__.py
│   ├── ner/
│   │   ├── train.py                # Fine-tuning script for XLM-RoBERTa NER (PT+EN)
│   │   ├── evaluate.py             # F1 evaluation per language on held-out splits
│   │   ├── predict.py              # Batch inference pipeline (min batch=32)
│   │   ├── entity_schema.py        # Entity label definitions (shared across both languages)
│   │   └── annotation/
│   │       ├── en/
│   │       │   ├── export_to_labelstudio.py
│   │       │   └── import_from_labelstudio.py
│   │       └── pt/
│   │           ├── export_to_labelstudio.py
│   │           └── import_from_labelstudio.py
│   ├── embeddings/
│   │   ├── encoder.py              # paraphrase-multilingual-MiniLM-L12-v2 wrapper (PT+EN)
│   │   └── qdrant_client.py        # Qdrant upsert, search, and collection management
│   └── registry/
│       └── model_loader.py         # Loads Production-stage model from MLflow Model Registry
│
├── mlflow/                         # MLflow tracking server configuration
│   ├── Dockerfile                  # Optional custom MLflow image
│   └── mlflow.env                  # MLflow env vars (backend store URI, artifact root)
│
├── phoenix/                        # Arize Phoenix observability configuration
│   └── phoenix.env                 # Phoenix env vars (port, persistence path, auth)

│
├── api/                            # FastAPI application layer
│   ├── Dockerfile                  # Multi-stage: uv sync --frozen --no-dev → slim runtime image
│   ├── pyproject.toml              # API package dependencies (FastAPI, Pydantic, structlog, etc.)
│   ├── main.py                     # FastAPI app factory, middleware registration
│   ├── routers/
│   │   ├── health.py               # GET /health — liveness probe
│   │   ├── skills.py               # GET /skills/trending?lang=, GET /skills/search?q=&lang=, GET /skills/cooccurrence?skill=
│   │   └── query.py                # POST /query — RAG pipeline (EN or PT input)
│   ├── rag/
│   │   ├── pipeline.py             # 5-stage RAG orchestrator
│   │   ├── retriever.py            # Qdrant ANN search wrapper
│   │   ├── augmenter.py            # PostgreSQL context enrichment (language-aware)
│   │   ├── synthesizer.py          # Generative response synthesis
│   └── instrumentation.py      # OpenTelemetry tracer setup; wraps all 5 RAG stages as spans
│   ├── models/
│   │   ├── requests.py             # Pydantic v2 request schemas (includes optional lang param)
│   │   └── responses.py            # Pydantic v2 response schemas
│   ├── auth/
│   │   └── api_key.py              # Bearer token validation middleware
│   └── core/
│       ├── config.py               # Settings loaded from environment variables
│       ├── database.py             # SQLAlchemy async session factory
│       └── logging.py              # structlog JSON logging configuration
│
├── db/                             # Database schema management (Alembic)
│   ├── Dockerfile                  # Builds db-migrations container
│   ├── pyproject.toml              # Dependencies (alembic, psycopg2-binary, etc.)
│   ├── alembic.ini                 # Alembic configuration
│   ├── env.py                      # SQLAlchemy/Alembic environment configuration
│   ├── init/                       # Initialisation SQL scripts (e.g. mlflow_db.sql)
│   ├── scripts/                    # Helper scripts for the container lifecycle
│   ├── seeds/                      # Data seeding scripts
│   └── versions/                   # Generated Alembic migration revisions
│
├── infrastructure/                 # Cloud provider configuration (all three)
│   ├── oracle/
│   │   ├── vm_setup.sh             # Full Oracle VM bootstrap: Docker, deps, clone repo, start stack
│   │   ├── firewall_rules.md       # Step-by-step VCN Security List + iptables commands
│   │   ├── crontab.txt             # @reboot auto-start entry for docker compose
│   │   └── deploy.sh               # Pull latest images + docker compose prod up (called by CI/CD)
│   ├── aws/
│   │   ├── iam_policy.json         # Least-privilege IAM policy (S3 + CloudWatch only)
│   │   ├── s3_lifecycle.json       # S3 lifecycle rules (IA transition + deletion)
│   │   └── cloudwatch_dashboard.json  # CloudWatch dashboard JSON template
│   └── gcp/
│       ├── artifact_registry.md    # Steps to create Artifact Registry repo + auth
│       ├── cloud_run.md            # Optional: deploy FastAPI to Cloud Run
│       └── service_account.json.example  # Template showing required IAM roles (no real keys)
│
├── tests/                          # Test suite
│   ├── unit/
│   │   ├── test_scraper.py         # Scraper normalization and deduplication logic
│   │   ├── test_lang_detector.py   # Language detection correctness (EN and PT samples)
│   │   ├── test_ner_predict.py     # NER batch inference correctness
│   │   └── test_api_routes.py      # FastAPI endpoint unit tests (mocked deps)
│   ├── integration/
│   │   ├── test_pipeline_e2e.py    # Full DAG run against a local test environment
│   │   └── test_rag_query.py       # RAG pipeline with live Qdrant + PostgreSQL
│   └── fixtures/
│       ├── sample_job_postings_en.json
│       ├── sample_job_postings_pt.json
│       ├── annotated_ner_samples_en.json
│       └── annotated_ner_samples_pt.json
│
├── frontend/                       # React SPA (TypeScript + Vite + Tailwind)
│   ├── Dockerfile                  # Multi-stage: node build → nginx serve · multi-platform
│   ├── nginx.conf                  # Nginx config: serve static files + proxy /api/* to fastapi
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx                # React entry point
│   │   ├── App.tsx                 # Router setup (/, /query, /skills, /login)
│   │   ├── api/
│   │   │   ├── client.ts           # Typed Axios client with Bearer auth interceptor
│   │   │   ├── skills.ts           # API calls: trending, search, cooccurrence
│   │   │   └── query.ts            # API calls: POST /query, GET /health
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # View 1: Trending skills bar + line charts
│   │   │   ├── QueryInterface.tsx  # View 2: RAG query input, response, evidence panel
│   │   │   ├── SkillSearch.tsx     # View 3: Search, comparison table, co-occurrence chips
│   │   │   └── Login.tsx           # API key entry + validation
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── TopSkillsBar.tsx      # Recharts horizontal bar — top 20 skills
│   │   │   │   ├── SkillTrendLine.tsx    # Recharts line — week-over-week for N skills
│   │   │   │   └── LanguageOverlay.tsx   # EN vs PT overlay toggle for charts
│   │   │   ├── query/
│   │   │   │   ├── QueryInput.tsx        # Text area + language selector + submit
│   │   │   │   ├── ResponsePanel.tsx     # Markdown-rendered answer + Phoenix trace link
│   │   │   │   ├── EvidenceCard.tsx      # Single retrieved job posting card
│   │   │   │   └── QueryHistory.tsx      # Session query history sidebar
│   │   │   ├── skills/
│   │   │   │   ├── SkillSearchInput.tsx  # Typeahead search backed by /skills/search
│   │   │   │   ├── ComparisonTable.tsx   # Sortable 4-skill comparison table + CSV export
│   │   │   │   └── CooccurrenceChips.tsx # Top-5 co-occurring skills per selected skill
│   │   │   └── shared/
│   │   │       ├── LanguageToggle.tsx    # EN/PT global toggle (React context)
│   │   │       ├── TimeWindowSelect.tsx  # 7d / 30d / 90d segmented control
│   │   │       ├── ErrorBanner.tsx       # Graceful API error display
│   │   │       └── LastUpdatedBadge.tsx  # Last DAG run timestamp
│   │   ├── context/
│   │   │   ├── LanguageContext.tsx       # Global EN/PT selection
│   │   │   └── AuthContext.tsx           # API key storage + auth state
│   │   └── hooks/
│   │       ├── useTrendingSkills.ts      # React Query hook for /skills/trending
│   │       ├── useSkillSearch.ts         # React Query hook for /skills/search
│   │       └── useRagQuery.ts            # React Query mutation for POST /query
│   └── public/
│       └── favicon.svg
│
├── docs/                           # MkDocs documentation source (deploys to GitHub Pages)
│   ├── mkdocs.yml                  # MkDocs config: site name, theme (Material), nav structure
│   ├── index.md                    # Homepage: project overview and quick-start
│   ├── architecture.md             # System architecture + data flow walkthrough
│   ├── setup/
│   │   ├── oracle_vm.md            # Step-by-step Oracle Cloud VM provisioning guide
│   │   ├── aws_s3.md               # S3 bucket setup + IAM policy guide
│   │   └── gcp_registry.md         # GCP Artifact Registry + Cloud Run setup guide
│   ├── api/
│   │   ├── endpoints.md            # All FastAPI endpoints with request/response examples
│   │   └── authentication.md       # API key generation and usage
│   ├── mlops/
│   │   ├── mlflow.md               # MLflow experiment tracking and model promotion guide
│   │   └── phoenix.md              # Phoenix RAG observability: traces, spans, UI walkthrough
│   ├── frontend.md                 # React app setup, local dev, component guide
│   └── contributing.md             # How to add a new job board source or entity type
│
├── notebooks/                      # Exploratory & experimental notebooks (not production)
│   ├── 01_eda_job_descriptions.ipynb
│   ├── 02_ner_training_experiments.ipynb   # Includes PT vs EN F1 comparison charts
│   ├── 03_rag_response_quality_eval.ipynb
│   └── 04_mlflow_experiment_comparison.ipynb
│
└── scripts/                        # Operational one-off scripts
    ├── backup_volumes.sh           # Docker volume backup to AWS S3 (PG + Qdrant + MLflow + Phoenix)
    ├── restore_volumes.sh          # Restore volumes from S3 backup onto Oracle VM
    ├── seed_api_key.py             # Generate and hash a new API key into the DB
    └── retrain_ner.sh              # End-to-end NER retrain + MLflow registration (uses uv run)
```

### 5.1 Key Architectural Decisions in the File Structure

**Monorepo with clear layer separation.** Each of the four pipeline layers (`dags/`, `scraper/`, `nlp/`, `api/`) maps directly to the architecture diagram, making it easy to reason about data flow and assign ownership.

**Single `docker-compose.yml` at root.** One command (`docker compose up -d`) starts the entire 8-service stack including MLflow and Phoenix. No developer needs to know about individual service configurations.

**`scraper/sources/en/` and `scraper/sources/pt/`.** Sources are separated by language folder, making it trivial to add new job boards per market without changing the scraping logic. Satisfies DE-07 and DE-09.

**`nlp/registry/model_loader.py` talks to MLflow, not S3 directly.** Production model resolution is fully delegated to the MLflow Model Registry. No `$MODEL_VERSION` env var management — MLflow's `Production` alias is the single source of truth.

**`mlflow/` as a first-class directory.** MLflow is not an afterthought — it has its own configuration folder alongside the other services, reinforcing that experiment tracking is part of the core engineering workflow.

**`infrastructure/` split into `oracle/`, `aws/`, and `gcp/`.** Each cloud provider has its own configuration folder. This makes the multi-cloud setup auditable and reproducible — a new contributor can read one folder and understand exactly what that provider is responsible for.

**`db/migrations/003_add_language_column.py`.** Schema changes are version-controlled. The bilingual extension is a clean, auditable migration, not a destructive alteration of the original schema.

**`tests/` split into `unit/` and `integration/`, with language-split fixtures.** Unit tests run on every push (fast). Integration tests run on merge to `main`. Fixtures are separated by language to make per-corpus F1 testing unambiguous.

**`uv` as a workspace-aware package manager across the entire monorepo.** A root-level `pyproject.toml` declares a `uv` workspace that includes `api/`, `nlp/`, `scraper/`, and any other Python package. A single `uv.lock` at the root pins every transitive dependency across all sub-packages — one lockfile, zero version drift between services. In Dockerfiles, `uv sync --frozen --no-dev` installs only production dependencies in milliseconds using `uv`'s compiled resolver. In CI, `curl -LsSf https://astral.sh/uv/install.sh | sh` installs `uv` in under 3 seconds before any test step — no caching of a heavyweight pip environment needed.

**`docker-compose.dev.yml` and `docker-compose.prod.yml` as override files, not separate full stacks.** The base `docker-compose.yml` defines every service once. The override files only declare the differences — a few `image:` vs `build:` lines, a few environment variables, and `restart: always` on prod. This means there is a single source of truth for the service topology, eliminating the drift that happens when two separate Compose files diverge over time.

**`JMIE_USE_MOCK_SCRAPER=true` as a dev escape hatch.** Rather than mocking at the HTTP level (which requires maintaining fake HTML fixtures for every job board), a single env flag in the Airflow worker switches the scraper layer to read from local JSONL fixtures instead of making real HTTP requests. This makes local DAG runs fast, deterministic, and free of rate-limiting concerns without any structural change to the pipeline code.

**Three GitHub Actions workflow files, not one.** `ci.yml` (fast, every push), `integration.yml` (medium, PRs only), `cd.yml` (slow, main only). Splitting them means a typo fix pushed to `dev` gets feedback in 90 seconds from the lint job — not 8 minutes waiting for a Docker build that was never needed.

**`frontend/src/api/client.ts` as the single API gateway.** All backend calls go through a typed Axios client generated from the FastAPI OpenAPI spec. This means if the backend changes a response shape, TypeScript compilation fails in the frontend immediately — catching integration drift at build time, not at runtime.

**`frontend/nginx.conf` proxying `/api/*` internally.** The React app never calls the FastAPI service across a public network boundary. Nginx on the same Docker bridge network proxies API requests internally — eliminating CORS configuration entirely and keeping the API service off the public internet if desired.

**`api/rag/instrumentation.py` as a dedicated module.** Phoenix OpenTelemetry instrumentation is isolated in its own file rather than scattered across the RAG pipeline stages. This keeps observability concerns separate from business logic and makes it trivial to disable tracing in test environments by swapping one import.

**`docs/` as a first-class directory with `mkdocs.yml` at its root.** Documentation lives alongside the code it describes, not in a separate wiki that goes stale. The GitHub Actions `docs.yml` workflow means the live site at GitHub Pages is always in sync with `main`. The Material theme provides a professional, searchable documentation site with zero custom CSS required.

---

## 6. Milestones & Sprints

Each sprint is two weeks with a defined, demonstrable deliverable. Sprints are strictly sequential.

### Sprint 1 — Infrastructure Foundations *(Weeks 1–2)*

| Deliverable | Acceptance Criteria |
|---|---|
| Oracle Cloud VM provisioned | `VM.Standard.A1.Flex` (4 OCPU, 24 GB RAM) running Ubuntu 22.04 LTS; Docker + Docker Compose installed; SSH access verified |
| Oracle firewall configured | VCN Security List AND OS iptables rules verified; ports 8000, 8080, 5000, 22 accessible as defined in §4.2 |
| AWS S3 bucket created | Versioning enabled, lifecycle rules configured, IAM user with scoped access keys created |
| GCP Artifact Registry created | Repository `jmie` created in chosen region; `docker push` from local machine succeeds |
| Docker Compose scaffolded | All 9 services defined (placeholder images, including Phoenix and frontend Nginx); `docker compose up` succeeds on Oracle VM |
| GitHub repo + branch structure | `main` and `dev` branches created; `.gitignore`, `.env.example`, `.env.dev`, `docker-compose.dev.yml`, `docker-compose.prod.yml` committed; three GitHub Actions workflows (`ci.yml`, `cd.yml`, `docs.yml`) scaffolded |
| **Sprint Deliverable** | All 9 containers running on the Oracle VM via `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`; same stack verified locally with `docker-compose.dev.yml`; S3 accessible from VM; first multi-platform image in GCP Artifact Registry; push to `dev` triggers `ci.yml`; merge to `main` triggers `cd.yml` |

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
| Annotation dataset | 2,000+ labeled English sentences + 1,500+ labeled Portuguese sentences in Label Studio; exported to unified training format |
| XLM-RoBERTa NER fine-tuned | F1 ≥ 0.80 measured per language on separate held-out splits; both must pass before promotion |
| MLflow experiment tracking | All training runs logged to MLflow with `f1_en`, `f1_pt`, hyperparameters, and confusion matrix artifact |
| MLflow Model Registry | Trained model registered under `jmie-ner`; manually promoted to `Production` stage after evaluation |
| NER Airflow task | Batch inference loads Production model from MLflow; writes to `skills_extracted` table with `language` field |
| Embedding pipeline | `paraphrase-multilingual-MiniLM-L12-v2` vectors upserted into Qdrant `job_postings` collection |
| **[AGENT] NER Annotation Assistant** | **Framework: PydanticAI.** Receives raw job description batches and outputs strictly typed JSON conforming to the Label Studio annotation schema. PydanticAI validation must raise an error — not silently pass — if the LLM returns malformed output. Agent runs as a pre-annotation step invoked by the human annotator workflow, never by the Airflow DAG directly. Output feeds `nlp/annotation/en/import_from_labelstudio.py` and `nlp/annotation/pt/import_from_labelstudio.py`. |
| **Sprint Deliverable** | End-to-end bilingual pipeline with full MLflow experiment history; all runs comparable in the MLflow UI; PydanticAI NER Annotation Assistant validated against Label Studio import schema |

### Sprint 4 — FastAPI & RAG Query Layer *(Weeks 7–8)*

| Deliverable | Acceptance Criteria |
|---|---|
| FastAPI skeleton | All 4 endpoints scaffold with Pydantic v2 models |
| Auth middleware | Bearer token validation tested; 401 on missing/invalid token |
| `/skills/trending` | Returns real data from `skill_trends_daily` materialized view |
| `POST /query` | Full 5-stage RAG pipeline executes; returns JSON with answer + cited evidence |
| Phoenix instrumentation | `opentelemetry-sdk` and `arize-phoenix` integrated into FastAPI RAG pipeline; all 5 stages visible as spans in Phoenix UI at `:6006` |
| Phoenix trace validation | A real `POST /query` call produces a complete trace tree in Phoenix showing latencies and retrieved document scores |
| **[AGENT] Smart Search Agent / Agentic RAG** | **Framework: LangGraph or Raw SDK Tool Calling.** Replaces the static 5-stage RAG pipeline with a routing state machine. The agent may call up to **3 tool hops** (`max_iterations = 3` hard cap — this is non-negotiable; infinite tool-calling loops cause unbounded token cost). Tools available to the agent: `qdrant_search`, `postgres_skill_trends`, `assemble_context`. The graph must be acyclic — no edge may create a loop back to a previously visited node. **Semantic caching is mandatory** on the `POST /query` endpoint: identical or near-identical user queries must be served from cache without hitting the LLM API. Recommended: `GPTCache` or a Redis-backed semantic similarity cache keyed on the query embedding. |
| **Sprint Deliverable** | Callable, fully observable Agentic RAG API with `max_iterations = 3` guardrail enforced at the framework level; semantic cache hit rate ≥ 80% on repeated queries; every query produces a Phoenix trace |

### Sprint 5 — MLOps Hardening & CI/CD *(Weeks 9–10)*

| Deliverable | Acceptance Criteria |
|---|---|
| `ci.yml` finalized | Lint + unit tests run on every push to any branch; job completes in under 2 minutes |
| `integration.yml` finalized | Docker dev stack spun up in GitHub Actions runner; integration tests (`test_pipeline_e2e.py`, `test_rag_query.py`) run against it; job gated on PRs to `main` only |
| `cd.yml` finalized | Multi-platform Docker image (`linux/amd64,linux/arm64`) for api and frontend built and pushed to GCP Artifact Registry; SSH action runs `deploy.sh` on Oracle VM with prod Compose override; zero-downtime rolling update |
| Cloud Run deploy *(optional)* | `gcloud run deploy` step in CI pipeline; FastAPI publicly accessible at a GCP-managed HTTPS URL |
| CloudWatch metrics | Custom DAG success/failure rate metrics visible in CloudWatch dashboard; pushed from Oracle VM via AWS SDK |
| VM auto-start on reboot | `@reboot` cron job verified; Docker Compose restarts automatically after an Oracle maintenance reboot |
| Airflow alerting | Email or Slack webhook fires on DAG task failure |
| Volume backups | `backup_volumes.sh` covers PostgreSQL, Qdrant, MLflow, and Phoenix volumes; verified upload to S3 backup prefix |
| MkDocs site | `docs/` folder populated with architecture, setup, API, MLflow, and Phoenix sections; Material theme configured |
| GitHub Pages deploy | `docs.yml` GitHub Actions workflow builds and deploys MkDocs site; live at `https://USERNAME.github.io/jmie` |
| **[AGENT] Diagnostic Agent / Scraper Monitor** | **Framework: Raw SDK (simple Python function invoking the LLM — zero framework overhead).** Reads Airflow task logs from the S3 audit prefix and CloudWatch metrics. Identifies patterns indicating scraper failure, rate-limiting, or schema drift across sources. **Autonomous self-healing is explicitly banned.** This is a Human-in-the-Loop (HITL) diagnostic process: the agent produces a plain-language diagnostic summary and sends it as a Slack alert payload via `dags/utils/alerting.py`. A human engineer reads the alert and decides on remediation. The agent never modifies DAG configuration, restarts tasks, or alters source configs autonomously. Token cost is bounded by the single-shot invocation pattern. |
| **Sprint Deliverable** | Full zero-touch CI/CD + live public documentation; Slack Diagnostic Agent alerts firing on scraper anomalies; human-readable diagnostic summaries validated in staging |

### Sprint 6 — React Frontend *(Weeks 11–12)*

| Deliverable | Acceptance Criteria |
|---|---|
| Project scaffold | Vite + React 18 + TypeScript + Tailwind CSS initialised; Dockerfile (multi-stage, multi-platform) builds successfully; Nginx serves the static bundle on `:3000` |
| Typed API client | Axios client generated from FastAPI `/openapi.json`; Bearer auth interceptor tested; all 5 endpoints callable from the browser |
| `GET /skills/cooccurrence` endpoint | New FastAPI endpoint implemented and tested; returns top-N co-occurring skills for a given skill name and language |
| View 1 — Trending Dashboard | Top Skills bar chart and Skill Trend line chart rendering real data; time window selector (7d/30d/90d) and skill type filter functional; EN/PT language toggle switches data source |
| View 2 — RAG Query Interface | Query input submits to `POST /query`; response rendered with markdown; evidence cards show retrieved postings with matched skill highlights; query history sidebar persists in `sessionStorage`; Phoenix trace link visible in response footer |
| View 3 — Skill Search & Comparison | Typeahead search calls `/skills/search`; up to 4 skills addable to comparison table; co-occurrence chips rendered per skill; CSV export working client-side |
| Login view | API key entry form; key validated against `GET /health`; stored in `localStorage`; Axios interceptor attaches key to all requests; 401 responses redirect to `/login` |
| Error handling | All API error states (401, 422, 500, timeout) display a non-technical `ErrorBanner` — no raw JSON visible to the user |
| CI/CD extended | Frontend Docker image built multi-platform and pushed to GCP Artifact Registry in the existing `ci_cd.yml` workflow; Oracle VM deploys frontend alongside API on merge to `main` |
| Documentation | `docs/frontend.md` populated with local dev setup, component structure, and ENV variable guide |
| **[AGENT] Reporter Agent / Market Intelligence** | **Framework: Raw SDK (direct Python function calling the production LLM — no agent framework overhead).** Reads pre-aggregated data from the `skill_trends_daily` PostgreSQL materialized view (via a parameterized SQL query) and synthesizes a concise, human-readable weekly market intelligence report. The report is generated as a single-shot LLM call — no tool loops, no intermediate steps. Output is returned as a structured JSON payload `{"report": "...", "period": "...", "language": "en|pt"}` and exposed via a new `GET /report/weekly?lang=en|pt` FastAPI endpoint. Report generation is triggered once per week by a dedicated Airflow run (read-only DAG task: it queries PostgreSQL and passes results to the Agent function). |
| **Sprint Deliverable** | A live, publicly accessible React dashboard at `http://ORACLE_IP:3000` showing real job market data — fully functional across all three views; `GET /report/weekly` endpoint returning AI-generated market narrative backed by real PostgreSQL trend data |

---

## 7. Out of Scope

The following items are explicitly excluded from JMIE v1.0. Any scope change request during active sprints requires formal discussion and a documented decision.

### 7.1 User Interface

- A React SPA is now in scope (Sprint 6). See §3.4 and §3.5 for full requirements.
- No additional frontend frameworks (Streamlit, Grafana, Metabase) beyond the React SPA are in scope.
- No real-time push updates (WebSockets, SSE) — all data fetching is polling-based via React Query.

### 7.2 Advanced ML Capabilities

- Salary prediction, job recommendation systems, or any model beyond NER is out of scope.
- LLM fine-tuning: The generative component uses a pre-trained model. Fine-tuning the generative model is not in scope.
- Real-time streaming ingestion (Kafka, Kinesis): All ingestion is batch-based on a daily schedule.
- Language support beyond Portuguese and English is out of scope for v1.0.

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

## 8. Cost, AI Infrastructure & Multi-Model Strategy

> **Mandate (v2.0):** All AI Agent LLM calls must flow through the tiered model strategy defined below. No agent may use a model outside this stack without an explicit architecture decision record.

### 8.1 LLM Tier Stack

| Tier | Model Family | Usage Context | Cost |
|---|---|---|---|
| **Development / Local** | **Llama** (any locally served variant via Ollama or llama.cpp) | All local development and automated testing. Zero API calls, zero token cost. Agents must be configurable to use a local Llama endpoint by setting `LLM_PROVIDER=local` in `.env.dev`. | **$0** |
| **Production Backbone** | **Google Gemini** (via AI Studio API) | Primary production engine for all four agents. Gemini's generous free tier handles high-volume routing and processing at scale. Default for all agents when `LLM_PROVIDER=gemini` (set in `.env.prod`). | **$0** (within AI Studio free tier) |
| **Fallback / Specialized** | **DeepSeek** (API) | Fallback for highly complex multi-step reasoning tasks, or when Gemini production rate limits are hit. Activated automatically via `LLM_PROVIDER=deepseek` or via a runtime fallback wrapper that catches `429 Too Many Requests` from the Gemini API. | Low cost per token; reserved for fallback use only |

**Implementation note:** All agents must accept an `llm_provider` parameter resolved from environment variables. No model name must ever be hardcoded in agent logic. The provider abstraction layer (`api/ai/provider.py`) exposes a single `call_llm(prompt, provider)` interface used by all four agents.

### 8.2 Agent Framework Mandate Per Sprint

> **Banned framework:** **CrewAI** (and any other heavy multi-agent roleplay framework) is **explicitly prohibited** across all sprints. These frameworks force agents to call each other in recursive roleplay loops, making token consumption non-deterministic and impossible to bound within the $3/month infrastructure budget. Violations of this policy must be flagged as blocking issues in code review.

| Sprint | Agent | **Mandated Framework** | Rationale |
|---|---|---|---|
| **Sprint 3** | NER Annotation Assistant | **PydanticAI** | Guarantees strictly typed JSON output for Label Studio. If the LLM returns schema-invalid output, PydanticAI raises a hard validation error — garbage data never silently enters the annotation pipeline. |
| **Sprint 4** | Smart Search Agent / Agentic RAG | **LangGraph** or **Raw SDK Tool Calling** | Models the RAG routing as an explicit, acyclic state machine. `max_iterations = 3` is enforced at the graph level — a cycle cannot exist because the graph edges don't include one. Raw SDK Tool Calling is an acceptable alternative if the routing logic is simple enough to not warrant a full graph. |
| **Sprint 5** | Diagnostic Agent / Scraper Monitor | **Raw SDK** (Python function → LLM call) | Single-shot diagnostic generation. A full agent framework adds zero capability and measurable token overhead for a function that reads logs and returns a Slack message. |
| **Sprint 6** | Reporter Agent / Market Intelligence | **Raw SDK** (Python function → LLM call) | Single-shot report generation from pre-aggregated SQL results. Same rationale as Sprint 5. Any agentic looping is unnecessary and wasteful. |

### 8.3 Semantic Caching Mandate (Sprint 4)

The `POST /query` endpoint **must** implement semantic caching to avoid repeatedly hitting the LLM API for identical or near-identical user queries. This is a hard requirement, not a nice-to-have.

- **Mechanism:** Cache keyed on the query's dense vector embedding (cosine similarity threshold: ≥ 0.95 = cache hit). On a cache hit, return the cached response immediately — skip the LLM call entirely.
- **Recommended implementations:** `GPTCache` (drop-in wrapper) or a Redis-backed semantic cache using the existing `redis` Docker Compose service.
- **Acceptance criterion:** Cache hit rate ≥ 80% on a benchmark set of 50 repeated queries across a 7-day window.
- **Observability:** Cache hits and misses must be tracked as custom CloudWatch metrics and visible in the Phoenix trace as a span attribute (`cache_hit: true|false`).

---

## Tech Stack Summary

| Category | Technology | Version / Notes |
|---|---|---|
| **Orchestration** | Apache Airflow | 2.x · Docker Compose service |
| **Ingestion** | Python requests + BeautifulSoup4 | Standard library HTTP + HTML parsing |
| **Language Detection** | `langdetect` | Classifies `en` / `pt` at ingestion time |
| **Storage — Raw** | AWS S3 | Partitioned JSONL · Lifecycle rules |
| **ML Framework** | PyTorch + Hugging Face Transformers | CPU-only inference |
| **NER Model** | XLM-RoBERTa-base fine-tuned | Bilingual PT+EN · F1 ≥ 0.80 per language |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` | 768-dim · Multilingual PT+EN |
| **Experiment Tracking** | MLflow | Tracking server + Model Registry · Docker service on `:5000` |
| **Frontend** | React 18 + TypeScript + Vite | Tailwind CSS · Recharts · React Query · Axios · served by Nginx on `:3000` |
| **RAG Observability** | Arize Phoenix | Open-source LLM/RAG tracing · OpenTelemetry · Docker service on `:6006` |
| **Documentation** | MkDocs + Material theme | Markdown source in `docs/` · Auto-deployed to GitHub Pages |
| **Vector DB** | Qdrant | HNSW index · containerized |
| **Relational DB** | PostgreSQL 15 | Containerized (RDS optional) |
| **API Framework** | FastAPI + Pydantic v2 | Async · Bearer auth · `?lang=en\|pt` filter |
| **Containerization** | Docker + Docker Compose | 9-service · Compose override pattern (base + dev + prod) · multi-platform build |
| **Env Management** | `.env.dev` / `.env.prod` + Compose overrides | Dev: mock scraper, hot-reload, debug · Prod: real data, immutable images |
| **Package Manager** | `uv` | Workspace lockfile (`uv.lock`) · `uv sync --frozen` in Docker · replaces pip entirely |
| **CI/CD** | GitHub Actions | Lint → Build → Push → Deploy |
| **Compute Host** | Oracle Cloud Always Free VM | `VM.Standard.A1.Flex` · 4 OCPU · 24 GB RAM · ARM64 · Ubuntu 22.04 · $0/month |
| **Image Registry** | GCP Artifact Registry | Multi-platform images (amd64 + arm64) · `docker buildx` |
| **API Hosting** *(opt.)* | GCP Cloud Run | Serverless · HTTPS · Scales to zero · Free tier |
| **Monitoring** | AWS CloudWatch | Custom DAG metrics pushed from Oracle VM |
| **Identity** | AWS IAM | Least-privilege instance role |
| **LLM — Development** | Llama (local via Ollama / llama.cpp) | Zero-cost local dev; activated via `LLM_PROVIDER=local` |
| **LLM — Production** | Google Gemini (AI Studio API) | Primary production backbone; generous free tier; activated via `LLM_PROVIDER=gemini` |
| **LLM — Fallback** | DeepSeek (API) | Complex reasoning fallback; triggered on rate-limit or explicit routing; `LLM_PROVIDER=deepseek` |
| **Agent Framework — Sprint 3** | PydanticAI | Strictly typed JSON output for Label Studio annotation pipeline |
| **Agent Framework — Sprint 4** | LangGraph or Raw SDK | Acyclic RAG routing state machine; `max_iterations = 3` hard cap |
| **Agent Framework — Sprints 5–6** | Raw SDK (Python + LLM call) | Single-shot diagnostic and reporting; zero framework overhead |
| **Semantic Cache — Sprint 4** | GPTCache or Redis semantic cache | Keyed on query embedding; ≥ 0.95 cosine similarity = cache hit; ≥80% hit rate target |

---

*Document Control: JMIE PRD v2.0 · Senior AI PM & Lead MLOps Engineering*
*v2.0 changes: Hybrid Agentic Architecture · Four AI Agents mapped to Sprints 3–6 · Multi-Model Tiered Strategy (Llama/Gemini/DeepSeek) · Agent framework mandates per sprint (PydanticAI · LangGraph · Raw SDK) · CrewAI explicitly banned · Semantic caching mandated for Sprint 4 · Two-Tier Execution Model (Airflow deterministic · Agents analytical-only)*
*v1.6 changes: `uv` as Python package manager (MLOPS-15) · `pyproject.toml` + `uv.lock` across all services · Dockerfile `uv sync --frozen` · uv in CI runner and Oracle VM bootstrap*