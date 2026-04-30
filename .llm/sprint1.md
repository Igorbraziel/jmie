# JMIE — Sprint 1 Implementation Plan
## Infrastructure Foundations · Weeks 1–2

> **Goal:** All 9 containers running on Oracle Cloud · OCI Object Storage accessible from the VM · First multi-platform Docker image in GCP Artifact Registry · GitHub repo with branch structure and CI/CD pipelines wired up · `api/ai/` Agent Framework scaffold committed.
>
> **PRD version:** v2.1 · **Estimated time:** 16–21 hours total across 2 weeks
> **Prerequisites:** A computer with Docker Desktop, Git, Python 3.11+, and Node.js 20+ installed locally.

---

## What changed from the original Sprint 1

If you already completed Sprint 1 against PRD v1.6/v2.0, here is exactly what is different — skip to the ★ markers to do only the delta work.

| Phase | Old (v1.6) | New (v2.1) | Action needed |
|---|---|---|---|
| Phase 1 — Local tools | Install AWS CLI | Install OCI CLI instead | ★ Replace |
| Phase 2 — Env files | AWS S3 vars in `.env.example` | OCI vars; AWS only for CloudWatch | ★ Update files |
| **Phase 3 — Storage** | **AWS S3 bucket + IAM user** | **OCI Object Storage bucket + IAM policy** | ★ Redo entirely |
| Phase 4 — GCP | No change | No change | ✓ Done |
| Phase 5 — Oracle VM | Install AWS CLI, `aws configure` | Install OCI CLI, configure Instance Principal | ★ Update |
| Phase 6 — Docker Compose | MLflow uses AWS S3 artifact root | MLflow uses local volume (dev) / OCI S3-compat (prod) | ★ Update files |
| **Phase 7 — Agent scaffold** | **Did not exist** | **New: `api/ai/` module committed** | ★ New phase |
| Phase 8 — CI/CD Secrets | AWS S3 keys in GitHub Secrets | Remove S3 keys; add OCI secrets | ★ Update |
| Phase 9 — Verification | `aws s3 ls s3://jmie-datalake` | `oci os object list --bucket-name jmie-datalake` | ★ Update |

---

## Overview

```
Phase 1 · Local machine setup          (~2h)   Steps 1–3
Phase 2 · GitHub repository            (~1h)   Steps 4–5
Phase 3 · OCI Object Storage + IAM     (~1.5h) Step 6      ← replaces AWS S3
Phase 4 · GCP Artifact Registry        (~1h)   Step 7
Phase 5 · Oracle Cloud VM              (~3h)   Steps 8–10
Phase 6 · Docker Compose scaffold      (~4h)   Steps 11–13
Phase 7 · Agent Framework scaffold     (~1h)   Step 14     ← new in v2.1
Phase 8 · GitHub Actions CI/CD         (~3h)   Steps 15–17
Phase 9 · Verification                 (~1h)   Step 18
```

---

## Phase 1 · Local Machine Setup

### Step 1 — Install required tools ★ (OCI CLI replaces AWS CLI for storage)

```bash
# Verify Docker Desktop is running
docker --version        # should be 24+
docker compose version  # should be 2.x

# Verify Git
git --version

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv --version              # should be 0.4+

# Install Node.js 20+
# macOS:  brew install node
# Ubuntu: sudo apt install nodejs npm
node --version  # should be 20+

# Install the GCP CLI
# macOS:  brew install --cask google-cloud-sdk
# Ubuntu: https://cloud.google.com/sdk/docs/install
gcloud --version

# ★ Install the OCI CLI (replaces the AWS CLI for object storage)
# macOS:
brew install oci-cli
# Ubuntu / WSL:
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
# Follow the prompts; accept defaults for install location.
# Restart your shell afterwards.
oci --version   # should return a version number

# Keep the AWS CLI installed — it is still needed for CloudWatch in Sprint 5.
# macOS:  brew install awscli
# Ubuntu: sudo apt install awscli
aws --version
```

> **Checkpoint:** All six commands (`docker`, `uv`, `node`, `gcloud`, `oci`, `aws`) return version numbers without errors.

---

### Step 2 — Install Docker buildx (multi-platform builder)

The Oracle VM is ARM64. Your laptop is likely x86. You need `buildx` to build images that run on both.

```bash
docker buildx create --name jmie-builder --use
docker buildx inspect --bootstrap
docker buildx ls
# You should see: linux/amd64, linux/arm64 listed under jmie-builder
```

> **Checkpoint:** `docker buildx ls` shows `linux/arm64` as a supported platform.

---

### Step 3 — Generate SSH key pair for Oracle VM

```bash
ssh-keygen -t ed25519 -C "jmie-oracle" -f ~/.ssh/jmie_oracle
# Creates: ~/.ssh/jmie_oracle (private) and ~/.ssh/jmie_oracle.pub (public)

cat ~/.ssh/jmie_oracle.pub
# Keep this output — you'll paste it into the Oracle console in Step 8.
```

> **Checkpoint:** `cat ~/.ssh/jmie_oracle.pub` shows a line starting with `ssh-ed25519`.

---

## Phase 2 · GitHub Repository

### Step 4 — Create the GitHub repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `jmie`
3. Visibility: **Private** (make public later once everything works)
4. **Do not** initialise with a README — you'll push the structure yourself
5. Click **Create repository**

---

### Step 5 — Initialise the repository locally ★ (env files updated for OCI)

```bash
mkdir jmie && cd jmie
git init
git branch -M main
git checkout -b dev
git remote add origin https://github.com/YOUR_USERNAME/jmie.git
```

