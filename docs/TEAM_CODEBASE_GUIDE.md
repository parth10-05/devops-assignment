# 📘 TriageIQ Codebase & Architecture Guide

> **A Complete Teammate Reference for Code, Architecture, and Live Evaluation**  
> *Prepared for the TriageIQ MLOps Engineering Team (Nihar, Nand, Divyesh, Devan)*

---

## 📑 Table of Contents
1. [Project Overview & System Architecture](#1-project-overview--system-architecture)
2. [Root Directory & Configuration Files](#2-root-directory--configuration-files)
3. [Folder Deep-Dive](#3-folder-deep-dive)
   - [config/ (Labels & Drift Schema)](#a-config-labels--drift-schema)
   - [data/ (Raw, Processed & DVC Versioning)](#b-data-raw-processed--dvc-versioning)
   - [ml/ (Feature Extraction, Training & Tests)](#c-ml-triage_ml-package--tests)
   - [ops/ (Prometheus, Grafana & Alertmanager)](#d-ops-monitoring-dashboards--webhooks)
   - [scripts/ (Pipelines, Retraining & Smoke Tests)](#e-scripts-operational-tools--pipelines)
   - [services/ (The 6 Microservices)](#f-services-the-6-containerized-microservices)
4. [The Closed-Loop Automated Retraining Pipeline](#4-the-closed-loop-automated-retraining-pipeline)
5. [Evaluation Cheat-Sheet: URLs, Ports & Live Demo Steps](#5-evaluation-cheat-sheet-urls-ports--live-demo-steps)

---

## 1. Project Overview & System Architecture

**TriageIQ** is an enterprise MLOps platform that automatically routes incoming customer support tickets into 10 specialized queues. It incorporates **Human-in-the-Loop (HITL)** active learning, real-time observability, concept drift detection, and an **event-driven automated retraining pipeline**.

```
                           [ Customer Support Tickets ]
                                        │
                                        ▼
                           ┌─────────────────────────┐
                           │  Gateway (Nginx: 8085)  │ ◄─── Human Reviewers
                           └────────────┬────────────┘      (Reviewer Web UI)
                                        │
                         ┌──────────────┴───────────────┐
                         ▼                              ▼
             ┌──────────────────────┐        ┌──────────────────────┐
             │ backend-api (8000)   │        │feedback-service(8001)│
             └───────────┬──────────┘        └──────────┬───────────┘
                         │                              │
                ┌────────┴────────┐                     │
                ▼                 ▼                     ▼
     ┌──────────────────┐  ┌────────────────────────────────────┐
     │model-service:8002│  │         PostgreSQL (5433)          │
     │(Hybrid Classifier)  │  (tickets, predictions, feedback)  │
     └──────────────────┘  └────────────────────────────────────┘
                                        ▲
════════════════════════════ Observability ════════════════════════════
                                        │
┌──────────────────┐       ┌────────────┴─────────────┐       ┌────────────────────┐
│ Grafana (:3005)  │ ◄──── │   Prometheus (:9090)     │ ─────►│Alertmanager (:9093)│
│ (Live Dashboards)│       │ (Scrapes metrics every 5s)│       │(Alert visibility)  │
└──────────────────┘       └──────────────────────────┘       └────────────────────┘

════════════════════ GitHub Actions delivery on push to main ════════════════════
                                                                  │
                                                     tests + scans + deploy
                                                                  ▼
                                                      CloudFront + EC2 Compose
```

---

## 2. Root Directory & Configuration Files

| File | Purpose | Why It Is Crucial |
| :--- | :--- | :--- |
| **`docker-compose.yml`** | Multi-container orchestration | Spins up all 9 services (gateway, backend-api, feedback-service, model-service, postgres, ticket-generator, prometheus, alertmanager, grafana) with memory limits, healthchecks, and internal networks. |
| **`requirements.txt`** | Python environment dependencies | Core libraries (`fastapi`, `uvicorn`, `scikit-learn`, `sentence-transformers`, `torch`, `pandas`, `psycopg`) required for local virtual environment (`.venv`). |
| **`pyproject.toml`** | Testing & Linting configuration | Configures `pytest` with `pythonpath = ["ml"]` and test markers so tests resolve the `triage_ml` package automatically. |
| **`.env`** | Local secrets and environment vars | Stores database passwords, ports, and gateway auth hashes. Cloud deployment secrets live in GitHub Environment secrets and Parameter Store. |
| **`.gitignore`** | Git exclusion list | Excludes heavy model binaries (`artifacts/`), local `.env`, and virtual environments (`.venv/`) from bloating the Git repo. |
| **`.dockerignore`** | Build context optimizer | Excludes git logs, test caches, and documentation from being copied into container builds, accelerating build times. |
| **`README.md`** | Main project documentation | High-level overview, quickstart instructions, and system service table. |
| **`STARTUP_GUIDE.md`** | Teammate 5-minute setup guide | Step-by-step instructions for teammates cloning the repo onto fresh laptops. |

---

## 3. Folder Deep-Dive

---

### A. `config/` (Labels & Drift Schema)
* **`config/labels.yaml`**: The single source of truth for ticket classification labels across backend, frontend, and ML models:
  ```yaml
  labels:
    - Technical Support
    - Product Support
    - Customer Service
    - IT Support
    - Billing and Payments
    - Returns and Exchanges
    - Sales and Pre-Sales
    - Human Resources
    - General Inquiry
    - Service Outages and Maintenance
  heldout_labels:
    - Service Outages and Maintenance
  ```
* **Why `heldout_labels` matters**:
  `Service Outages and Maintenance` is intentionally excluded from initial training. When testing drift detection, the `ticket-generator` streams this heldout category. Because the model has never learned it, errors spike, triggering the **30% error threshold alert** in Prometheus!

---

### B. `data/` (Raw, Processed & DVC Versioning)
* **Data Source**: Hugging Face `Tobi-Bueck/customer-support-tickets` (61,765 raw customer support tickets).
* **`data/raw/`**:
  - `tickets.parquet` (24.6 MB): The original unmodified parquet file.
  - `tickets.parquet.dvc`: Data Version Control (DVC) pointer tracking the raw data hash.
* **`data/processed/`** (Cleaned, deduplicated, and split):
  - **`train.parquet`** (13,685 rows): Training split used for model training.
  - **`val.parquet`** (2,281 rows): Validation split used for hyperparameter tuning ($C$).
  - **`golden.parquet`** (2,281 rows): Fixed out-of-sample benchmark test set (never touched in training).
  - **`stream.parquet`** (4,562 rows): Replayed by `ticket-generator` to simulate production traffic.
  - **`heldout.parquet`** (937 rows): Contains isolated `Service Outages and Maintenance` tickets for drift simulation.
* **`stats.json`**: Machine-readable statistics showing exact row counts and label distributions across all splits.
* **`README.md`**: CC BY-NC 4.0 license attribution and baseline model metrics.

---

### C. `ml/` (`triage_ml` Package & Tests)
Contains the Python package `triage_ml` and its automated test suite:

#### Core Modules (`ml/triage_ml/`):
* **`text.py`**:
  - Normalizes text: joins `subject` and `body` into `"Subject: ... \n\n Body: ..."`.
  - **Hybrid Feature Extraction**: Combines **TF-IDF word n-grams (1-2 words)** with dense semantic embeddings from **`all-MiniLM-L6-v2`** into a single feature matrix.
  - *Why hybrid?* Dense embeddings alone achieved only 0.27 Macro-F1 (struggled with technical keywords like VPN or invoice); TF-IDF alone achieved 0.60; combining both achieved **61.5% Accuracy and 0.602 Macro-F1**.
* **`prepare.py`**: Reads raw parquet, filters English non-empty tickets, deduplicates identical rows, and performs stratified splitting.
* **`train.py`**: Fits a `LogisticRegression(class_weight="balanced")` across grid $C \in \{1, 10, 100\}$. Evaluates on `golden.parquet`, and saves `classifier.joblib`, `metadata.json`, and `model_card.json`.
* **`evaluate.py`**: Implements Champion vs. Challenger model validation (compares candidate model metrics against active production model).
* **`export_feedback.py`**: Queries PostgreSQL `labeled_feedback` view for human review corrections and creates versioned snapshots for retraining.
* **`runs.py`**: Manages retraining state and enforces cooldown periods.
* **`promote.py`**: Updates model registry status (`production` vs. `retired`) in the database.

#### Automated Test Suite (`ml/tests/`):
* `test_text.py`: Verifies text normalization and feature concatenation.
* `test_prepare.py`: Asserts `heldout` categories never leak into `train.parquet`.
* `test_train.py`: Fast offline training test using a mock embedder (<0.5s execution).
* `test_dry_runs.py`: Tests CLI commands (`runs`, `export_feedback`, `promote`) without network or database dependencies.
* `test_integration.py`: End-to-end integration test (train $\to$ save $\to$ evaluate).

---

### D. `ops/` (Monitoring, Dashboards & Webhooks)

#### 1. `ops/prometheus/` (Metrics & Alerting Engine)
* **`prometheus.yml`**: Configures Prometheus to scrape `/metrics` from `backend-api` and `feedback-service` every **5 seconds**. Points alert notifications to `alertmanager:9093`.
* **`alerts.yml`**: Contains PromQL recording rules and the retraining alert:
  ```yaml
  - record: triageiq:feedback_error_ratio_1h
    expr: |
      sum by (model_version) (increase(triageiq_feedback_incorrect_total[1h]))
      /
      sum by (model_version) (increase(triageiq_feedback_total[1h]))
  - alert: ModelErrorRateHigh
    expr: triageiq:feedback_error_ratio_1h > 0.50 and triageiq:feedback_count_1h >= 20
    for: 1m
    labels:
      severity: retrain
  ```
  - **Threshold 0.50**: Triggers whenever reviewer error rate exceeds 50% (prevents false alarms since healthy baseline has ~38% error).
  - **Count $\ge$ 20**: Requires at least 20 reviews for statistical significance.
  - **For 1m**: 1-minute debounce window before firing.
  - **Repeat Interval 30m**: Alertmanager repeats a visible alert at most every 30 minutes.

#### 2. `ops/grafana/` (Zero-Click Pre-provisioned Dashboards)
* **`provisioning/datasources/datasources.yaml`**: Auto-mounts Prometheus as default datasource.
* **`provisioning/dashboards/dashboards.yaml`**: Auto-loads dashboards from disk every 10 seconds.
* **`dashboards/triageiq-overview.json`**: Pre-built *TriageIQ Overview* dashboard with 5 panels:
  1. *Tickets Processed / Min* (Throughput rate)
  2. *Live Model Accuracy (1h)* ($1 - \text{error ratio}$)
  3. *Error Ratio vs 0.50 Alert Threshold* (Time-series with red threshold line at 0.50)
  4. *Predicted Queue Mix (Drift Signal)* (Stacked area distribution across queues)
  5. *Human Reviews in Last Hour* (Total review count)

#### 3. `ops/alertmanager/` (Local Alert Visibility)
* **`alertmanager.yml`**: Receives `ModelErrorRateHigh` alerts from Prometheus for the local observability demonstration. Deployment automation deliberately remains in GitHub Actions so releases are tied to reviewed commits rather than alert webhooks.

---

### E. `scripts/` (Operational Tools & Pipelines)

| Script | Purpose |
| :--- | :--- |
| **`prepare_data.py`** | Downloads/reads raw dataset and generates the 5 `data/processed/*.parquet` splits. |
| **`train_initial.py`** | Trains the baseline model locally and populates `artifacts/` (`classifier.joblib`, `metadata.json`, `model_card.json`). |
| **`smoke_test.py`** | End-to-end 6-step black-box HTTP verification through Gateway (healthz, labels, ticket prediction, pending queue, feedback submission, 409 idempotency check). |
| **`retrain_local.py`** | Continuous retraining engine: queries PostgreSQL `labeled_feedback` view, concatenates human corrections into training data, fits new model, writes timestamped artifacts, and promotes version in database. |
| **`run_pipeline.py`** | Master 3-stage CI/CD pipeline: **Stage 1 (Pytest)** $\to$ **Stage 2 (Retrain with feedback)** $\to$ **Stage 3 (Restart `model-service` & verify health)**. |

---

### F. `services/` (The 6 Containerized Microservices)

```text
services/
├── gateway/              # Nginx Reverse Proxy (8085) + Reviewer Web UI
├── backend-api/          # Ticket Ingestion & Routing API (8000)
├── feedback-service/     # Human Review Submission & Metrics API (8001)
├── model-service/        # Low-latency ML Inference Service (8002)
├── postgres/             # Database (5433) + Schema Migrations
└── ticket-generator/     # Background Traffic & Drift Simulator
```

1. **`gateway/`** (`port 8085`):
   - Nginx reverse proxy with Basic Authentication (`smoke:smoke`).
   - Routes `/api/*` to `backend-api` and `/feedback-api/*` to `feedback-service`.
   - Serves the **Reviewer Web UI** ([frontend/index.html](file:///d:/MLOps/services/gateway/frontend/index.html), `app.js`, `styles.css`) where support agents review tickets and submit corrections.
2. **`backend-api/`** (`port 8000`):
   - Ingestion API (FastAPI). Receives `POST /tickets`, calls `model-service:8000/predict`, saves ticket & prediction to PostgreSQL, and emits Prometheus metrics (`triageiq_predictions_total`).
3. **`feedback-service/`** (`port 8001`):
   - Human feedback API (FastAPI). Receives reviewer verdicts (`is_correct: true/false`, `corrected_label`).
   - **Idempotency**: Returns `409 Conflict` if the same prediction is reviewed twice.
   - **Metrics Engine**: Increments `triageiq_feedback_total` and `triageiq_feedback_incorrect_total`.
4. **`model-service/`** (`port 8002`):
   - Real-time ML inference service (FastAPI + Uvicorn).
   - Background model loading (returns `503` on `/health` until model is ready).
   - Mounts host `./artifacts:/app/artifacts:ro` as read-only.
   - Computes TF-IDF + Sentence-Transformers embeddings and returns predicted label, confidence, and top-3 classes.
5. **`postgres/`** (`port 5433`):
   - PostgreSQL 16 initialized via [migrations/001_init.sql](file:///d:/MLOps/services/postgres/migrations/001_init.sql).
   - Manages tables: `tickets`, `predictions`, `feedback`, `model_versions`, `training_runs`.
   - Creates the **`labeled_feedback`** SQL view:
     ```sql
     CREATE VIEW labeled_feedback AS
     SELECT f.feedback_id, t.subject, t.body,
            COALESCE(f.corrected_label, p.predicted_label) AS label
     FROM feedback f
     JOIN predictions p USING (prediction_id)
     JOIN tickets t USING (ticket_id)
     WHERE t.source <> 'smoke';
     ```
6. **`ticket-generator/`** (Internal background container):
   - Simulates production user traffic by reading `stream.parquet` and sending a ticket every 15 seconds.
   - **Drift Simulation**: When `DRIFT_ENABLED=true`, streams tickets from `heldout.parquet` (`Service Outages and Maintenance`), inducing high error rates for evaluation demos.

---

## 4. Feedback and deployment workflow

Feedback remains available for local retraining. Public releases are automated
from GitHub Actions so the deployed revision is always a commit on `main`.

```
[1] Reviewers mark tickets incorrect
           │
           ▼
[2] Feedback Service records metrics
    (triageiq_feedback_incorrect_total increments)
           │
           ▼
[3] Prometheus scrapes metrics & evaluates alerts.yml
    (Error ratio exceeds 0.50 for 1m -> Alert turns FIRING locally)
           │
           ▼
[4] Reviewer feedback is available to retrain_local.py when a new model is needed
           │
           ▼
[5] A push to main triggers GitHub Actions
    ├── CI runs tests, linting, secret, dependency, SAST, and filesystem scans
    ├── Deployment trains the baseline release artifact and publishes the UI to S3
    └── EC2 receives the exact commit bundle through Systems Manager
           │
           ▼
[6] CloudFront serves the updated frontend and routes API paths to EC2
```

---

## 5. Evaluation Cheat-Sheet: URLs, Ports & Live Demo Steps

### Service Endpoints Table

| Service | Local URL | Default Credentials | What to Show Evaluators |
| :--- | :--- | :--- | :--- |
| **Reviewer Web UI** | [http://localhost:8085](http://localhost:8085) | `smoke` / `smoke` | Live pending tickets, human review interface, and instant feedback submission. |
| **Grafana Dashboard** | [http://localhost:3005](http://localhost:3005) | `admin` / `admin` | Real-time throughput, live accuracy, error ratio vs. 0.30 red alert line, and queue mix. |
| **Prometheus Alerts** | [http://localhost:9090/alerts](http://localhost:9090/alerts) | (No auth) | `ModelErrorRateHigh` alert state (Green Inactive $\to$ Yellow Pending $\to$ Red Firing). |
| **Alertmanager** | [http://localhost:9093](http://localhost:9093) | (No auth) | Local view of active alerts. |
| **GitHub Actions** | Repository **Actions** tab | GitHub access | CI and automatic deployment history for every push to `main`. |
| **Model Health API** | [http://localhost:8002/health](http://localhost:8002/health) | (No auth) | Returns `{"status": "ok", "model_version": "..."}` showing the active model version. |
| **PostgreSQL** | `localhost:5433` | `triageiq` / `postgres` | Tables and `labeled_feedback` view storing human corrections. |

---

### Step-by-Step Live Demo for Evaluators:

1. **Show the Web UI (`http://localhost:8085`)**:
   Show tickets streaming in every 10–15 seconds from `ticket-generator`.
2. **Show the Grafana Dashboard (`http://localhost:3005`)**:
   Point out the **red dotted line at 0.30 (30%)** on the *Error Ratio* panel.
3. **Simulate Model Drift / Operator Corrections**:
   Review ~10–12 tickets in the Web UI and mark them as **"Incorrect"** (or let drift tickets stream).
4. **Watch the Alert Fire in Prometheus (`http://localhost:9090/alerts`)**:
   Show that once the error ratio exceeds **30%**, `ModelErrorRateHigh` turns 🔴 **FIRING**.
5. **Show the GitHub Actions deployment**:
   Push a small reviewed change to `main`, then show the successful CI and deployment workflow runs.
6. **Show the CloudFront URL**:
   Open the Terraform `frontend_url` output and demonstrate that the reviewer UI and API calls work through the one HTTPS address.
