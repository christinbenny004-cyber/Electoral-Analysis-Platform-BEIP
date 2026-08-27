"""
BEIP -- Bronze -> Silver Transform: Candidate Affidavits (MyNeta / ADR)

Reads from bronze.candidate_affidavits, cleans and standardizes the data,
then writes to silver.candidate_affidavits.

Transformations:
    - Standardize candidate, party, state, and constituency name formatting
    - Normalize criminal_cases: treat null/non-numeric values as 0
    - Normalize serious_criminal_cases: same treatment as criminal_cases
    - Classify candidates: has_criminal_case, is_crorepati (assets > 1 Crore)
    - Classify education into broad buckets (graduate, post-graduate, etc.)
    - Drop exact duplicate rows on natural key
    - Preserve bronze_id for lineage tracking

Usage:
    python -m src.validation.transform_myneta
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine

# ============================================
# Education level normalization
# Maps raw strings from affidavits to broad buckets
# ============================================
EDUCATION_MAP = {
    # Post Graduate
    "post graduate": "Post Graduate",
    "post-graduate": "Post Graduate",
    "postgraduate": "Post Graduate",
    "pg": "Post Graduate",
    "m.a": "Post Graduate",
    "m.sc": "Post Graduate",
    "m.com": "Post Graduate",
    "mba": "Post Graduate",
    "m.b.a": "Post Graduate",
    "m.tech": "Post Graduate",
    "phd": "Doctorate",
    "ph.d": "Doctorate",
    "doctorate": "Doctorate",
    # Graduate
    "graduate": "Graduate",
    "b.a": "Graduate",
    "b.sc": "Graduate",
    "b.com": "Graduate",
    "b.tech": "Graduate",
    "b.e": "Graduate",
    "llb": "Graduate",
    "l.l.b": "Graduate",
    "b.ed": "Graduate",
    # 12th Pass
    "12th pass": "12th Pass",
    "intermediate": "12th Pass",
    "higher secondary": "12th Pass",
    "hsc": "12th Pass",
    "10+2": "12th Pass",
    # 10th Pass
    "10th pass": "10th Pass",
    "matriculate": "10th Pass",
    "sslc": "10th Pass",
    "secondary": "10th Pass",
    "high school": "10th Pass",
    # Below 10th
    "8th pass": "Below 10th",
    "5th pass": "Below 10th",
    "illiterate": "Illiterate",
    "not literate": "Illiterate",
    # Others
    "others": "Others",
    "other": "Others",
}

# Reuse the same party name map as election results for consistency
PARTY_NAME_MAP = {
    "B.J.P": "BJP", "B.J.P.": "BJP",
    "Bharatiya Janata Party": "BJP", "BHARATIYA JANATA PARTY": "BJP",
    "I.N.C": "INC", "I.N.C.": "INC",
    "Indian National Congress": "INC", "INDIAN NATIONAL CONGRESS": "INC",
    "Aam Aadmi Party": "AAP", "AAM AADMI PARTY": "AAP",
    "B.S.P": "BSP", "B.S.P.": "BSP", "Bahujan Samaj Party": "BSP",
    "S.P": "SP", "S.P.": "SP", "Samajwadi Party": "SP",
    "CPI(M)": "CPIM", "CPM": "CPIM", "C.P.I.(M)": "CPIM",
    "Communist Party of India (Marxist)": "CPIM",
    "C.P.I.": "CPI", "Communist Party of India": "CPI",
    "N.C.P": "NCP", "N.C.P.": "NCP", "Nationalist Congress Party": "NCP",
    "T.M.C": "TMC", "T.M.C.": "TMC", "AITC": "TMC",
    "All India Trinamool Congress": "TMC",
    "IND": "IND", "Independent": "IND", "INDEPENDENT": "IND", "Ind.": "IND",
    "NOTA": "NOTA", "None of the Above": "NOTA",
}

CRORE = 10_000_000  # 1 Crore = 10 million INR


def load_bronze_data() -> pd.DataFrame:
    """Load all data from bronze.candidate_affidavits.

    Reads only the columns that are guaranteed to exist in the bronze table,
    which may vary depending on the ingestion method (file vs. scraper).
    """
    engine = get_engine()
    # Discover actual columns in the bronze table
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'bronze' AND table_name = 'candidate_affidavits'"
        ))
        available_cols = {row[0] for row in result}

    # Map to expected column names and select what exists
    # Some ingestion runs may not have state_name or serious_criminal_cases
    desired_cols = [
        "year", "state_name", "constituency_name", "candidate_name",
        "party", "criminal_cases", "serious_criminal_cases",
        "education", "total_assets", "total_liabilities",
    ]
    select_cols = [c for c in desired_cols if c in available_cols]
    missing = set(desired_cols) - available_cols
    if missing:
        print(f"  [WARN] Bronze table missing columns (will be set to null): {missing}")

    with engine.connect() as conn:
        df = pd.read_sql(
            f"SELECT {', '.join(select_cols)} FROM bronze.candidate_affidavits",
            conn
        )

    # Add missing columns as nulls so downstream steps don't fail
    for col in desired_cols:
        if col not in df.columns:
            df[col] = None

    print(f"  [LOAD] Read {len(df):,} rows from bronze.candidate_affidavits")
    return df


def clean_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize name columns: strip, title case, remove underscores.

    Also handles scraping artifacts from MyNeta:
      - '&Nbsp' / '&nbsp' HTML entities left in candidate names
      - 'winner' / 'lost' suffixes appended to candidate names
      - 'And' vs '&' mismatch in constituency names (election results use '&')
    """
    df = df.copy()

    # Clean candidate_name: remove HTML artifacts and status tags from scraping
    if "candidate_name" in df.columns:
        df["candidate_name"] = (
            df["candidate_name"]
            .astype(str)
            .str.replace(r"(?i)&nbsp;?", " ", regex=True)   # HTML &nbsp entities
            .str.replace(r"(?i)\s*(winner|lost|deposit lost)\s*$", "", regex=True)  # Status suffixes
            .str.replace("_", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True)            # Collapse whitespace
            .str.strip()
            .str.title()
        )

    # Clean constituency_name: use '&' instead of 'And' to match election results
    if "constituency_name" in df.columns:
        df["constituency_name"] = (
            df["constituency_name"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.title()
        )
        # Replace ' And ' with ' & ' to match election results format
        df["constituency_name"] = df["constituency_name"].str.replace(" And ", " & ", regex=False)

    # Clean state_name
    if "state_name" in df.columns:
        df["state_name"] = (
            df["state_name"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.title()
        )

    return df


def standardize_parties(df: pd.DataFrame) -> pd.DataFrame:
    """Map party name variants to canonical names (same map as election results)."""
    df = df.copy()
    if "party" in df.columns:
        df["party"] = df["party"].astype(str).str.strip()
        df["party"] = df["party"].replace(PARTY_NAME_MAP)
    return df


def normalize_criminal_cases(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert criminal case columns to integers.
    Null/non-numeric values from the affidavit source are treated as 0
    (meaning no declared cases, not missing data — per ADR convention).
    """
    df = df.copy()
    for col in ["criminal_cases", "serious_criminal_cases"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def normalize_assets(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure total_assets and total_liabilities are integers (in INR)."""
    df = df.copy()
    for col in ["total_assets", "total_liabilities"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def normalize_education(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw education strings to broad, comparable buckets."""
    df = df.copy()
    if "education" in df.columns:
        df["education"] = (
            df["education"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lambda x: next(
                (v for k, v in EDUCATION_MAP.items() if k in x),
                "Others"
            ))
        )
    return df


def add_derived_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add boolean analytical flags useful for Phase 2 ML features:
        - has_criminal_case:    True if candidate declared >= 1 criminal case
        - has_serious_case:     True if candidate declared >= 1 serious case
        - is_crorepati:         True if total_assets > 1 Crore INR
    """
    df = df.copy()
    if "criminal_cases" in df.columns:
        df["has_criminal_case"] = df["criminal_cases"] > 0
    if "serious_criminal_cases" in df.columns:
        df["has_serious_case"] = df["serious_criminal_cases"] > 0
    if "total_assets" in df.columns:
        df["is_crorepati"] = df["total_assets"] > CRORE

    print(
        f"  [FLAGS] Added: has_criminal_case, has_serious_case, is_crorepati"
    )
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate rows on the natural key."""
    before = len(df)
    key_cols = ["year", "state_name", "constituency_name", "candidate_name"]
    available = [c for c in key_cols if c in df.columns]
    df = df.drop_duplicates(subset=available, keep="first")
    dropped = before - len(df)
    if dropped > 0:
        print(f"  [CLEAN] Dropped {dropped:,} duplicate rows")
    return df


def select_silver_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order columns matching silver.candidate_affidavits schema."""
    silver_cols = [
        "year",
        "state_name",
        "constituency_name",
        "candidate_name",
        "party",
        "criminal_cases",
        "serious_criminal_cases",
        "has_criminal_case",
        "has_serious_case",
        "education",
        "total_assets",
        "total_liabilities",
        "is_crorepati",
    ]
    available = [c for c in silver_cols if c in df.columns]
    return df[available]


def write_to_silver(df: pd.DataFrame):
    """Write cleaned data to silver.candidate_affidavits."""
    engine = get_engine()

    print(f"\n  [WRITE] Writing {len(df):,} rows to silver.candidate_affidavits...")
    df.to_sql(
        "candidate_affidavits",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500,
    )

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM silver.candidate_affidavits")
        ).scalar()
        print(f"  [OK] Total rows in silver.candidate_affidavits: {count:,}")


def print_summary():
    """Show a quick analytical summary of the Silver data."""
    engine = get_engine()
    with engine.connect() as conn:
        bronze_count = conn.execute(
            text("SELECT COUNT(*) FROM bronze.candidate_affidavits")
        ).scalar()
        silver_count = conn.execute(
            text("SELECT COUNT(*) FROM silver.candidate_affidavits")
        ).scalar()

        criminal_stats = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE has_criminal_case) AS with_criminal_cases,
                COUNT(*) FILTER (WHERE is_crorepati)      AS crorepatis,
                ROUND(AVG(total_assets::NUMERIC / 1e7), 2) AS avg_assets_cr
            FROM silver.candidate_affidavits
            WHERE year = (SELECT MAX(year) FROM silver.candidate_affidavits)
        """)).fetchone()

        print(f"\n  --- Bronze vs Silver ---")
        print(f"  Bronze rows: {bronze_count:,}")
        print(f"  Silver rows: {silver_count:,}")
        if criminal_stats:
            print(f"\n  Most recent election snapshot:")
            print(f"    Candidates with criminal cases : {criminal_stats[0]:,}")
            print(f"    Crorepati candidates           : {criminal_stats[1]:,}")
            print(f"    Average assets (Crore INR)     : {criminal_stats[2]}")


def main():
    print("=" * 60)
    print("BEIP -- Bronze -> Silver: Candidate Affidavits (MyNeta)")
    print("=" * 60)

    print("\n[1/8] Loading bronze data...")
    df = load_bronze_data()

    print("\n[2/8] Cleaning names...")
    df = clean_names(df)

    print("\n[3/8] Standardizing party names...")
    df = standardize_parties(df)

    print("\n[4/8] Normalizing criminal cases...")
    df = normalize_criminal_cases(df)

    print("\n[5/8] Normalizing asset values...")
    df = normalize_assets(df)

    print("\n[6/8] Normalizing education levels...")
    df = normalize_education(df)

    print("\n[7/8] Adding derived flags and removing duplicates...")
    df = add_derived_flags(df)
    df = drop_duplicates(df)
    df = select_silver_columns(df)
    print(f"  [COLS] Silver columns: {list(df.columns)}")

    print("\n[8/8] Writing to silver layer...")
    write_to_silver(df)

    print_summary()

    print("\n" + "=" * 60)
    print("[OK] MyNeta Silver transform complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