Create the root-level files. The `.env.example` now reflects OCI Object Storage instead of AWS S3:

```bash
cat > .gitignore << 'EOF'
# Environment files — never commit real credentials
.env.prod
.env
*.env.local

# OCI credentials — never commit
.oci/

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

# Local mock OCI bucket
tmp/
EOF
```

```bash
# ★ .env.example — OCI vars replace S3 vars; AWS kept only for CloudWatch
cat > .env.example << 'EOF'
# ── Environment ───────────────────────────────────────────────────────
ENV=development

# ── OCI Object Storage ────────────────────────────────────────────────
# Used by oci_helpers.py for all data lake reads and writes.
# In production on the Oracle VM, Instance Principal is used instead —
# these vars are only needed for local development.
OCI_TENANCY_OCID=ocid1.tenancy.oc1..your_tenancy_ocid
OCI_USER_OCID=ocid1.user.oc1..your_user_ocid
OCI_FINGERPRINT=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
OCI_REGION=sa-saopaulo-1
OCI_PRIVATE_KEY_PATH=/home/youruser/.oci/oci_api_key.pem
OCI_BUCKET_NAME=jmie-datalake
OCI_NAMESPACE=your_tenancy_namespace
# Set to "true" in dev to skip real OCI calls and read/write from ./tmp/mock-oci-bucket/
OCI_USE_MOCK=true

# ── OCI S3-Compatible (MLflow artifact store — prod only) ─────────────
# MLflow uses boto3 with OCI's S3-compatible endpoint.
# Generate Customer Secret Keys in: OCI Console → Identity → Users → Your User → Customer Secret Keys
# Leave blank in dev (MLflow uses a local volume instead).
OCI_S3_COMPAT_ACCESS_KEY=
OCI_S3_COMPAT_SECRET_KEY=
# Example: https://abc123.compat.objectstorage.sa-saopaulo-1.oraclecloud.com
OCI_S3_COMPAT_ENDPOINT=

# ── AWS (CloudWatch monitoring only — Sprint 5) ───────────────────────
# These credentials are ONLY for CloudWatch PutMetricData.
# AWS S3 is no longer used in this project.
AWS_ACCESS_KEY_ID=your_cloudwatch_iam_key
AWS_SECRET_ACCESS_KEY=your_cloudwatch_iam_secret
AWS_DEFAULT_REGION=us-east-1

# ── GCP ───────────────────────────────────────────────────────────────
GCP_PROJECT_ID=your_gcp_project_id
GCP_REGION=southamerica-east1
GCP_ARTIFACT_REPO=jmie

# ── PostgreSQL (app) ──────────────────────────────────────────────────
POSTGRES_APP_USER=jmie
POSTGRES_APP_PASSWORD=changeme
POSTGRES_APP_DB=jmie
POSTGRES_APP_PORT=5432

# ── PostgreSQL (Airflow) ──────────────────────────────────────────────
POSTGRES_AIRFLOW_USER=airflow
POSTGRES_AIRFLOW_PASSWORD=changeme
POSTGRES_AIRFLOW_DB=airflow
POSTGRES_AIRFLOW_PORT=5433

# ── Airflow ───────────────────────────────────────────────────────────
AIRFLOW__CORE__FERNET_KEY=generate_with_python_-c_"from_cryptography.fernet_import_Fernet;print(Fernet.generate_key().decode())"
AIRFLOW__WEBSERVER__SECRET_KEY=changeme
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=changeme

# ── Qdrant ────────────────────────────────────────────────────────────
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# ── MLflow ────────────────────────────────────────────────────────────
MLFLOW_TRACKING_URI=http://mlflow:5000
# Dev: uses local Docker volume path. Prod: uses OCI S3-compat endpoint.
MLFLOW_ARTIFACT_ROOT=/mlflow/artifacts

# ── FastAPI ───────────────────────────────────────────────────────────
API_SECRET_KEY=changeme
API_HOST=0.0.0.0
API_PORT=8000

# ── Phoenix ───────────────────────────────────────────────────────────
PHOENIX_PORT=6006

# ── NLP ───────────────────────────────────────────────────────────────
MODEL_VERSION=latest
JMIE_USE_MOCK_SCRAPER=true

# ── Agent Framework ───────────────────────────────────────────────────
# "local" = Ollama/llama.cpp on localhost (dev). "gemini" = production.
LLM_PROVIDER=local
OLLAMA_BASE_URL=http://host.docker.internal:11434
EOF

cp .env.example .env.dev
# .env.dev defaults are already correct for local development:
# OCI_USE_MOCK=true, JMIE_USE_MOCK_SCRAPER=true, LLM_PROVIDER=local

cp .env.example .env.prod.example
sed -i '1s/^/# PRODUCTION — fill in real values, store on Oracle VM only, never commit\n/' .env.prod.example
```

Push the first commit:

```bash
git add .gitignore .env.example .env.dev .env.prod.example
git commit -m "chore: initialise repo with OCI-based env templates and gitignore"
git push -u origin dev
```

Protect `main` on GitHub:
1. Settings → Branches → Add branch protection rule
2. Branch name pattern: `main`
3. Check **Require a pull request before merging** and **Require status checks to pass**
4. Save

> **Checkpoint:** `dev` branch exists on GitHub. Direct pushes to `main` are blocked.

---

## Phase 3 · OCI Object Storage + IAM ★ (replaces AWS S3)

### Step 6 — Create the OCI bucket and set up access

This phase replaces the old AWS S3 step entirely. Everything that previously went to S3 now goes here.

---

