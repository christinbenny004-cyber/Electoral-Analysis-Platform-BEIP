"""
BEIP -- Phase 2: Feature Engineering

Joins the three Silver layer tables to produce a single, flat,
model-ready analytical dataset: one row per candidate per election.

Silver tables joined:
    silver.election_results       -- who ran, how many votes, did they win?
    silver.candidate_affidavits   -- criminal cases, assets, education
    silver.census_demographics    -- district-level literacy, population, sex ratio

Output table:
    gold.candidate_features       -- flat feature table for ML models

Key features produced:
    Candidate profile:
        - party (standardized)
        - education_level
        - has_criminal_case, has_serious_case
        - is_crorepati, log_total_assets
        - total_liabilities

    Electoral context:
        - year
        - constituency_type (GEN / SC / ST)
        - n_candidates (field size)
        - turnout_percentage

    District context (from Census 2011):
        - district_literacy_rate
        - district_sex_ratio
        - district_sc_percentage
        - district_st_percentage
        - district_worker_participation
        - log_district_population

    Target variable:
        - won  (1 = position 1, 0 = otherwise)

Usage:
    python -m src.ml.feature_engineering
    python -m src.ml.feature_engineering --year 2019
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Data Loading
# ============================================

def load_election_results(year: int = None) -> pd.DataFrame:
    """Load silver.election_results, optionally filtered by year."""
    engine = get_engine()
    query = "SELECT * FROM silver.election_results"
    if year:
        query += f" WHERE year = {int(year)}"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    print(f"  [LOAD] election_results: {len(df):,} rows")
    return df


def load_candidate_affidavits(year: int = None) -> pd.DataFrame:
    """Load silver.candidate_affidavits, optionally filtered by year."""
    engine = get_engine()
    query = "SELECT * FROM silver.candidate_affidavits"
    if year:
        query += f" WHERE year = {int(year)}"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    print(f"  [LOAD] candidate_affidavits: {len(df):,} rows")
    return df


def load_census_demographics() -> pd.DataFrame:
    """Load silver.census_demographics (Census 2011 — no year filter needed)."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM silver.census_demographics", conn)
    print(f"  [LOAD] census_demographics: {len(df):,} rows")
    return df


# ============================================
# Feature Construction
# ============================================

