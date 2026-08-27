# BEIP — Bharat Election Intelligence Platform

A data engineering project that ingests, cleans, and structures Indian election data into a local Postgres data warehouse.

## What This Project Does

Pulls data from multiple public Indian election sources (Lok Dhaba, ECI, Census 2011, MyNeta, data.gov.in), loads it into a **Bronze** (raw) layer, validates it with Great Expectations, and promotes clean data to a **Silver** (curated) layer — all orchestrated by Apache Airflow.

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+

### Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd beip

# 2. Start Postgres
docker compose up -d

# 3. Create a Python virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment variables
cp .env.example .env
# Edit .env if you want different credentials
```

### Verify

```bash
# Check Postgres is running
docker compose exec postgres pg_isready

# Connect with psql
docker compose exec postgres psql -U beip -d beip_warehouse -c "\dn"
# Should show: bronze, silver, public
```

## Project Structure

```
beip/
├── data/
│   └── raw/                  ← downloaded source files (gitignored)
├── src/
│   ├── config.py             ← DB connection helper
│   ├── ingestion/            ← scripts that load raw files into Bronze tables
│   └── validation/           ← data quality checks + Silver transforms
├── sql/
│   ├── init/                 ← auto-runs on first Postgres boot
│   └── schema.sql            ← full schema reference
├── dags/                     ← Airflow DAGs (Week 3)
├── docker-compose.yml
├── requirements.txt

```

## Data Sources

| Source | Data | Access |
|---|---|---|
| Lok Dhaba (TCPD, Ashoka) | Election results by constituency & candidate | Free download — lokdhaba.ashoka.edu.in |
| ECI | Official election results | eci.gov.in |
| Census 2011 | District demographics | censusindia.gov.in |
| MyNeta / ADR | Candidate affidavits (assets, criminal cases) | myneta.info |
| data.gov.in | Open government datasets | API with key auth |

## Architecture

```
Raw Sources → Bronze (raw) → Validation → Silver (clean)
     ↑                                         ↑
  Ingestion scripts                    Transform scripts
     ↑                                         ↑
  ─────────── Orchestrated by Airflow ──────────
```

## Phase Roadmap

| Phase | Focus | Status |
|---|---|---|
| **Phase 1** | Data Engineering | ✅ Complete |
| **Phase 2** | Feature Engineering + ML | ✅ Complete |
| **Phase 3** | Serving + Deployment | 🚀 Next |
