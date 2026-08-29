# BEIP — Bharat Election Intelligence Platform 🇮🇳

An end-to-end data engineering, machine learning, and analytics platform that ingests, cleans, analyzes, and visualizes Indian parliamentary election data and candidate affidavits.

---

## 🌟 Features & Highlights

- **Medallion Lakehouse Architecture:** Multi-hop pipeline (Bronze raw ➔ Silver curated ➔ Gold feature store) built on PostgreSQL.
- **Automated Data Quality & Validation:** Schema enforcement, deduplication, and sanity checking.
- **Machine Learning Insights:** Random Forest classification model trained on 8,900+ candidate features with Gini importance scoring.
- **Modern Analytical Dashboard:** Luxury, high-contrast light-themed React (Vite) application with Recharts visualizations, interactive filters, and analytical figure intelligence cards.
- **FastAPI REST Service:** High-performance async backend powering live statistics and paginated data queries.

---

## 🏗️ Architecture

```
                               ┌─────────────────────────────────────────────────────────────┐
                               │                    Data Lakehouse Pipeline                  │
                               └─────────────────────────────────────────────────────────────┘
  Raw Public Data Sources
  ├── Lok Dhaba (TCPD)    ──►  [ Bronze Layer ]   ──►  [ Silver Layer ]   ──►  [ Gold Layer ]
  ├── MyNeta / ADR (Affidavits) (Raw Staging)          (Clean & Curated)      (Analytics & Features)
  └── Census 2011 (Demographics)
                                                                                    │
                                                                                    ▼
                                                                       ┌─────────────────────────┐
                                                                       │  ML Pipeline (sklearn)  │
                                                                       │  Random Forest (97.9%)  │
                                                                       └─────────────────────────┘
                                                                                    │
                                                                                    ▼
┌──────────────────────────────┐                              ┌─────────────────────────┐
│     React / Vite UI App      │  ◄───── HTTP / REST ───────  │     FastAPI Backend     │
│  (Modern Luxury Light Theme) │       localhost:8000         │   (Async Python API)    │
└──────────────────────────────┘                              └─────────────────────────┘
```

---

## 📊 Data Sources

| Source | Description | Coverage |
|---|---|---|
| **Lok Dhaba (TCPD, Ashoka)** | Constituency & candidate election results | Lok Sabha elections |
| **MyNeta / ADR** | Candidate self-declared affidavits (cases, wealth, education) | Candidate profiles |
| **Census 2011** | District-level demographic, literacy, and population data | Primary Census Abstract |
| **data.gov.in / ECI** | Open government datasets and official electoral records | Parliamentary data |

---

## 📁 Project Structure

```
beip/
├── data/
│   └── raw/                  ← Raw dataset files (gitignored)
├── dags/                     ← Airflow curation & orchestration DAGs
├── models/                   ← Serialized ML models (election_predictor.pkl)
├── notebooks/                ← Jupyter EDA notebooks (Elections, Affidavits, Census)
├── sql/
│   ├── init/                 ← Auto-run schema initialization
│   ├── schema.sql            ← Master PostgreSQL schema reference
│   └── transform/            ← Gold layer feature engineering SQL scripts
├── src/
│   ├── config.py             ← Database connection engine
│   ├── ingestion/            ← Raw data loaders into Bronze layer
│   ├── validation/           ← Cleansing & transformation into Silver layer
│   ├── ml/                   ← Model training and feature importance scripts
│   └── api/                  ← FastAPI REST backend
│       ├── main.py           ← API application entry point & CORS
│       └── routes/           ← Endpoints (elections, insights, predictions)
├── frontend/                 ← React + Vite Web Application
│   ├── src/
│   │   ├── components/       ← Sidebar, StatCard, and reusable UI
│   │   ├── pages/            ← Overview, Election Explorer, Key Insights
│   │   ├── api.js            ← Frontend API client
│   │   └── index.css         ← Modern luxury light design system
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml        ← PostgreSQL container setup
├── requirements.txt          ← Python dependencies
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for PostgreSQL)
- Python 3.11+
- Node.js 18+ & npm

---

### 2. Database Setup

```bash
# Clone the repository
git clone https://github.com/christinbenny004-cyber/Electoral-Analysis-Platform-BEIP.git
cd Electoral-Analysis-Platform-BEIP

# Start PostgreSQL database container
docker compose up -d

# Verify Postgres container is healthy
docker compose exec postgres pg_isready
```

---

### 3. Backend & API Setup

```bash
# Create & activate Python virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI REST Server
uvicorn src.api.main:app --reload --port 8000
```
> API will be live at: **http://localhost:8000** (Interactive Docs: `http://localhost:8000/docs`)

---

### 4. Frontend Dashboard Setup

In a new terminal window:

```bash
cd frontend

# Install UI dependencies
npm install

# Start Vite React development server
npm run dev
```
> Dashboard will be live at: **http://localhost:5173**

---

## 📈 Phase Roadmap

| Phase | Milestone | Status |
|---|---|---|
| **Phase 1** | Data Engineering (Bronze & Silver Layers, Ingestion, Quality Validation) | ✅ Complete |
| **Phase 2.1** | Exploratory Data Analysis (Jupyter Notebooks for Elections, Affidavits & Census) | ✅ Complete |
| **Phase 2.2** | Machine Learning & Gold Layer (Random Forest Model Training & Serialization) | ✅ Complete |
| **Phase 3** | Serving & Web Dashboard (FastAPI REST Backend + React Luxury UI) | ✅ Complete |

---

## 📜 License & Acknowledgments

- **Data Providers:** Election Commission of India (ECI), Trivedi Centre for Political Data (TCPD), Association for Democratic Reforms (ADR / MyNeta), and Office of the Registrar General & Census Commissioner.
- Created for advanced electoral intelligence and democratic data transparency.
