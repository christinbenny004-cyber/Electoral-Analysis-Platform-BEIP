-- ============================================
-- BEIP — Auto-init script for Docker
-- ============================================
-- This runs on first Postgres container boot.
-- Creates schemas and all Bronze/Silver tables.
-- ============================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;

-- ============================================
-- BRONZE TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS bronze.election_results (
    id                  SERIAL PRIMARY KEY,
    year                INTEGER,
    state_name          TEXT,
    constituency_name   TEXT,
    constituency_number INTEGER,
    constituency_type   TEXT,
    candidate_name      TEXT,
    sex                 TEXT,
    age                 INTEGER,
    party               TEXT,
    votes               INTEGER,
    vote_share          NUMERIC(6,2),
    position            INTEGER,
    deposit_lost        TEXT,
    electors            INTEGER,
    turnout_percentage  NUMERIC(6,2),
    source_file         TEXT,
    loaded_at           TIMESTAMP DEFAULT NOW(),
    UNIQUE (year, state_name, constituency_name, candidate_name)
);

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
    source_file             TEXT,
    loaded_at               TIMESTAMP DEFAULT NOW(),
    UNIQUE (state_code, district_code)
);

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
    total_assets            BIGINT,
    total_liabilities       BIGINT,
    source_url              TEXT,
    source_file             TEXT,
    loaded_at               TIMESTAMP DEFAULT NOW(),
    UNIQUE (year, state_name, constituency_name, candidate_name)
);

-- ============================================
-- SILVER TABLES
-- ============================================

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
    party               TEXT NOT NULL,
    votes               INTEGER NOT NULL,
    vote_share          NUMERIC(6,2),
    position            INTEGER NOT NULL,
    deposit_lost        BOOLEAN,
    electors            INTEGER,
    turnout_percentage  NUMERIC(6,2),
    bronze_id           INTEGER,
    promoted_at         TIMESTAMP DEFAULT NOW(),
    UNIQUE (year, state_name, constituency_name, candidate_name)
);

CREATE TABLE IF NOT EXISTS silver.census_demographics (
    id                      SERIAL PRIMARY KEY,
    state_name              TEXT NOT NULL,
    district_name           TEXT NOT NULL,
    total_population        BIGINT NOT NULL,
    male_population         BIGINT,
    female_population       BIGINT,
    literacy_rate           NUMERIC(5,2),
    sex_ratio               NUMERIC(7,2),
    sc_percentage           NUMERIC(5,2),
    st_percentage           NUMERIC(5,2),
    worker_participation    NUMERIC(5,2),
    bronze_id               INTEGER,
    promoted_at             TIMESTAMP DEFAULT NOW(),
    UNIQUE (state_name, district_name)
);

-- Grant usage (helpful if connecting as a non-superuser later)
GRANT USAGE ON SCHEMA bronze TO PUBLIC;
GRANT USAGE ON SCHEMA silver TO PUBLIC;