**6a — Create the Object Storage bucket**

1. Log into [cloud.oracle.com](https://cloud.oracle.com) → navigate to **Storage → Object Storage & Archive Storage → Buckets**
2. Select your compartment (use root compartment for simplicity)
3. Click **Create Bucket**:
   - Bucket Name: `jmie-datalake`
   - Default Storage Tier: **Standard**
   - Versioning: **Enabled** ← important for the `mlflow-artifacts/` prefix
   - Encryption: leave default (Oracle-managed keys)
4. Click **Create**

> Note your **namespace** — visible on the Bucket Details page under "Namespace". You'll need it for the S3-compatible endpoint URL in prod. It looks like a short string, e.g. `abc1def2ghij`.

---

**6b — Set lifecycle rules**

Inside the `jmie-datalake` bucket → **Lifecycle Policy Rules** → **Create Rule**:

**Rule 1 — Transition raw data to Infrequent Access:**
- Rule Name: `raw-to-infrequent-access`
- Object Name Filter: prefix `raw/`
- Action: **Move to Infrequent Access** after **30 days**

**Rule 2 — Delete old raw data:**
- Rule Name: `raw-delete-90d`
- Object Name Filter: prefix `raw/`
- Action: **Delete** after **90 days**

---

**6c — Create OCI API key for local development**

This key lets your local machine write to the bucket in development. In production, the Oracle VM uses Instance Principal instead (no key files on disk).

1. OCI Console → top-right avatar → **My Profile**
2. Scroll down → **API Keys** → **Add API Key**
3. Select **Generate API Key Pair**
4. **Download Private Key** → save to `~/.oci/oci_api_key.pem`
5. Click **Add** — Oracle shows you a config file snippet. Copy it.

Create the OCI config file on your local machine:

```bash
mkdir -p ~/.oci
chmod 700 ~/.oci

# Paste the config snippet Oracle showed you:
cat > ~/.oci/config << 'EOF'
[DEFAULT]
user=ocid1.user.oc1..YOUR_USER_OCID
fingerprint=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
tenancy=ocid1.tenancy.oc1..YOUR_TENANCY_OCID
region=sa-saopaulo-1
key_file=/home/YOUR_USERNAME/.oci/oci_api_key.pem
EOF

chmod 600 ~/.oci/config
chmod 600 ~/.oci/oci_api_key.pem
```

---

**6d — Verify bucket access locally**

```bash
# List buckets (confirms auth is working)
oci os bucket list --compartment-id ocid1.tenancy.oc1..YOUR_TENANCY_OCID

# Write a test object
echo "sprint1-oci-test" | oci os object put \
  --bucket-name jmie-datalake \
  --name sprint1-verify.txt \
  --file -

# Read it back
oci os object get \
  --bucket-name jmie-datalake \
  --name sprint1-verify.txt \
  --file -

# Delete the test object
oci os object delete \
  --bucket-name jmie-datalake \
  --name sprint1-verify.txt \
  --force
```

> **Checkpoint:** All three commands succeed without errors. The test object appears and disappears cleanly.

---

**6e — Set up Instance Principal for the Oracle VM** *(do this before Step 10)*

Instance Principal lets the Oracle VM authenticate to OCI Object Storage automatically — no API key files, no credential rotation. You'll reference this in Step 10 when bootstrapping the VM.

**Create a Dynamic Group** (groups VMs by OCID, so IAM policies can target them):

1. OCI Console → **Identity & Security → Dynamic Groups → Create Dynamic Group**
   - Name: `jmie-vm-group`
   - Description: `JMIE Oracle VM for Instance Principal auth`
   - Matching Rule: `ANY {instance.compartment.id = 'ocid1.tenancy.oc1..YOUR_TENANCY_OCID'}`
   *(or use the specific compartment OCID if you're not using root)*
2. Click **Create**

**Create an IAM Policy** granting the group access to the bucket:

1. OCI Console → **Identity & Security → Policies → Create Policy**
   - Name: `jmie-vm-object-storage-policy`
   - Description: `Allows JMIE VM to read and write OCI Object Storage`
   - Compartment: root (or your compartment)
   - Policy Statements (add each one):
     ```
     Allow dynamic-group jmie-vm-group to manage objects in tenancy where target.bucket.name='jmie-datalake'
     Allow dynamic-group jmie-vm-group to read buckets in tenancy
     ```
2. Click **Create**

The VM doesn't need any configuration to use Instance Principal — the OCI SDK detects it automatically when `oci.auth.signers.InstancePrincipalsSecurityTokenSigner()` is called. You'll verify this in Step 10 after provisioning the VM.

---

**6f — Get your OCI namespace** *(needed for `.env` files and MLflow prod config)*

```bash
oci os ns get
# Returns: {"data": "your_namespace_string"}
# Save this value — it goes into OCI_NAMESPACE in your .env files
```

---

**6g — Update your local `.env.dev` with real OCI values**

```bash
# Edit .env.dev and fill in the values from steps above
nano .env.dev

# Fill in:
#   OCI_TENANCY_OCID=ocid1.tenancy.oc1..YOUR_TENANCY_OCID
#   OCI_USER_OCID=ocid1.user.oc1..YOUR_USER_OCID
#   OCI_FINGERPRINT=aa:bb:cc:... (from the API key page)
#   OCI_REGION=sa-saopaulo-1
#   OCI_PRIVATE_KEY_PATH=/home/YOUR_USERNAME/.oci/oci_api_key.pem
#   OCI_BUCKET_NAME=jmie-datalake
#   OCI_NAMESPACE=your_namespace_string
#   OCI_USE_MOCK=true   ← keep true for now; DAG code doesn't exist yet
```

> **Checkpoint:** `oci os object list --bucket-name jmie-datalake` succeeds from your local machine. The bucket is empty (or contains only the cleanup test from 6d).

---

## Phase 4 · GCP Artifact Registry

### Step 7 — Create the image registry

*(Unchanged from original Sprint 1 — reproduced here for completeness)*

**7a — Create or select a GCP project**

```bash
gcloud auth login
gcloud projects create jmie-project-YOUR_ID --name="JMIE"
gcloud config set project jmie-project-YOUR_ID
# Enable billing: console.cloud.google.com → Billing → Link account
```

**7b — Enable the Artifact Registry API**

```bash
gcloud services enable artifactregistry.googleapis.com
```

**7c — Create the Docker repository**

```bash
export GCP_REGION=southamerica-east1

gcloud artifacts repositories create jmie \
  --repository-format=docker \
  --location=$GCP_REGION \
  --description="JMIE Docker images"

gcloud artifacts repositories list
```

**7d — Authenticate Docker**

```bash
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev
```

**7e — Create a CI/CD Service Account**

```bash
gcloud iam service-accounts create jmie-cicd --display-name="JMIE CI/CD"

gcloud artifacts repositories add-iam-policy-binding jmie \
  --location=$GCP_REGION \
  --member="serviceAccount:jmie-cicd@jmie-project-YOUR_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud iam service-accounts keys create gcp-sa-key.json \
  --iam-account=jmie-cicd@jmie-project-YOUR_ID.iam.gserviceaccount.com

cat gcp-sa-key.json   # copy this for GitHub Secrets in Step 15
rm gcp-sa-key.json    # NEVER commit this file
```

**7f — Test pushing a placeholder image**

```bash
export IMAGE=$GCP_REGION-docker.pkg.dev/jmie-project-YOUR_ID/jmie/api
docker pull hello-world
docker tag hello-world $IMAGE:test
docker push $IMAGE:test
gcloud artifacts docker images list $GCP_REGION-docker.pkg.dev/jmie-project-YOUR_ID/jmie
```

> **Checkpoint:** `api:test` image appears in the Artifact Registry.

---

## Phase 5 · Oracle Cloud VM

### Step 8 — Create the Always Free VM

*(Unchanged from original Sprint 1)*

1. [cloud.oracle.com](https://cloud.oracle.com) → **Compute → Instances → Create instance**
2. Name: `jmie-vm`
3. Image: **Canonical Ubuntu 22.04**
4. Shape: **VM.Standard.A1.Flex** → OCPUs: **4** · Memory: **24 GB**
5. **Assign a public IPv4 address**: ✅
6. SSH keys: paste the content of `~/.ssh/jmie_oracle.pub`
7. Click **Create**

Save the public IP address. Also save the **instance OCID** (visible on the instance details page) — you'll need it to add this VM to the `jmie-vm-group` Dynamic Group.

**Add VM to the Dynamic Group:**

1. After the VM is `RUNNING`, copy its OCID (`ocid1.instance.oc1...`)
2. OCI Console → **Identity → Dynamic Groups → jmie-vm-group → Edit**
3. Update the matching rule to target this specific instance:
   ```
   ANY {instance.id = 'ocid1.instance.oc1..YOUR_INSTANCE_OCID'}
   ```
   (More specific than compartment-wide — better practice for a single VM)
4. Save

> **Checkpoint:** SSH connects: `ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP`

---

### Step 9 — Configure Oracle firewall (both layers)

*(Unchanged from original Sprint 1)*

**Layer 1 — VCN Security List** (Oracle console):

| Source CIDR | Protocol | Port | Description |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `22` | SSH |
| `0.0.0.0/0` | TCP | `3000` | React frontend |
| `0.0.0.0/0` | TCP | `8000` | FastAPI |
| `YOUR_HOME_IP/32` | TCP | `8080` | Airflow UI |
| `YOUR_HOME_IP/32` | TCP | `5000` | MLflow UI |
| `YOUR_HOME_IP/32` | TCP | `6006` | Phoenix UI |

Find your IP: `curl ifconfig.me`

**Layer 2 — OS iptables** (inside the VM via SSH):

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 22 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 3000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 6006 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
sudo iptables -L INPUT --line-numbers   # verify
```

> **Checkpoint:** SSH works without `Connection refused` or timeouts.

---

### Step 10 — Bootstrap the Oracle VM ★ (installs OCI CLI; no `aws configure` for storage)

Still inside the SSH session on the Oracle VM:

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

# ── Install OCI CLI ───────────────────────────────────────────────────
# The VM uses Instance Principal — no oci setup config needed.
# The CLI is installed for manual bucket inspection and debugging only.
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
# Accept all defaults when prompted.
source ~/.bashrc
oci --version   # confirm it installed

# ── Install GCP CLI ───────────────────────────────────────────────────
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
  https://packages.cloud.google.com/apt cloud-sdk main" | \
  sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
  sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install -y google-cloud-cli

# ── Install AWS CLI (CloudWatch only — Sprint 5 will configure it) ────
sudo apt-get install -y awscli

# ── Log out and back in ───────────────────────────────────────────────
exit
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# ── Verify all tools ─────────────────────────────────────────────────
docker --version
docker compose version
uv --version
oci --version
gcloud --version
aws --version

# ── Verify Instance Principal (OCI Object Storage access) ─────────────
# The VM authenticates automatically — no config files needed.
# Test by listing buckets using Instance Principal (the --auth flag forces it):
oci os bucket list \
  --compartment-id ocid1.tenancy.oc1..YOUR_TENANCY_OCID \
  --auth instance_principal
# Expected: JSON output listing your compartment's buckets (including jmie-datalake)

# Write a test object using Instance Principal
echo "vm-instance-principal-test" | oci os object put \
  --bucket-name jmie-datalake \
  --name sprint1-vm-verify.txt \
  --file - \
  --auth instance_principal

# Confirm it exists
oci os object list \
  --bucket-name jmie-datalake \
  --auth instance_principal

# Clean up
oci os object delete \
  --bucket-name jmie-datalake \
  --name sprint1-vm-verify.txt \
  --force \
  --auth instance_principal

# ── Authenticate GCP on the VM ────────────────────────────────────────
gcloud auth configure-docker YOUR_GCP_REGION-docker.pkg.dev

# ── Configure auto-start on reboot ───────────────────────────────────
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && cd /home/ubuntu/jmie && docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d") | crontab -
```

> **Checkpoint:** Instance Principal test succeeds — the VM writes to and reads from `jmie-datalake` with no credentials on disk.

---

## Phase 6 · Docker Compose Scaffold

### Step 11 — Create the three Compose files ★ (OCI vars; MLflow uses local volume in dev)

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
    # ★ Dev: artifact root is a local Docker volume path (/mlflow/artifacts).
    # ★ Prod: artifact root is OCI S3-compat (set via docker-compose.prod.yml override).
    # No AWS S3 credentials here — MLflow uses OCI's S3-compatible endpoint in prod.
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
      # ★ OCI credentials for oci_helpers.py — dev uses API key, prod uses Instance Principal.
      # In production, these vars are left unset; the OCI SDK detects Instance Principal automatically.
      OCI_TENANCY_OCID: ${OCI_TENANCY_OCID}
      OCI_USER_OCID: ${OCI_USER_OCID}
      OCI_FINGERPRINT: ${OCI_FINGERPRINT}
      OCI_REGION: ${OCI_REGION}
      OCI_PRIVATE_KEY_PATH: ${OCI_PRIVATE_KEY_PATH}
      OCI_BUCKET_NAME: ${OCI_BUCKET_NAME}
      OCI_NAMESPACE: ${OCI_NAMESPACE}
      OCI_USE_MOCK: ${OCI_USE_MOCK}
      JMIE_USE_MOCK_SCRAPER: ${JMIE_USE_MOCK_SCRAPER}
      # Agent framework
      LLM_PROVIDER: ${LLM_PROVIDER}
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
      LLM_PROVIDER: ${LLM_PROVIDER}
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

  db-migrations:
    image: jmie/db:latest
    environment:
      DATABASE_URL: postgresql://${POSTGRES_APP_USER}:${POSTGRES_APP_PASSWORD}@postgres-app:5432/${POSTGRES_APP_DB}
    depends_on:
      postgres-app:
        condition: service_healthy
    networks: [jmie-net]
    profiles:
      - migrations
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
      - "5173:5173"

  postgres-app:
    ports:
      - "${POSTGRES_APP_PORT}:5432"

  db-migrations:
    build:
      context: .
      dockerfile: db/Dockerfile
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

  # ★ MLflow prod override: uses OCI S3-compatible endpoint as artifact root.
  # MLflow's boto3 backend connects to OCI's S3-compatible endpoint using
  # Customer Secret Keys (NOT OCI API keys — these are separate credentials).
  # Generate at: OCI Console → Identity → Users → Your User → Customer Secret Keys
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    command: >
      mlflow server
      --backend-store-uri sqlite:///mlflow/mlflow.db
      --default-artifact-root s3://jmie-datalake/mlflow-artifacts
      --host 0.0.0.0
      --port 5000
    environment:
      MLFLOW_S3_ENDPOINT_URL: ${OCI_S3_COMPAT_ENDPOINT}
      AWS_ACCESS_KEY_ID: ${OCI_S3_COMPAT_ACCESS_KEY}
      AWS_SECRET_ACCESS_KEY: ${OCI_S3_COMPAT_SECRET_KEY}
    restart: always

  postgres-app:
    restart: always

  postgres-airflow:
    restart: always

  qdrant:
    restart: always

  phoenix:
    restart: always

  airflow-scheduler:
    # ★ Production: OCI credentials vars are intentionally left unset here.
    # The OCI SDK inside airflow-scheduler auto-detects Instance Principal
    # when running on the Oracle VM — no credentials needed in env.
    environment:
      OCI_TENANCY_OCID: ""
      OCI_USER_OCID: ""
      OCI_FINGERPRINT: ""
      OCI_PRIVATE_KEY_PATH: ""
      OCI_USE_MOCK: "false"
    restart: always

  airflow-webserver:
    restart: always

  db-migrations:
    image: ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${GCP_ARTIFACT_REPO}/db:latest
EOF
```

---

### Step 12 — Create placeholder Dockerfiles and app stubs

*(Mostly unchanged — updated `api/pyproject.toml` adds agent framework dependencies)*

```bash
mkdir -p api frontend dags db api/ai/agents

# DB placeholder
cat > db/Dockerfile << 'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY . .
CMD ["echo", "Migrations standalone container"]
EOF

cat > db/pyproject.toml << 'EOF'
[project]
name = "jmie-db"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["alembic>=1.13.0"]
EOF

# FastAPI Dockerfile (multi-stage)
cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim AS base
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./

FROM base AS development
RUN uv sync --frozen
COPY . .
CMD ["uv", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

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

# ★ FastAPI pyproject.toml — agent framework deps added
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
    # Agent Framework Layer (v2.1)
    "pydantic-ai>=0.0.13",
    "langgraph>=0.1.0",
    # OCI SDK (for oci_helpers.py — used by DAGs but also available to agents)
    "oci>=2.126.0",
    # Observability
    "opentelemetry-sdk>=1.24.0",
    "arize-phoenix>=4.0.0",
]

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Generate the lockfile
cd api && uv lock && cd ..

# Frontend placeholder
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

touch dags/.gitkeep
```

---

### Step 13 — Verify the stack starts locally

```bash
cp .env.dev .env

# Start infrastructure services first
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --env-file .env.dev \
  up postgres-app postgres-airflow qdrant mlflow phoenix -d

docker compose ps

# Test PostgreSQL
docker compose exec postgres-app pg_isready -U jmie

# Test Qdrant
curl http://localhost:6333/healthz

# Test MLflow (wait ~15s)
curl http://localhost:5000/health

# Build and start the API
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --env-file .env.dev build fastapi-app

docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  --env-file .env.dev up fastapi-app -d

curl http://localhost:8000/health
# Expected: {"status":"ok","service":"jmie-api"}

docker compose down
```

> **Checkpoint:** `curl http://localhost:8000/health` returns `{"status":"ok","service":"jmie-api"}`.

---

## Phase 7 · Agent Framework Scaffold ★ (new in v2.1)

### Step 14 — Create the `api/ai/` module stubs

This is a new Sprint 1 deliverable. The actual agent implementations come in Sprints 3–6, but the shared foundation must exist and be importable before Sprint 2 begins.

```bash
# Create the directory structure
mkdir -p api/ai/agents
touch api/ai/__init__.py
touch api/ai/agents/__init__.py
```

**`api/ai/base_agent.py`** — the abstract base every agent inherits from:

```bash
cat > api/ai/base_agent.py << 'EOF'
"""
BaseAgent — abstract base class for all JMIE AI agents.

Rules (from PRD §2.4):
  - All agents inherit from this class and implement run().
  - No agent may accept OCI bucket paths, DAG references, or DB connections as input.
  - No agent may write to OCI Object Storage or PostgreSQL directly.
  - All LLM calls go through call_llm() in provider.py — never hardcode model names.
"""
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    agent_name: str          # e.g. "ner_annotation"
    sprint: int              # sprint this agent belongs to
    framework: str           # "pydantic_ai" | "langgraph" | "raw_sdk"
    max_iterations: int | None = None  # None = single-shot

    @abstractmethod
    def run(self, input: dict) -> dict:
        """
        Execute the agent.
        Input and output must be JSON-serializable dicts.
        """
        ...

    def _emit_trace(self, span_name: str, attributes: dict) -> None:
        """
        Emit an OpenTelemetry span to Phoenix.
        Stub implementation — wired to Phoenix in Sprint 4.
        """
        # TODO Sprint 4: replace with real OTel span emission
        print(f"[TRACE STUB] {span_name}: {attributes}")
EOF
```

**`api/ai/config.py`** — LLM provider resolution from environment:

```bash
cat > api/ai/config.py << 'EOF'
"""
Agent framework configuration.
Resolves LLM_PROVIDER from environment and exposes provider settings.
No model name is ever hardcoded here — see provider.py for routing.
"""
import os

# Resolved once at import time. Overrideable per-call via call_llm(provider=...).
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")

PROVIDER_CONFIG: dict[str, dict] = {
    "local": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": "llama3",
    },
    "gemini": {
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-1.5-flash",
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
}


def get_provider_config(provider: str | None = None) -> dict:
    p = provider or LLM_PROVIDER
    if p not in PROVIDER_CONFIG:
        raise ValueError(
            f"Unknown LLM provider '{p}'. Valid: {list(PROVIDER_CONFIG)}"
        )
    return PROVIDER_CONFIG[p]
EOF
```

**`api/ai/provider.py`** — the single LLM call interface:

```bash
cat > api/ai/provider.py << 'EOF'
"""
Unified LLM call interface.
All four agents call this function — never the underlying SDK directly.

Sprint 1: stub implementation (returns a canned response).
Sprint 3: wire up PydanticAI + local Ollama.
Sprint 4: wire up LangGraph + Gemini production path.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

from api.ai.config import get_provider_config


def call_llm(
    prompt: str,
    provider: str | None = None,
    response_model: type["BaseModel"] | None = None,
    max_tokens: int = 1024,
) -> str | "BaseModel":
    """
    Route a prompt to the configured LLM provider.

    Args:
        prompt:         The full prompt string.
        provider:       Override LLM_PROVIDER env var for this call.
        response_model: If set, enforce structured JSON output via Pydantic validation.
        max_tokens:     Maximum tokens in the response.

    Returns:
        str if response_model is None, else a validated Pydantic model instance.

    Raises:
        ValidationError: If response_model is set and the LLM returns invalid output.
        RuntimeError:    If the provider call fails after retries.
    """
    config = get_provider_config(provider)
    # TODO Sprint 3: implement real provider routing
    # For now, return a stub so imports and tests don't fail
    stub = f"[STUB response from provider={config}] — implement in Sprint 3"
    if response_model is not None:
        raise NotImplementedError(
            "Structured output via response_model not yet implemented. "
            "Wire up PydanticAI in Sprint 3."
        )
    return stub
EOF
```

**`api/ai/agent_registry.py`** — the agent factory and registry:

```bash
cat > api/ai/agent_registry.py << 'EOF'
"""
Agent registry. Maps agent names to their classes.
All four agents must be registered here before they can be instantiated.
Using get_agent() is the only permitted way to create agent instances.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.ai.base_agent import BaseAgent

# Agents are imported lazily to avoid circular imports and to keep
# unused agent dependencies out of the import path.
AGENT_REGISTRY: dict[str, str] = {
    "ner_annotation": "api.ai.agents.annotation_agent.AnnotationAgent",   # Sprint 3
    "smart_search":   "api.ai.agents.search_agent.SearchAgent",           # Sprint 4
    "diagnostic":     "api.ai.agents.diagnostic_agent.DiagnosticAgent",   # Sprint 5
    "reporter":       "api.ai.agents.reporter_agent.ReporterAgent",       # Sprint 6
}


def get_agent(name: str) -> "BaseAgent":
    """Instantiate and return the named agent."""
    if name not in AGENT_REGISTRY:
        raise ValueError(
            f"Unknown agent '{name}'. Registered agents: {list(AGENT_REGISTRY)}"
        )
    module_path, class_name = AGENT_REGISTRY[name].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    agent_class = getattr(module, class_name)
    return agent_class()
EOF
```

**Agent stub files** — one per sprint, so the registry imports don't fail:

```bash
for agent in annotation_agent search_agent diagnostic_agent reporter_agent; do
cat > api/ai/agents/${agent}.py << PYEOF
"""
${agent} — stub implementation.
Full implementation added in the designated sprint (see PRD §2.4).
"""
from api.ai.base_agent import BaseAgent


class $(echo $agent | sed 's/_agent/Agent/g' | sed 's/\b./\u&/g' | tr -d ' ')(BaseAgent):
    framework = "stub"
    sprint = 0
    max_iterations = None

    def run(self, input: dict) -> dict:
        raise NotImplementedError(
            f"${agent} not yet implemented — see PRD sprint for this agent."
        )
PYEOF
done
```

> **Note:** The class name formatting in the loop above may not work in all shells. If it fails, create each file manually with these class names: `AnnotationAgent`, `SearchAgent`, `DiagnosticAgent`, `ReporterAgent`.

**`tests/unit/test_agents.py`** — placeholder unit tests (must pass in Sprint 1 with stubs):

```bash
mkdir -p tests/unit

cat > tests/unit/test_agents.py << 'EOF'
"""
Agent Framework unit tests — Sprint 1: validates scaffolding only.
Full behaviour tests added per sprint as agents are implemented.
"""
import pytest
from api.ai.config import get_provider_config, LLM_PROVIDER
from api.ai.agent_registry import AGENT_REGISTRY, get_agent
from api.ai.provider import call_llm


def test_provider_config_resolves_local():
    config = get_provider_config("local")
    assert "model" in config
    assert "base_url" in config


def test_provider_config_resolves_gemini():
    config = get_provider_config("gemini")
    assert "model" in config


def test_provider_config_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider_config("nonexistent_model_xyz")


def test_agent_registry_contains_all_four_agents():
    expected = {"ner_annotation", "smart_search", "diagnostic", "reporter"}
    assert expected == set(AGENT_REGISTRY.keys())


def test_call_llm_stub_returns_string():
    result = call_llm("hello world", provider="local")
    assert isinstance(result, str)


def test_call_llm_structured_output_not_yet_implemented():
    from pydantic import BaseModel

    class FakeSchema(BaseModel):
        value: str

    with pytest.raises(NotImplementedError):
        call_llm("hello", provider="local", response_model=FakeSchema)
EOF
```

Run the tests to confirm everything imports correctly:

```bash
cd api
uv run pytest tests/unit/test_agents.py -v
# Expected: 5 passed
cd ..
```

Commit the agent scaffold:

```bash
git add api/ai/ tests/unit/test_agents.py api/pyproject.toml api/uv.lock
git commit -m "feat(sprint1): scaffold api/ai/ agent framework layer with stubs and unit tests"
```

> **Checkpoint:** `uv run pytest tests/unit/test_agents.py -v` shows 5 tests passing.

---

## Phase 8 · GitHub Actions CI/CD

### Step 15 — Add GitHub Secrets ★ (OCI secrets replace S3 secrets)

Go to your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value | Notes |
|---|---|---|
| `GCP_SA_KEY` | Full JSON content of your GCP service account key | For Artifact Registry push |
| `GCP_PROJECT_ID` | Your GCP project ID | e.g. `jmie-project-abc123` |
| `GCP_REGION` | Your GCP region | e.g. `southamerica-east1` |
| `ORACLE_VM_IP` | Oracle VM public IP address | For SSH deploy |
| `ORACLE_SSH_KEY` | Private key content from `~/.ssh/jmie_oracle` | For SSH deploy |
| `OCI_BUCKET_NAME` | `jmie-datalake` | Used in CD pipeline to verify connectivity |
| `OCI_NAMESPACE` | Your OCI namespace string | From `oci os ns get` |
| `OCI_REGION` | `sa-saopaulo-1` (or your region) | For OCI CLI in CI if needed |

> **What was removed vs. original Sprint 1:**
> `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are **no longer needed for S3** — the VM uses Instance Principal.
> These keys will be added back in Sprint 5 specifically for CloudWatch `PutMetricData`, scoped to that permission only.

---

### Step 16 — Create the three workflow files ★ (CI now runs agent tests)

```bash
mkdir -p .github/workflows
```

**`ci.yml` — runs on every push; now includes agent unit tests:**

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

      - name: Run unit tests (including agent scaffold tests)
        working-directory: api
        run: uv run pytest tests/unit/ -v --tb=short
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

      - name: Build and push API image (multi-platform)
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

**`docs.yml` — placeholder for Sprint 5:**

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

### Step 17 — Clone the repo on the Oracle VM and do the first production deploy

```bash
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# Authenticate Docker to GCP Artifact Registry
gcloud auth configure-docker YOUR_GCP_REGION-docker.pkg.dev

# Clone the repository
git clone https://github.com/YOUR_USERNAME/jmie.git
cd jmie

# Create the production env file
cp .env.prod.example .env.prod
nano .env.prod
# Set the following (leave OCI API key vars blank — Instance Principal handles auth):
#   ENV=production
#   OCI_BUCKET_NAME=jmie-datalake
#   OCI_NAMESPACE=your_namespace
#   OCI_REGION=sa-saopaulo-1
#   OCI_USE_MOCK=false
#   OCI_TENANCY_OCID=   ← leave blank (Instance Principal)
#   OCI_USER_OCID=      ← leave blank (Instance Principal)
#   OCI_FINGERPRINT=    ← leave blank (Instance Principal)
#   OCI_PRIVATE_KEY_PATH= ← leave blank (Instance Principal)
#   OCI_S3_COMPAT_ENDPOINT=https://YOUR_NAMESPACE.compat.objectstorage.sa-saopaulo-1.oraclecloud.com
#   OCI_S3_COMPAT_ACCESS_KEY=  ← Customer Secret Key access key (from OCI console)
#   OCI_S3_COMPAT_SECRET_KEY=  ← Customer Secret Key secret (from OCI console)
#   JMIE_USE_MOCK_SCRAPER=false
#   LLM_PROVIDER=gemini
#   All PostgreSQL, Airflow, GCP, FastAPI, Phoenix values

# Start the full production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.prod up -d

docker compose ps
```

Now trigger the CI/CD from your local machine:

```bash
git checkout dev
git add .
git commit -m "feat(sprint1): complete infrastructure scaffold with OCI storage and agent framework"
git push origin dev
# Open PR from dev → main on GitHub, merge it
# Watch Actions tab — cd.yml deploys to Oracle VM automatically
```

> **Checkpoint:** CD run completes. `curl http://YOUR_ORACLE_IP:8000/health` returns `{"status":"ok","service":"jmie-api"}`.

---

## Phase 9 · Verification

### Step 18 — Sprint 1 acceptance checklist ★ (OCI checks replace S3 checks)

```bash
ssh -i ~/.ssh/jmie_oracle ubuntu@YOUR_ORACLE_IP

# ── All 9 services running? ─────────────────────────────────────────────
docker compose ps --format "table {{.Name}}\t{{.Status}}"
# Expected: 9 rows, all State = Up

# ── OCI Object Storage from the VM (Instance Principal) ────────────────
oci os object put \
  --bucket-name jmie-datalake \
  --name sprint1-verify.txt \
  --file - \
  --auth instance_principal \
  <<< "vm-to-oci-sprint1-verify"

oci os object list \
  --bucket-name jmie-datalake \
  --auth instance_principal
# Expected: sprint1-verify.txt appears in the listing

oci os object delete \
  --bucket-name jmie-datalake \
  --name sprint1-verify.txt \
  --force \
  --auth instance_principal
# Expected: object deleted

# ── GCP Artifact Registry ───────────────────────────────────────────────
gcloud artifacts docker images list \
  YOUR_GCP_REGION-docker.pkg.dev/YOUR_GCP_PROJECT/jmie
# Expected: api:latest listed

# ── API health ──────────────────────────────────────────────────────────
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"jmie-api"}

# ── From your local machine ─────────────────────────────────────────────
curl http://YOUR_ORACLE_IP:8000/health
# Expected: {"status":"ok","service":"jmie-api"}

# ── Agent framework tests (on local machine) ────────────────────────────
cd api && uv run pytest tests/unit/test_agents.py -v
# Expected: 5 passed, 0 failed
```

**GitHub checks:**

- [ ] Push to `dev` triggers `ci.yml` — lint passes, 5 agent unit tests pass
- [ ] Merge to `main` triggers `cd.yml` — build + deploy passes
- [ ] Oracle VM shows latest API image after deploy

**Expected `docker compose ps` output:**

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

If all checks pass, Sprint 1 is done under PRD v2.1. The foundation is in place:

- **Oracle Cloud VM** running 24/7 with 9 containerised services
- **OCI Object Storage** bucket `jmie-datalake` with lifecycle rules and Instance Principal auth — no credentials on disk in production
- **GCP Artifact Registry** holding the first multi-platform Docker image
- **GitHub** repo with `dev`/`main` branch protection and all three CI/CD pipelines wired
- **Dev/prod environment split** verified: `OCI_USE_MOCK=true` in dev, Instance Principal in prod
- **`api/ai/` Agent Framework scaffold** committed: `BaseAgent`, `provider.py`, `AgentRegistry`, 4 agent stubs, 5 unit tests all passing

**Next up — Sprint 2:** Python scrapers for 2 EN + 2 PT job boards, the Airflow daily DAG, PostgreSQL schema with Alembic, and the OCI-to-Postgres loader (using `oci_helpers.py`).

---

*JMIE Sprint 1 Plan · Infrastructure Foundations · Generated from PRD v2.1*
*Changes from original Sprint 1: OCI Object Storage replaces AWS S3 · Instance Principal auth · `oci_helpers.py` replaces `s3_helpers.py` · AWS kept for CloudWatch only (Sprint 5) · `api/ai/` agent framework scaffold added as new Phase 7*