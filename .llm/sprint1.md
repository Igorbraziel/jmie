# JMIE — Sprint 1 Implementation Plan
## Infrastructure Foundations · Weeks 1–2

> **Goal:** All 9 containers running on Oracle Cloud · S3 accessible from the VM · First multi-platform Docker image in GCP Artifact Registry · GitHub repo with branch structure and CI/CD pipelines wired up.
>
> **Estimated time:** 15–20 hours total across 2 weeks  
> **Prerequisites:** A computer with Docker Desktop, Git, Python 3.11+, and Node.js 20+ installed locally.

---

## Overview

```
Phase 1 · Local machine setup          (~2h)   Steps 1–3
Phase 2 · GitHub repository            (~1h)   Steps 4–5
Phase 3 · AWS S3 + IAM                 (~1h)   Step 6
Phase 4 · GCP Artifact Registry        (~1h)   Step 7
Phase 5 · Oracle Cloud VM              (~3h)   Steps 8–10
Phase 6 · Docker Compose scaffold      (~4h)   Steps 11–13
Phase 7 · GitHub Actions CI/CD         (~3h)   Steps 14–16
Phase 8 · Verification                 (~1h)   Step 17
```

---

## Phase 1 · Local Machine Setup

### Step 1 — Install required tools

Make sure everything is installed before touching any cloud provider.

```bash
# Verify Docker Desktop is running
docker --version        # should be 24+
docker compose version  # should be 2.x

# Verify Git
git --version

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env   # or restart your terminal
uv --version              # should be 0.4+

# Install Node.js 20+ (for the React frontend in later sprints — install now)
# macOS:  brew install node
# Ubuntu: sudo apt install nodejs npm
node --version  # should be 20+

# Install the GCP CLI (gcloud)
# macOS:  brew install --cask google-cloud-sdk
# Ubuntu: https://cloud.google.com/sdk/docs/install
gcloud --version

# Install the AWS CLI
# macOS:  brew install awscli
# Ubuntu: sudo apt install awscli
aws --version
```

> **Checkpoint:** All five commands return a version number without errors.

---

### Step 2 — Install Docker buildx (multi-platform builder)

The Oracle VM is ARM64. Your laptop is likely x86. You need `buildx` to build images that run on both.

```bash
# Create and activate a multi-platform builder
docker buildx create --name jmie-builder --use
docker buildx inspect --bootstrap

# Verify QEMU emulation is available (needed to build ARM images on x86)
docker buildx ls
# You should see: linux/amd64, linux/arm64 listed under jmie-builder
```

> **Checkpoint:** `docker buildx ls` shows `linux/arm64` as a supported platform.

---

### Step 3 — Generate SSH key pair for Oracle VM

You'll need this in Step 8 when creating the Oracle VM.

```bash
# Generate a dedicated key for this project
ssh-keygen -t ed25519 -C "jmie-oracle" -f ~/.ssh/jmie_oracle

# This creates two files:
#   ~/.ssh/jmie_oracle       (private key — never share or commit)
#   ~/.ssh/jmie_oracle.pub   (public key — you'll paste this into Oracle)

# Print the public key — keep this tab open for Step 8
cat ~/.ssh/jmie_oracle.pub
```

> **Checkpoint:** You can see a line starting with `ssh-ed25519` when you print the public key.

---

## Phase 2 · GitHub Repository

### Step 4 — Create the GitHub repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `jmie`
3. Visibility: **Private** (you can make it public later once the project is working)
4. **Do not** initialise with a README — you'll push the structure yourself
5. Click **Create repository**

---

### Step 5 — Initialise the repository locally

```bash
# Create the project directory
mkdir jmie && cd jmie

# Initialise git
git init
git branch -M main

# Create the branch structure
git checkout -b dev        # this is your working branch
# main = production (protected, only CI/CD deploys here)
# dev  = development (you push here daily)

# Connect to GitHub
git remote add origin https://github.com/YOUR_USERNAME/jmie.git
```

Now create the root-level files you need before the first commit:

