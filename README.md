# JMIE - Job Migration and Integration Engine

A powerful job scraping and integration system designed to aggregate job opportunities from various platforms including LinkedIn, RemoteOK, Gupy, and ProgramaThor.

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and runner)
- `make` (Optional, for simplified command execution)

### 🛠️ Environment Setup

You can set up the development environment using either the provided `Makefile` or raw `docker compose` commands.

#### Option 1: Using Makefile (Recommended)

```bash
# Start the development stack in the background
make up-dev

# Run database migrations to set up the schema
make migrate
```

#### Option 2: Raw Commands

If you don't have `make` installed, use these equivalent commands:

```bash
# Start the development stack
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Run database migrations
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev --profile migrations run --rm db-migrations
```

---

## 🕷️ Running Scrapers

The project uses `uv` to manage dependencies and run scripts. You can run individual scrapers locally for testing:

### LinkedIn Scraper
```bash
uv run python -m scraper.sources.multi_language.source_linkedin
```

### RemoteOK Scraper (English)
```bash
uv run python -m scraper.sources.en.source_remoteok
```

### Gupy Scraper (Portuguese)
```bash
uv run python -m scraper.sources.pt.source_gupy
```

### ProgramaThor Scraper (Portuguese)
```bash
uv run python -m scraper.sources.pt.source_programathor
```

---

## 🌿 Git Best Practices

To keep the project history clean and collaborative, please follow this workflow:

1.  **Sync with upstream main**:
    Always ensure your local `main` branch is up to date before starting new work.
    ```bash
    git fetch origin
    git pull origin main
    ```

2.  **Work on feature branches**:
    Never commit directly to `main`. Create a descriptive branch for your changes:
    ```bash
    git checkout -b feature/your-awesome-feature
    # or for bugfixes
    git checkout -b fix/issue-description
    ```

3.  **Commitment to Quality**:
    - Write clear, concise commit messages.
    - Commit small chunks of related changes.
    - Ensure your code passes local tests before pushing.

4.  **Open a Pull Request**:
    Once your feature is ready, push your branch and open a PR for review.
