# 🚀 TriageIQ Team Quick-Start Guide

For teammates who already have **Python 3.11+**, **Docker Desktop**, and **Git** installed on their computer.

---

### Step 1: Clone Repository & Create Virtual Environment

Open PowerShell or Command Prompt:

```powershell
git clone https://github.com/nsk724/autoTagger.git
cd autoTagger

# Create standard Python virtual environment (No Conda required)
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

---

### Step 2: Prepare Data & Train Baseline Model (~40s)

```powershell
# 1. Download dataset and create data/processed splits
python scripts/prepare_data.py

# 2. Train baseline model to artifacts/
python scripts/train_initial.py
```

---

### Step 3: Launch Docker Services

Make sure **Docker Desktop** is running, then:

```powershell
docker compose up -d
```

Verify the services are running with `docker compose ps`:
* **Reviewer UI (Nginx)**: [http://localhost:8085](http://localhost:8085) (Login: `reviewer1` / `reviewer1`)
* **Prometheus Targets**: [http://localhost:9090/targets](http://localhost:9090/targets) (Scrapes backend & feedback)
* **Grafana Dashboard**: [http://localhost:3005](http://localhost:3005) (Login: `admin` / `admin` -> *TriageIQ Overview*)
* **Model Inference API**: [http://localhost:8002/health](http://localhost:8002/health)

---

### Step 4: Verify with Smoke Test

```powershell
python scripts/smoke_test.py
```
*(Should pass 6/6 steps with `SMOKE OK`)*.

---

### Step 5: CI/CD and cloud deployment

GitHub Actions runs CI and, after the
one-time AWS setup in `infra/README.md`, deploys the frontend to S3/CloudFront
and the existing Docker Compose backend to EC2.

---

### Key Ports Summary

| Service | Port | Description |
| :--- | :--- | :--- |
| **Gateway UI** | `8085` | Nginx reverse proxy & reviewer frontend |
| **Grafana** | `3005` | Real-time accuracy, error ratio & drift dashboard |
| **Prometheus** | `9090` | Time-series metrics engine & alerts |
| **Model Service** | `8002` | Local CPU inference API |
| **PostgreSQL** | `5433` | Host port mapped to container port 5432 |