```bash
# .gitignore
cat > .gitignore << 'EOF'
# Environment files — never commit real credentials
.env.prod
.env
*.env.local

# Python
__pycache__/
*.pyc
*.pyo
.venv/
dist/
*.egg-info/

# uv
.uv/

# Node
node_modules/
frontend/dist/
frontend/.vite/

# Docker
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
EOF

# .env.example — template, safe to commit
cat > .env.example << 'EOF'
# ── Environment ───────────────────────────────
ENV=development

# ── AWS ───────────────────────────────────────
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=jmie-datalake

# ── GCP ───────────────────────────────────────
GCP_PROJECT_ID=your_gcp_project_id
GCP_REGION=us-central1
GCP_ARTIFACT_REPO=jmie

# ── PostgreSQL (app) ──────────────────────────
POSTGRES_APP_USER=jmie
POSTGRES_APP_PASSWORD=changeme
POSTGRES_APP_DB=jmie
POSTGRES_APP_PORT=5432

# ── PostgreSQL (Airflow) ──────────────────────
POSTGRES_AIRFLOW_USER=airflow
POSTGRES_AIRFLOW_PASSWORD=changeme
POSTGRES_AIRFLOW_DB=airflow
POSTGRES_AIRFLOW_PORT=5433

# ── Airflow ───────────────────────────────────
AIRFLOW__CORE__FERNET_KEY=generate_with_python_-c_"from_cryptography.fernet_import_Fernet;print(Fernet.generate_key().decode())"
AIRFLOW__WEBSERVER__SECRET_KEY=changeme
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=changeme

# ── Qdrant ────────────────────────────────────
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# ── MLflow ────────────────────────────────────
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=
MLFLOW_ARTIFACT_ROOT=s3://jmie-datalake/mlflow-artifacts

# ── FastAPI ───────────────────────────────────
API_SECRET_KEY=changeme
API_HOST=0.0.0.0
API_PORT=8000

# ── Phoenix ───────────────────────────────────
PHOENIX_PORT=6006

# ── NLP ───────────────────────────────────────
MODEL_VERSION=latest
JMIE_USE_MOCK_SCRAPER=true
JMIE_S3_WRITE=false
EOF

# .env.dev — safe defaults for local development
cp .env.example .env.dev
# The defaults in .env.example are already dev-appropriate
# Just make sure JMIE_USE_MOCK_SCRAPER=true and JMIE_S3_WRITE=false

# .env.prod.example — reminder of what prod needs
cp .env.example .env.prod.example
# Add a comment at the top
sed -i '1s/^/# PRODUCTION values — fill in real credentials, store on Oracle VM only, never commit\n/' .env.prod.example
```

Push the first commit:

```bash
git add .gitignore .env.example .env.dev .env.prod.example
git commit -m "chore: initialise repo with env templates and gitignore"
git push -u origin dev
```

Now protect `main` on GitHub:
1. Go to your repo → **Settings** → **Branches**
2. Click **Add branch protection rule**
3. Branch name pattern: `main`
4. Check **Require a pull request before merging**
5. Check **Require status checks to pass before merging**
6. Save

> **Checkpoint:** `dev` branch exists on GitHub. Pushing to `main` directly is blocked.

---

## Phase 3 · AWS S3 + IAM

### Step 6 — Create the S3 bucket and IAM user

**6a — Create S3 bucket**

1. Log into [AWS Console](https://console.aws.amazon.com) → S3 → **Create bucket**
2. Bucket name: `jmie-datalake` (must be globally unique — add a suffix like `-yourname` if taken)
3. Region: `us-east-1` (keep all AWS resources in one region — free intra-region transfer)
4. **Block all public access:** ✅ On
5. **Versioning:** Enable (important for model artifact prefix)
6. Click **Create bucket**

**6b — Set lifecycle rules**

Inside your new bucket → **Management** → **Create lifecycle rule**:

- Rule name: `raw-data-lifecycle`
- Applies to: prefix `raw/`
- Transition to S3-IA after **30 days**
- Expire after **90 days**
- Save

**6c — Create IAM user with scoped permissions**

Go to IAM → **Users** → **Create user**:

- Username: `jmie-oracle-vm`
- Select **Programmatic access only**

Attach a custom inline policy (paste this JSON):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "JMIEBucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::jmie-datalake",
        "arn:aws:s3:::jmie-datalake/*"
      ]
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

