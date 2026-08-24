# BEIP — Phase 1: Data Engineering (Weeks 1–4)
### Beginner Task Guide

This phase has one goal: **get real election data sitting cleanly in a database on your laptop.** Nothing fancy yet — no Airflow, no Feast, no Kubernetes. Just data in, data cleaned, data trustworthy.

---

## Before Week 1: Setup (do this first)

- [ ] Install **Docker Desktop** (this is how you'll run Postgres without installing it directly on your machine)
- [ ] Install **Python 3.11+**
- [ ] Install **VS Code** or **Google Antigravity IDE**
- [ ] Create a GitHub repo called `beip` (or similar)
- [ ] Create this folder structure inside it:

```
beip/
├── data/
│   ├── raw/              ← original downloaded files go here, untouched
├── src/
│   ├── ingestion/         ← scripts that load raw files into the DB
│   ├── validation/        ← data quality checks
├── sql/
│   ├── schema.sql          ← table definitions
├── docker-compose.yml
├── requirements.txt
├── README.md
```

- [ ] Create a `docker-compose.yml` that runs **just Postgres** (one service, nothing else). Ask me for this file if you want it written for you.
- [ ] `pip install pandas psycopg2-binary sqlalchemy python-dotenv` (add `great_expectations` later in Week 4)

**Checkpoint:** you can run `docker compose up`, connect to Postgres with a GUI tool (DBeaver or TablePlus), and see an empty database.

---

## Week 1 — Database Schema + First Data Source (ECI / Lok Dhaba)

**Goal:** Get one election's results into one table.

### What to do
1. Pick **one election** to start: Lok Sabha 2019.
2. Download the results CSV from **Lok Dhaba** (Ashoka University's election data project — free, no scraping needed, just register and download).
3. Open the CSV in Excel/pandas first. Just look at it. Understand every column before writing code.
4. Design a `bronze.election_results` table in `sql/schema.sql` that mirrors the CSV columns almost exactly (raw layer = don't clean anything yet).
5. Write one Python script: `src/ingestion/load_lok_dhaba.py` that reads the CSV with pandas and writes it into that Postgres table.
6. Confirm row counts match: rows in CSV = rows in table.

### Sources to use this week
| Source | What you get | How to get it |
|---|---|---|
| **Lok Dhaba** (Ashoka University TCPD) | Constituency-level LS/VS results, candidate-level detail | Free download, registration required — trihelicoidal.tcpd.ashoka.edu.in |
| **ECI (Election Commission of India)** | Official results, useful for cross-checking Lok Dhaba | eci.gov.in — statistical reports section |

### Concepts to actually understand before moving on
- Why raw data should never be modified (this is the "Bronze layer" idea)
- Primary keys: what uniquely identifies a row here? (constituency + year + candidate)
- Why you're using Postgres instead of just a CSV/pandas long-term

**Checkpoint:** `SELECT COUNT(*) FROM bronze.election_results;` returns a sensible number (~500-2000 rows for one LS election), and you can explain every column to a rubber duck.

---

## Week 2 — More Sources: Census, data.gov.in, MyNeta

**Goal:** Add two or three more raw tables. Practice the same load pattern on messier data.

### What to do
1. **Census 2011** — download district-level PCA (Primary Census Abstract) tables. These come as Excel files with messy headers — expect to spend real time just cleaning column names.
2. **MyNeta / ADR** — candidate affidavit data (assets, criminal cases, education). This may require light web scraping (BeautifulSoup) since it's not always a clean download.
3. **data.gov.in** — register for an API key, pull one dataset via their REST API just to practice authenticated API calls.
4. For each source: raw file → `bronze.<source_name>` table. Same pattern as Week 1, repeated.

### Sources to use this week
| Source | What you get | How to get it |
|---|---|---|
| **Census of India 2011** | District-level demographics (literacy, population, SC/ST %) | censusindia.gov.in — PCA tables |
| **MyNeta.info** | Candidate wealth, criminal cases, education | Site scraping (BeautifulSoup) or bulk download if available |
| **data.gov.in** | Various open government datasets | REST API, key-based auth |

### Concepts to understand
- Why district-level Census data won't map 1:1 onto constituencies (this is a real, unsolved-by-you data granularity problem — just note it, don't fix it yet)
- Basic web scraping etiquette (rate limiting, robots.txt)
- REST API authentication basics (API keys in headers)

**Checkpoint:** you have 3–4 bronze tables, each loaded by its own small script, each with a sensible row count.

---

## Week 3 — Orchestration (Apache Airflow)

**Goal:** Stop running scripts by hand. Let Airflow do it.

### What to do
1. Add Airflow to your `docker-compose.yml` (it needs its own Postgres metadata DB — usually easiest via the official Airflow docker-compose template, not built from scratch).
2. Take the scripts you already wrote in Weeks 1–2 and wrap each one in a simple Airflow **DAG** — one task per script, no fancy dependencies yet.
3. Get one DAG running end-to-end from the Airflow UI (localhost:8080).
4. Don't build the "real" scheduled DAGs from the proposal yet (daily/monthly triggers) — just prove you can run a DAG manually on demand.

### Concepts to understand
- What a DAG actually is (a graph of tasks with dependencies, not a cron job)
- Task vs. DAG vs. Operator
- Why orchestration matters once you have more than 2–3 pipelines

**Checkpoint:** you can trigger a DAG from the Airflow UI and watch it succeed, pulling data into a bronze table.

---

## Week 4 — Data Quality + Silver Layer

**Goal:** Turn raw, messy bronze data into trustworthy silver data.

### What to do
1. Install `great_expectations`.
2. Write 4–5 basic checks on your `bronze.election_results` table:
   - No nulls in `constituency_id`
   - `vote_share` is between 0 and 100
   - No duplicate (constituency, year, candidate) rows
   - Sum of vote shares per constituency is close to 100%
3. Write a transform script that reads from bronze, cleans it (standardize party name spellings, fix encoding issues, drop exact duplicates), and writes to `silver.election_results`.
4. Repeat lightly for at least one other source (e.g., silver.census_demographics).

### Concepts to understand
- Bronze vs. Silver vs. Gold (you're only building Bronze + Silver in Phase 1 — Gold comes in Phase 2 with feature engineering)
- Why validation happens *before* promotion to silver, not after
- The difference between a data quality *check* (test) and a data *transformation* (fix)

**Checkpoint (Milestone 1):**
- [ ] Postgres warehouse running with Bronze + Silver schemas
- [ ] At least 3 sources ingested (election results, census, one more)
- [ ] One Airflow DAG running successfully
- [ ] Great Expectations suite passing on your main table
- [ ] You can explain, out loud, what every table and column represents

---

## What NOT to do in Phase 1

- Don't touch Feast, MLflow, XGBoost, or Kubernetes yet — they belong to later phases and will just distract you
- Don't try to ingest all 15 sources — 3 to 4 is enough to prove the pattern
- Don't scrape aggressively or hit APIs without checking rate limits — you'll get blocked
- Don't skip understanding a script just to move faster — this project is explicitly learning-first

---

## Quick Reference: Week-by-Week Summary

| Week | Focus | Main Deliverable |
|---|---|---|
| 0 | Setup | Docker + Postgres running locally |
| 1 | First source | Lok Dhaba 2019 results in `bronze.election_results` |
| 2 | More sources | Census + MyNeta + data.gov.in in bronze tables |
| 3 | Orchestration | Airflow running your scripts as DAGs |
| 4 | Data quality | Great Expectations checks + Silver layer |

