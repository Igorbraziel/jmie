# Welcome to JMIE

**Job Market Intelligence Engine** is an end-to-end automated ML pipeline system that scrapes, analyzes, and exposes market intelligence about technology job skills across English and Portuguese-speaking markets.

## Features

- **🔄 Automated Daily Pipeline**: Apache Airflow orchestrates scrapers, NLP processing, and embedding generation
- **🌍 Bilingual NLP**: XLM-RoBERTa fine-tuned for English and Portuguese entity extraction
- **🔍 RAG Query Interface**: Natural language queries powered by Retrieval-Augmented Generation
- **📊 Real-time Dashboards**: React SPA with interactive trending charts
- **📈 Multi-language Support**: Separate analysis for English (global) and Portuguese (Brazilian market) job posts
- **🚀 Cloud-Agnostic**: Multi-cloud architecture using Oracle (compute), AWS (storage), GCP (registry)
- **💰 Cost-Effective**: ~$0.20/month total infrastructure cost

## Quick Links

- [Architecture Overview](architecture.md) — Understand the four-layer pipeline
- [Setup Guide](setup/oracle_vm.md) — Deploy to Oracle Cloud
- [API Documentation](api/endpoints.md) — REST API reference
- [MLflow & Model Registry](mlops/mlflow.md) — Experiment tracking and model versioning
- [Frontend Guide](frontend.md) — React SPA development

## Getting Started

### Local Development

```bash
# Install dependencies
uv sync

# Start full stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Access services
# FastAPI:     http://localhost:8000
# Frontend:    http://localhost:5173
# Airflow UI:  http://localhost:8080
```

### Run Tests

```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=api --cov=nlp --cov=scraper
```

### Code Quality

```bash
# Format & lint
uv run ruff format .
uv run ruff check .
uv run mypy api/ nlp/ scraper/
```

## Core Concepts

### Four-Layer Architecture

1. **Layer 1 — Data Ingestion**: Web scrapers → AWS S3 data lake
2. **Layer 2 — NLP**: Entity extraction (NER) → Multilingual embeddings
3. **Layer 3 — Storage**: PostgreSQL (structured) + Qdrant (vectors)
4. **Layer 4 — API**: FastAPI RAG endpoint + React dashboard

### Entity Types Extracted

- `LANGUAGE` (Python, Java, Rust, etc.)
- `FRAMEWORK` (FastAPI, React, Spring, etc.)
- `CLOUD_PLATFORM` (AWS, GCP, Azure, etc.)
- `DATABASE` (PostgreSQL, MongoDB, Redis, etc.)
- `TOOL` (Docker, Terraform, Jenkins, etc.)
- `CERTIFICATION` (AWS SAA, CKA, etc.)
- `SOFT_SKILL` (Leadership, Communication, etc.)
- `EXPERIENCE_LEVEL` (Senior, Mid-level, Junior, etc.)

## Deployment

### Production Deployment to Oracle Cloud

```bash
# 1. Provision VM via Oracle Cloud Console
# 2. Run bootstrap script
ssh ubuntu@YOUR_ORACLE_IP < infrastructure/oracle/vm_setup.sh

# 3. CI/CD automatically deploys on git push to main
git push origin main
```

### Infrastructure Costs

- **Oracle Cloud**: $0/month (Always Free VM)
- **AWS S3**: ~$0.20/month
- **GCP**: $0/month (free tier)
- **Total**: ~$0.20/month

## Project Status

**Current**: Sprint 1 - Infrastructure Foundations ✅

Upcoming sprints:
- Sprint 2: Data Ingestion Pipeline
- Sprint 3: NLP & Embeddings
- Sprint 4: FastAPI RAG Layer
- Sprint 5: MLOps Hardening & CI/CD
- Sprint 6: React Frontend

See [JMIE_PRD.md](../JMIE_PRD.md) for detailed milestone breakdown.

## Contributing

1. Clone the repository
2. Create a feature branch from `dev`
3. Make changes and add tests
4. Submit a pull request to `dev`
5. After review, merge to `main` for production

See [CLAUDE.md](../CLAUDE.md) for development guidelines.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | Apache Airflow 2.x |
| ML Framework | PyTorch + Hugging Face |
| NER Model | XLM-RoBERTa (bilingual) |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 |
| Vector DB | Qdrant (HNSW) |
| Relational DB | PostgreSQL 15 |
| API | FastAPI + Pydantic v2 |
| Frontend | React 18 + TypeScript |
| Observability | Arize Phoenix + OpenTelemetry |
| CI/CD | GitHub Actions |
| Compute | Oracle Cloud Always Free VM |

## Support

- Check [documentation](../docs/) for detailed guides
- Review [Q&A in issues](https://github.com/yourusername/jmie/issues)
- See [contributing guidelines](contributing.md)

---

**License**: MIT
**Status**: Active Development
**Version**: 0.1.0