def build_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add binary target variable:
        won = 1 if position == 1 (candidate came first), else 0
    """
    df = df.copy()
    df["won"] = (df["position"] == 1).astype(int)
    print(f"  [TARGET] Winners: {df['won'].sum():,} / {len(df):,} candidates")
    return df


def join_affidavits(elections: pd.DataFrame, affidavits: pd.DataFrame) -> pd.DataFrame:
    """
    Left join affidavit data onto election results.
    Join key: year + state_name + constituency_name + candidate_name
    Not all candidates will have affidavit data (older elections / missing filings).
    """
    join_keys = ["year", "state_name", "constituency_name", "candidate_name"]
    affidavit_cols = [
        *join_keys,
        "criminal_cases", "serious_criminal_cases",
        "has_criminal_case", "has_serious_case",
        "education", "total_assets", "total_liabilities", "is_crorepati",
    ]
    # Only keep columns that exist in the loaded data
    affidavit_cols = [c for c in affidavit_cols if c in affidavits.columns]

    merged = elections.merge(
        affidavits[affidavit_cols],
        on=join_keys,
        how="left",
    )
    matched = merged["has_criminal_case"].notna().sum()
    print(f"  [JOIN] Affidavit match rate: {matched:,}/{len(merged):,} "
          f"({matched/len(merged)*100:.1f}%)")
    return merged


def join_census(df: pd.DataFrame, census: pd.DataFrame) -> pd.DataFrame:
    """
    Left join district-level census metrics onto candidate rows.

    Matching strategy:
        - Join on state_name (exact match after Silver standardization)
        - Since constituency != district, we use a fuzzy approach:
          pick the census district whose name is the closest match
          to the constituency name within the same state.

    NOTE: For a production system, you would maintain a
    constituency-to-district mapping table. This is a reasonable
    approximation for an initial Phase 2 baseline.
    """
    # Rename census columns to avoid clashes
    census_renamed = census.rename(columns={
        "district_name": "census_district_name",
        "total_population": "district_population",
        "literacy_rate": "district_literacy_rate",
        "sex_ratio": "district_sex_ratio",
        "sc_percentage": "district_sc_percentage",
        "st_percentage": "district_st_percentage",
        "worker_participation": "district_worker_participation",
    })

    census_cols = [
        "state_name", "census_district_name",
        "district_population", "district_literacy_rate",
        "district_sex_ratio", "district_sc_percentage",
        "district_st_percentage", "district_worker_participation",
    ]
    census_renamed = census_renamed[[c for c in census_cols if c in census_renamed.columns]]

    # Simple join: aggregate census to state level as fallback
    # (constituency-level district mapping to be added as a future enhancement)
    state_census = (
        census_renamed
        .groupby("state_name")
        .agg({
            "district_population": "sum",
            "district_literacy_rate": "mean",
            "district_sex_ratio": "mean",
            "district_sc_percentage": "mean",
            "district_st_percentage": "mean",
            "district_worker_participation": "mean",
        })
        .reset_index()
    )

    merged = df.merge(state_census, on="state_name", how="left")
    matched = merged["district_literacy_rate"].notna().sum()
    print(f"  [JOIN] Census match rate: {matched:,}/{len(merged):,} "
          f"({matched/len(merged)*100:.1f}%)")
    return merged


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build derived features from the joined dataset.

    Log-transforms on skewed financial/population columns improve
    model performance by reducing the effect of extreme outliers.
    """
    df = df.copy()

    # Log-transform assets (highly skewed — billionaires vs. common candidates)
    if "total_assets" in df.columns:
        df["log_total_assets"] = np.log1p(
            df["total_assets"].fillna(0).clip(lower=0)
        ).round(4)

    # Log-transform district population
    if "district_population" in df.columns:
        df["log_district_population"] = np.log1p(
            df["district_population"].fillna(0)
        ).round(4)

    # Fill affidavit nulls conservatively
    # (null criminal_cases = not declared, treat as 0 per ADR convention)
    for col in ["criminal_cases", "serious_criminal_cases"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    for col in ["has_criminal_case", "has_serious_case", "is_crorepati"]:
        if col in df.columns:
            df[col] = df[col].fillna(False)

    print(f"  [FEATURES] Built: log_total_assets, log_district_population")
    return df


def select_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order the final columns for the gold.candidate_features table."""
    feature_cols = [
        # Identifiers
        "year", "state_name", "constituency_name", "candidate_name",
        # Target
        "won",
        # Candidate electoral features
        "party", "position", "votes", "vote_share",
        "constituency_type", "electors", "turnout_percentage",
        # Candidate affidavit features
        "criminal_cases", "serious_criminal_cases",
        "has_criminal_case", "has_serious_case",
        "education", "total_assets", "log_total_assets",
        "total_liabilities", "is_crorepati",
        # District / Census features
        "district_literacy_rate", "district_sex_ratio",
        "district_sc_percentage", "district_st_percentage",
        "district_worker_participation", "log_district_population",
    ]
    available = [c for c in feature_cols if c in df.columns]
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        print(f"  [WARN] Columns not available yet: {missing}")
    return df[available]


# ============================================
# Output
# ============================================

def write_to_gold(df: pd.DataFrame):
    """
    Write the feature table to gold.candidate_features.

    NOTE: The 'gold' schema may not exist yet — this script creates it
    if missing. Add 'CREATE SCHEMA IF NOT EXISTS gold;' to schema.sql
    as the next step if you want it persisted on Docker boot.
    """
    engine = get_engine()

    # Ensure gold schema exists
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold"))

    print(f"\n  [WRITE] Writing {len(df):,} rows to gold.candidate_features...")
    df.to_sql(
        "candidate_features",
        engine,
        schema="gold",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM gold.candidate_features")
        ).scalar()
        print(f"  [OK] Total rows in gold.candidate_features: {count:,}")


def print_summary(df: pd.DataFrame):
    """Print a quick summary of the feature table."""
    print(f"\n  --- Feature Table Summary ---")
    print(f"  Shape          : {df.shape[0]:,} rows x {df.shape[1]} columns")
    print(f"  Years covered  : {sorted(df['year'].unique())}")
    print(f"  Winners (won=1): {df['won'].sum():,}")
    print(f"  Columns        : {list(df.columns)}")

    if "district_literacy_rate" in df.columns:
        print(f"\n  Census join coverage:")
        print(f"    Literacy rate  : {df['district_literacy_rate'].notna().sum():,} rows")

    if "has_criminal_case" in df.columns:
        pct = df["has_criminal_case"].mean() * 100
        print(f"\n  Affidavit insights:")
        print(f"    % with criminal case : {pct:.1f}%")
    if "is_crorepati" in df.columns:
        pct = df["is_crorepati"].mean() * 100
        print(f"    % crorepati          : {pct:.1f}%")


# ============================================
# Main
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="BEIP Phase 2: Build ML feature table from Silver layer"
    )
    parser.add_argument(
        "--year", "-y", type=int, default=None,
        help="Filter to a specific election year (default: all years)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BEIP -- Phase 2: Feature Engineering")
    print("=" * 60)

    print("\n[1/7] Loading Silver data...")
    elections = load_election_results(year=args.year)
    affidavits = load_candidate_affidavits(year=args.year)
    census = load_census_demographics()

    print("\n[2/7] Building target variable (won)...")
    elections = build_target(elections)

    print("\n[3/7] Joining affidavit data...")
    df = join_affidavits(elections, affidavits)

    print("\n[4/7] Joining census data...")
    df = join_census(df, census)

    print("\n[5/7] Engineering derived features...")
    df = engineer_features(df)

    print("\n[6/7] Selecting final feature columns...")
    df = select_feature_columns(df)

    print_summary(df)

    print("\n[7/7] Writing to gold layer...")
    write_to_gold(df)

    print("\n" + "=" * 60)
    print("[OK] Feature engineering complete!")
    print(f"     gold.candidate_features is ready for model training.")
    print("=" * 60)


if __name__ == "__main__":
    main()