- Create user → **Download the `.csv` file** with the access key. You only see this once.

**6d — Verify S3 access locally**

```bash
# Configure the AWS CLI with your new key
aws configure --profile jmie
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

# Test write access
echo "sprint1-test" | aws s3 cp - s3://jmie-datalake/test.txt --profile jmie

# Test read access
aws s3 cp s3://jmie-datalake/test.txt - --profile jmie

# Clean up test file
aws s3 rm s3://jmie-datalake/test.txt --profile jmie
```

> **Checkpoint:** All three commands succeed without errors.

---

## Phase 4 · GCP Artifact Registry

### Step 7 — Create the image registry

**7a — Create or select a GCP project**

```bash
# Log in to GCP
gcloud auth login

# Create a new project (or use existing)
gcloud projects create jmie-project-YOUR_ID --name="JMIE"
gcloud config set project jmie-project-YOUR_ID

# Enable billing on the project (required even for free tier)
# Go to: console.cloud.google.com → Billing → Link account
```

**7b — Enable the Artifact Registry API**

```bash
gcloud services enable artifactregistry.googleapis.com
```

**7c — Create the Docker repository**

```bash
# Choose a region close to you
# Brazil: southamerica-east1  |  US: us-central1  |  EU: europe-west1
export GCP_REGION=southamerica-east1

gcloud artifacts repositories create jmie \
  --repository-format=docker \
  --location=$GCP_REGION \
  --description="JMIE Docker images"

# Verify
gcloud artifacts repositories list
```

**7d — Authenticate Docker to push images**

```bash
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev
```

**7e — Create a Service Account for CI/CD**

```bash
# Create the service account
gcloud iam service-accounts create jmie-cicd \
  --display-name="JMIE CI/CD"

# Grant it writer access to the Artifact Registry
gcloud artifacts repositories add-iam-policy-binding jmie \
  --location=$GCP_REGION \
  --member="serviceAccount:jmie-cicd@jmie-project-YOUR_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Generate a JSON key file
gcloud iam service-accounts keys create gcp-sa-key.json \
  --iam-account=jmie-cicd@jmie-project-YOUR_ID.iam.gserviceaccount.com

# Print the key content — you'll paste this into GitHub Secrets in Step 14
cat gcp-sa-key.json

# Delete the local key file after saving it to GitHub Secrets
# IMPORTANT: never commit this file
rm gcp-sa-key.json
```

**7f — Test pushing a placeholder image**

```bash
export IMAGE=$GCP_REGION-docker.pkg.dev/jmie-project-YOUR_ID/jmie/api

# Pull a tiny test image and push it to your registry
docker pull hello-world
docker tag hello-world $IMAGE:test
docker push $IMAGE:test

# Verify it shows up
gcloud artifacts docker images list $GCP_REGION-docker.pkg.dev/jmie-project-YOUR_ID/jmie
```

> **Checkpoint:** The `api:test` image appears in the Artifact Registry.

---

## Phase 5 · Oracle Cloud VM

### Step 8 — Create the Always Free VM

