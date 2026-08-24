-- ============================================
-- BEIP — Database Initialization
-- ============================================
-- This script runs automatically on first Postgres boot
-- via the docker-entrypoint-initdb.d mount.
--
-- It creates the Bronze and Silver schemas.
-- Table definitions are added as the project progresses.
-- ============================================

-- Create schemas for the medallion architecture
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;

-- ============================================
-- BRONZE LAYER — Raw data, mirrors source structure
-- ============================================

-- Lok Dhaba: Lok Sabha / Vidhan Sabha election results (candidate-level)
CREATE TABLE IF NOT EXISTS bronze.election_results (
    id                  SERIAL PRIMARY KEY,
    year                INTEGER,
    state_name          TEXT,
    constituency_name   TEXT,
    constituency_number INTEGER,
    constituency_type   TEXT,          -- GEN, SC, ST
    candidate_name      TEXT,
    sex                 TEXT,
    age                 INTEGER,
    party               TEXT,
    votes               INTEGER,
    vote_share          NUMERIC(6,2),
    position            INTEGER,
    deposit_lost        TEXT,          -- Yes/No as-is from source
    electors            INTEGER,
    turnout_percentage  NUMERIC(6,2),
    -- Metadata
    source_file         TEXT,          -- which CSV this row came from
    loaded_at           TIMESTAMP DEFAULT NOW(),
    -- Uniqueness constraint (not a PK — bronze allows some messiness)
    UNIQUE (year, state_name, constituency_name, candidate_name)
);

-- Census 2011: District-level Primary Census Abstract
CREATE TABLE IF NOT EXISTS bronze.census_demographics (
    id                      SERIAL PRIMARY KEY,
    state_code              TEXT,
    district_code           TEXT,
    state_name              TEXT,
    district_name           TEXT,
    total_population        BIGINT,
    male_population         BIGINT,
    female_population       BIGINT,
    total_literate          BIGINT,
    male_literate           BIGINT,
    female_literate         BIGINT,
    sc_population           BIGINT,
    st_population           BIGINT,
    total_workers           BIGINT,
    -- Metadata
    source_file             TEXT,
    loaded_at               TIMESTAMP DEFAULT NOW(),
    UNIQUE (state_code, district_code)
);

-- MyNeta / ADR: Candidate affidavit data
CREATE TABLE IF NOT EXISTS bronze.candidate_affidavits (
    id                      SERIAL PRIMARY KEY,
    year                    INTEGER,
    state_name              TEXT,
    constituency_name       TEXT,
    candidate_name          TEXT,
    party                   TEXT,
    criminal_cases          INTEGER,
    serious_criminal_cases  INTEGER,
    education               TEXT,
    total_assets            BIGINT,      -- in INR
    total_liabilities       BIGINT,      -- in INR
    -- Metadata
    source_url              TEXT,
    source_file             TEXT,
    loaded_at               TIMESTAMP DEFAULT NOW(),
    UNIQUE (year, state_name, constituency_name, candidate_name)
);

-- ============================================
-- SILVER LAYER — Cleaned, validated, standardized
-- ============================================

-- Cleaned election results
CREATE TABLE IF NOT EXISTS silver.election_results (
    id                  SERIAL PRIMARY KEY,
    year                INTEGER NOT NULL,
    state_name          TEXT NOT NULL,
    constituency_name   TEXT NOT NULL,
    constituency_number INTEGER,
    constituency_type   TEXT,
    candidate_name      TEXT NOT NULL,
    sex                 TEXT,
    age                 INTEGER,
    party               TEXT NOT NULL,       -- standardized party names
    votes               INTEGER NOT NULL,
    vote_share          NUMERIC(6,2),
    position            INTEGER NOT NULL,
    deposit_lost        BOOLEAN,             -- converted from Yes/No to boolean
    electors            INTEGER,
    turnout_percentage  NUMERIC(6,2),
    -- Metadata
    bronze_id           INTEGER REFERENCES bronze.election_results(id),
    promoted_at         TIMESTAMP DEFAULT NOW(),
    UNIQUE (year, state_name, constituency_name, candidate_name)
);

-- Cleaned census demographics
CREATE TABLE IF NOT EXISTS silver.census_demographics (
    id                      SERIAL PRIMARY KEY,
    state_name              TEXT NOT NULL,
    district_name           TEXT NOT NULL,
    total_population        BIGINT NOT NULL,
    male_population         BIGINT,
    female_population       BIGINT,
    literacy_rate           NUMERIC(5,2),     -- computed from raw counts
    sex_ratio               NUMERIC(7,2),     -- females per 1000 males
    sc_percentage           NUMERIC(5,2),     -- computed
    st_percentage           NUMERIC(5,2),     -- computed
    worker_participation    NUMERIC(5,2),     -- workers / population
    -- Metadata
    bronze_id               INTEGER REFERENCES bronze.census_demographics(id),
    promoted_at             TIMESTAMP DEFAULT NOW(),
    UNIQUE (state_name, district_name)
);

-- Cleaned candidate affidavits (MyNeta / ADR)
-- Includes derived boolean flags ready for Phase 2 ML feature engineering
CREATE TABLE IF NOT EXISTS silver.candidate_affidavits (
    id                      SERIAL PRIMARY KEY,
    year                    INTEGER NOT NULL,
    state_name              TEXT NOT NULL,
    constituency_name       TEXT NOT NULL,
    candidate_name          TEXT NOT NULL,
    party                   TEXT,                    -- standardized party names
    criminal_cases          INTEGER DEFAULT 0,       -- 0 = no declared cases
    serious_criminal_cases  INTEGER DEFAULT 0,
    has_criminal_case       BOOLEAN,                 -- derived: criminal_cases >= 1
    has_serious_case        BOOLEAN,                 -- derived: serious_criminal_cases >= 1
    education               TEXT,                    -- bucketed: Graduate, Post Graduate, etc.
    total_assets            BIGINT,                  -- in INR
    total_liabilities       BIGINT,                  -- in INR
    is_crorepati            BOOLEAN,                 -- derived: total_assets > 1 Crore
    -- Metadata
    bronze_id               INTEGER REFERENCES bronze.candidate_affidavits(id),
    promoted_at             TIMESTAMP DEFAULT NOW(),
    UNIQUE (year, state_name, constituency_name, candidate_name)
);
