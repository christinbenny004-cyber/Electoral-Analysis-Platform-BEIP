CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.candidate_features;

CREATE TABLE gold.candidate_features AS
SELECT 
    e.year,
    e.state_name,
    a.constituency_name,
    a.candidate_name,
    a.party,
    
    -- Candidate Features (from Affidavits)
    a.criminal_cases,
    a.serious_criminal_cases,
    a.education,
    a.total_assets,
    a.total_liabilities,
    a.is_crorepati,
    
    -- Constituency Demographics (from Census, approximating constituency to district)
    c.total_population,
    c.literacy_rate,
    c.sex_ratio,
    c.sc_percentage,
    c.st_percentage,
    c.worker_participation,

    -- Electoral Context
    e.electors,
    e.turnout_percentage,
    e.n_cand as total_candidates,
    
    -- Target Variable
    CASE WHEN e.position = 1 THEN 1 ELSE 0 END AS won

FROM silver.candidate_affidavits a
JOIN silver.election_results e
    ON  a.year = e.year
    AND a.constituency_name = e.constituency_name
    AND a.candidate_name = e.candidate_name
LEFT JOIN silver.census_demographics c
    ON  e.state_name = c.state_name 
    AND a.constituency_name = c.district_name;

-- Add indexes for fast querying by ML scripts
CREATE INDEX idx_gold_features_year ON gold.candidate_features(year);
CREATE INDEX idx_gold_features_state ON gold.candidate_features(state_name);