1. Create an account at [cloud.oracle.com](https://cloud.oracle.com) if you haven't already
2. During signup, choose your **home region** — this cannot be changed later:
   - Brazil: `Brazil East (São Paulo)` → `sa-saopaulo-1`
   - Alternatively any other region close to you
3. Once inside the console → **Compute** → **Instances** → **Create instance**

**Instance configuration:**
- Name: `jmie-vm`
- Image: **Canonical Ubuntu 22.04** (click Edit → change from Oracle Linux)
- Shape: click **Change shape** → **Ampere** → `VM.Standard.A1.Flex`
  - OCPUs: **4**
  - Memory: **24 GB**
  - ⚠️ Make sure both sliders are at maximum — this is the Always Free limit
- Networking: keep defaults, ensure **Assign a public IPv4 address** is checked
- SSH keys: select **Paste public key** → paste the content of `~/.ssh/jmie_oracle.pub` from Step 3

Click **Create**. The VM will be in `PROVISIONING` state for 1–2 minutes.

**Save the public IP address** shown on the instance details page — you'll use it throughout.

```bash
# Test SSH connection (replace with your actual IP)
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# If it times out, the firewall isn't open yet — continue to Step 9
```

---

### Step 9 — Configure Oracle firewall (both layers)

**Layer 1 — VCN Security List** (Oracle console):

1. From your VM details page → click the **Subnet** link → **Security List** → **Default Security List**
2. Click **Add Ingress Rules** and add each of the following (click Add Rule for each):

| Source CIDR | Protocol | Destination Port | Description |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `22` | SSH (you'll restrict this after setup) |
| `0.0.0.0/0` | TCP | `3000` | React frontend |
| `0.0.0.0/0` | TCP | `8000` | FastAPI |
| `YOUR_HOME_IP/32` | TCP | `8080` | Airflow UI |
| `YOUR_HOME_IP/32` | TCP | `5000` | MLflow UI |
| `YOUR_HOME_IP/32` | TCP | `6006` | Phoenix UI |

> Find your home IP: `curl ifconfig.me`

**Layer 2 — OS iptables** (run inside the VM via SSH):

```bash
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# Open required ports in the OS firewall
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 22 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 6006 -j ACCEPT

# Save rules so they persist across reboots
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

# Verify rules were saved
sudo iptables -L INPUT --line-numbers
```

> **Checkpoint:** `ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP` connects successfully.

---

### Step 10 — Bootstrap the Oracle VM

Still inside the SSH session:

```bash
# ── Update the system ─────────────────────────────────────────────────
sudo apt-get update && sudo apt-get upgrade -y

# ── Install Docker ────────────────────────────────────────────────────
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo apt-get install -y docker-compose-plugin

# ── Install uv ───────────────────────────────────────────────────────
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# ── Install AWS CLI ───────────────────────────────────────────────────
sudo apt-get install -y awscli

# ── Install GCP CLI ───────────────────────────────────────────────────
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
  https://packages.cloud.google.com/apt cloud-sdk main" | \
  sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
  sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install -y google-cloud-cli

# ── Log out and back in (applies docker group membership) ─────────────
exit
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# ── Verify ────────────────────────────────────────────────────────────
docker --version
docker compose version
uv --version
aws --version
gcloud --version

# ── Configure AWS on the VM ───────────────────────────────────────────
aws configure
# Enter: your jmie IAM user keys, us-east-1, json

# ── Configure GCP on the VM ───────────────────────────────────────────
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev
# When prompted for a project: enter your GCP project ID

# ── Configure auto-start on reboot ───────────────────────────────────
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && cd /home/ubuntu/jmie && docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d") | crontab -
```

> **Checkpoint:** All version commands return output. `aws s3 ls s3://jmie-datalake` returns successfully from the VM.

---

## Phase 6 · Docker Compose Scaffold

### Step 11 — Create the three Compose files

Back on **your local machine**, inside the `jmie/` directory:

```bash
cat > docker-compose.yml << 'EOF'
version: "3.9"

networks:
  jmie-net:
    driver: bridge

volumes:
  postgres-app-data:
  postgres-airflow-data:
  qdrant-data:
  mlflow-data:
  phoenix-data:
  airflow-logs:

services:

  postgres-app:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_APP_USER}
      POSTGRES_PASSWORD: ${POSTGRES_APP_PASSWORD}
      POSTGRES_DB: ${POSTGRES_APP_DB}
    volumes:
      - postgres-app-data:/var/lib/postgresql/data
    networks: [jmie-net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_APP_USER}"]
      interval: 10s
      retries: 5

  postgres-airflow:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_AIRFLOW_USER}
      POSTGRES_PASSWORD: ${POSTGRES_AIRFLOW_PASSWORD}
      POSTGRES_DB: ${POSTGRES_AIRFLOW_DB}
    ports:
      - "${POSTGRES_AIRFLOW_PORT}:5432"
    volumes:
      - postgres-airflow-data:/var/lib/postgresql/data
    networks: [jmie-net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_AIRFLOW_USER}"]
      interval: 10s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage
    networks: [jmie-net]

  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    command: >
      mlflow server
      --backend-store-uri sqlite:///mlflow/mlflow.db
      --default-artifact-root ${MLFLOW_ARTIFACT_ROOT}
      --host 0.0.0.0
      --port 5000
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION}
    volumes:
      - mlflow-data:/mlflow
    ports:
      - "${MLFLOW_TRACKING_PORT:-5000}:5000"
    networks: [jmie-net]

  phoenix:
    image: arizephoenix/phoenix:latest
    environment:
      PHOENIX_PORT: ${PHOENIX_PORT}
    volumes:
      - phoenix-data:/root/.phoenix
    ports:
      - "${PHOENIX_PORT}:${PHOENIX_PORT}"
    networks: [jmie-net]

  airflow-scheduler:
    image: apache/airflow:2.9.1
    command: bash -c "airflow db migrate && airflow users create --username ${AIRFLOW_ADMIN_USER} --password ${AIRFLOW_ADMIN_PASSWORD} --firstname Admin --lastname User --role Admin --email admin@jmie.local; airflow scheduler"
    environment: &airflow-env
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_AIRFLOW_USER}:${POSTGRES_AIRFLOW_PASSWORD}@postgres-airflow:5432/${POSTGRES_AIRFLOW_DB}
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW__CORE__FERNET_KEY}
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW__WEBSERVER__SECRET_KEY}
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION}
      JMIE_USE_MOCK_SCRAPER: ${JMIE_USE_MOCK_SCRAPER}
      JMIE_S3_WRITE: ${JMIE_S3_WRITE}
    volumes:
      - ./dags:/opt/airflow/dags
      - airflow-logs:/opt/airflow/logs
    depends_on:
      postgres-airflow:
        condition: service_healthy
    networks: [jmie-net]

  airflow-webserver:
    image: apache/airflow:2.9.1
    command: airflow webserver
    environment: *airflow-env
    ports:
      - "8080:8080"
    volumes:
      - ./dags:/opt/airflow/dags
      - airflow-logs:/opt/airflow/logs
    depends_on:
      postgres-airflow:
        condition: service_healthy
    networks: [jmie-net]

  fastapi-app:
    environment:
      ENV: ${ENV}
      DATABASE_URL: postgresql://${POSTGRES_APP_USER}:${POSTGRES_APP_PASSWORD}@postgres-app:5432/${POSTGRES_APP_DB}
      QDRANT_HOST: ${QDRANT_HOST}
      QDRANT_PORT: ${QDRANT_PORT}
      MLFLOW_TRACKING_URI: ${MLFLOW_TRACKING_URI}
      PHOENIX_ENDPOINT: http://phoenix:${PHOENIX_PORT}
      API_SECRET_KEY: ${API_SECRET_KEY}
      API_HOST: ${API_HOST}
      API_PORT: ${API_PORT}
    ports:
      - "${API_PORT}:${API_PORT}"
    depends_on:
      postgres-app:
        condition: service_healthy
    networks: [jmie-net]

  frontend:
    ports:
      - "3000:3000"
    networks: [jmie-net]
    depends_on:
      - fastapi-app
EOF
```

```bash
cat > docker-compose.dev.yml << 'EOF'
version: "3.9"

services:

  fastapi-app:
    build:
      context: ./api
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./api:/app           # hot-reload: live code mount
    command: uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./frontend/src:/app/src
    command: npm run dev -- --host
    ports:
      - "5173:5173"          # Vite dev server

  postgres-app:
    ports:
      - "${POSTGRES_APP_PORT}:5432"  # expose locally for DB tools
EOF
```

```bash
cat > docker-compose.prod.yml << 'EOF'
version: "3.9"

services:

  fastapi-app:
    image: ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_ARTIFACT_REPO}/api:latest
    restart: always

  frontend:
    image: ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_ARTIFACT_REPO}/frontend:latest
    restart: always

  postgres-app:
    restart: always

  postgres-airflow:
    restart: always

  qdrant:
    restart: always

  mlflow:
    restart: always

  phoenix:
    restart: always

  airflow-scheduler:
    restart: always

  airflow-webserver:
    restart: always
EOF
```

---

### Step 12 — Create placeholder Dockerfiles

These are minimal stubs — the real implementations come in Sprint 4 (FastAPI) and Sprint 6 (frontend). They exist now so `docker compose build` succeeds.

```bash
# Create directory structure
mkdir -p api frontend dags

# FastAPI placeholder Dockerfile
mkdir -p api
cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim AS base

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Development stage
FROM base AS development
RUN uv sync --frozen
COPY . .
CMD ["uv", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# Production stage
FROM base AS production
RUN uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# FastAPI placeholder app
cat > api/main.py << 'EOF'
from fastapi import FastAPI

app = FastAPI(title="JMIE API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": "jmie-api"}
EOF

# FastAPI pyproject.toml
cat > api/pyproject.toml << 'EOF'
[project]
name = "jmie-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "structlog>=24.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Frontend placeholder Dockerfile
cat > frontend/Dockerfile << 'EOF'
FROM node:20-alpine AS development
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
EOF

# Frontend placeholder package.json
cat > frontend/package.json << 'EOF'
{
  "name": "jmie-frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "react-router-dom": "^6.0.0",
    "axios": "^1.0.0",
    "recharts": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.0.0"
  }
}
EOF

# Nginx config for frontend
cat > frontend/nginx.conf << 'EOF'
server {
    listen 3000;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://fastapi-app:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Empty dags placeholder
touch dags/.gitkeep
```

---

### Step 13 — Verify the stack starts locally

```bash
# Copy env template for local use
cp .env.dev .env

# Start only the infrastructure services first (no builds needed)
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --env-file .env.dev \
  up postgres-app postgres-airflow qdrant mlflow phoenix -d

# Check all are running
docker compose ps

# Test PostgreSQL app
docker compose exec postgres-app pg_isready -U jmie_user

# Test Qdrant
curl http://localhost:6333/healthz

# Test MLflow (wait ~15s for startup)
curl http://localhost:5000/health

# Now start the API (requires a build)
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --env-file .env.dev build fastapi-app

docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --env-file .env.dev up fastapi-app -d

# Test the API
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"jmie-api"}

# Tear down when done testing
docker compose down
```

> **Checkpoint:** `curl http://localhost:8000/health` returns `{"status":"ok","service":"jmie-api"}`.

---

## Phase 7 · GitHub Actions CI/CD

### Step 14 — Add GitHub Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Add each of the following:

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your jmie IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Your jmie IAM user secret key |
| `GCP_SA_KEY` | The entire JSON content of your GCP service account key |
| `GCP_PROJECT_ID` | Your GCP project ID (e.g. `jmie-project-abc123`) |
| `GCP_REGION` | Your chosen region (e.g. `southamerica-east1`) |
| `ORACLE_VM_IP` | Your Oracle VM public IP address |
| `ORACLE_SSH_KEY` | The **private** key content from `~/.ssh/jmie_oracle` |

---

### Step 15 — Create the three workflow files

```bash
mkdir -p .github/workflows
```

**`ci.yml` — runs on every push to any branch:**

```bash
cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh && echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Set up Python
        run: uv python install 3.11

      - name: Install API dependencies
        working-directory: api
        run: uv sync --frozen

      - name: Lint with ruff
        working-directory: api
        run: uv run ruff check .

      - name: Run unit tests
        working-directory: api
        run: uv run pytest tests/unit/ -v --tb=short
        continue-on-error: true   # no unit tests yet in Sprint 1 — remove in Sprint 2
EOF
```

**`cd.yml` — runs only on merge to `main`:**

```bash
cat > .github/workflows/cd.yml << 'EOF'
name: CD

on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ secrets.GCP_REGION }}-docker.pkg.dev

      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: ./api
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/jmie/api:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Oracle VM
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.ORACLE_VM_IP }}
          username: ubuntu
          key: ${{ secrets.ORACLE_SSH_KEY }}
          script: |
            cd /home/ubuntu/jmie
            git pull origin main
            docker compose -f docker-compose.yml -f docker-compose.prod.yml \
              --env-file .env.prod \
              pull fastapi-app
            docker compose -f docker-compose.yml -f docker-compose.prod.yml \
              --env-file .env.prod \
              up -d --no-deps fastapi-app
EOF
```

**`docs.yml` — runs on merge to `main` (placeholder for Sprint 5):**

```bash
cat > .github/workflows/docs.yml << 'EOF'
name: Docs

on:
  push:
    branches: [main]

jobs:
  deploy-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Placeholder — MkDocs added in Sprint 5
        run: echo "Docs pipeline placeholder — implement in Sprint 5"
EOF
```

---

### Step 16 — Clone the repo on the Oracle VM and do the first production deploy

```bash
# SSH into the Oracle VM
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# Authenticate Docker to GCP Artifact Registry
gcloud auth configure-docker YOUR_GCP_REGION-docker.pkg.dev

# Clone your repository
git clone https://github.com/YOUR_USERNAME/jmie.git
cd jmie

# Create the production env file (fill in real values)
cp .env.prod.example .env.prod
nano .env.prod
# Set:
#   ENV=production
#   JMIE_USE_MOCK_SCRAPER=false
#   JMIE_S3_WRITE=true
#   All AWS, GCP, and DB credentials

# Start the full production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.prod up -d

# Verify all services are running
docker compose ps
```

Now push a change from your local machine to trigger the CI/CD pipeline:

```bash
# On your local machine
git checkout dev

# Add all Sprint 1 files
git add .
git commit -m "feat(sprint1): scaffold docker-compose, Dockerfiles, placeholder API and frontend"
git push origin dev

# Open a PR from dev → main on GitHub
# Merge it
# Watch the Actions tab — cd.yml should trigger and deploy to Oracle VM
```

> **Checkpoint:** The GitHub Actions **CD** run completes successfully. `curl http://YOUR_ORACLE_IP:8000/health` returns `{"status":"ok","service":"jmie-api"}`.

---

## Phase 8 · Verification

### Step 17 — Sprint 1 acceptance checklist

Run through every acceptance criterion from the PRD:

```bash
# ── Oracle VM ─────────────────────────────────────────────────────────
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# All 9 services running?
docker compose ps
# Expected: 9 rows, all State = Up

# ── S3 access from the VM ─────────────────────────────────────────────
aws s3 ls s3://jmie-datalake
# Expected: empty listing (no error)

echo "vm-to-s3-test" | aws s3 cp - s3://jmie-datalake/sprint1-verify.txt
aws s3 rm s3://jmie-datalake/sprint1-verify.txt
# Expected: both commands succeed

# ── GCP Artifact Registry ─────────────────────────────────────────────
gcloud artifacts docker images list \
  YOUR_GCP_REGION-docker.pkg.dev/YOUR_GCP_PROJECT/jmie
# Expected: api:latest image listed

# ── API health ────────────────────────────────────────────────────────
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"jmie-api"}

# ── From your local machine ───────────────────────────────────────────
curl http://YOUR_ORACLE_IP:8000/health
# Expected: {"status":"ok","service":"jmie-api"}
```

**GitHub checks:**

- [ ] Push to `dev` triggers `ci.yml` (lint job passes)
- [ ] Merge to `main` triggers `cd.yml` (build + deploy passes)
- [ ] Oracle VM shows the latest API image after the deploy

**All 9 services check:**

```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

Expected output:
```
NAME                       STATUS
jmie-airflow-scheduler-1   Up
jmie-airflow-webserver-1   Up
jmie-fastapi-app-1         Up
jmie-frontend-1            Up
jmie-mlflow-1              Up
jmie-phoenix-1             Up
jmie-postgres-airflow-1    Up
jmie-postgres-app-1        Up
jmie-qdrant-1              Up
```

---

## Sprint 1 Complete ✓

If all checks pass, Sprint 1 is done. The foundation is in place:

- **Oracle Cloud VM** running 24/7 with 9 containerised services
- **AWS S3** bucket with lifecycle rules, IAM scoped to the bucket
- **GCP Artifact Registry** holding the first multi-platform Docker image
- **GitHub** repo with `dev`/`main` branch protection and all three CI/CD pipelines wired
- **Dev/prod environment split** verified: local dev stack runs, prod stack deploys via CI/CD

**Next up — Sprint 2:** Python scrapers for 2 EN + 2 PT job boards, the Airflow daily DAG, PostgreSQL schema with Alembic, and the S3-to-Postgres loader.

---

*JMIE Sprint 1 Plan · Infrastructure Foundations · Generated from PRD v1.6*