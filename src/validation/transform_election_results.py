"""
BEIP -- Bronze -> Silver Transform: Election Results

Reads from bronze.election_results, cleans and standardizes the data,
then writes to silver.election_results.

Transformations:
    - Standardize party name spellings (e.g., 'BJP' vs 'B.J.P')
    - Clean state/constituency names (remove underscores, fix encoding)
    - Convert deposit_lost from Yes/No to boolean
    - Drop exact duplicate rows
    - Ensure proper data types

Usage:
    python -m src.validation.transform_election_results
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Party name standardization
# ============================================
# Maps common variations/abbreviations to canonical party names.
# This is a subset — expand as you encounter more variations.
PARTY_NAME_MAP = {
    # BJP variants
    "B.J.P": "BJP",
    "B.J.P.": "BJP",
    "Bharatiya Janata Party": "BJP",
    "BHARATIYA JANATA PARTY": "BJP",
    # INC variants
    "I.N.C": "INC",
    "I.N.C.": "INC",
    "Indian National Congress": "INC",
    "INDIAN NATIONAL CONGRESS": "INC",
    # AAP
    "Aam Aadmi Party": "AAP",
    "AAM AADMI PARTY": "AAP",
    # BSP
    "B.S.P": "BSP",
    "B.S.P.": "BSP",
    "Bahujan Samaj Party": "BSP",
    # SP
    "S.P": "SP",
    "S.P.": "SP",
    "Samajwadi Party": "SP",
    # CPI(M)
    "CPI(M)": "CPIM",
    "CPM": "CPIM",
    "C.P.I.(M)": "CPIM",
    "Communist Party of India (Marxist)": "CPIM",
    # CPI
    "C.P.I.": "CPI",
    "Communist Party of India": "CPI",
    # NCP
    "N.C.P": "NCP",
    "N.C.P.": "NCP",
    "Nationalist Congress Party": "NCP",
    # TMC
    "T.M.C": "TMC",
    "T.M.C.": "TMC",
    "AITC": "TMC",
    "All India Trinamool Congress": "TMC",
    # Independent
    "IND": "IND",
    "Independent": "IND",
    "INDEPENDENT": "IND",
    "Ind.": "IND",
    # NOTA
    "NOTA": "NOTA",
    "None of the Above": "NOTA",
}


def load_bronze_data() -> pd.DataFrame:
    """Load all data from bronze.election_results."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM bronze.election_results", conn)
    print(f"  [LOAD] Read {len(df):,} rows from bronze.election_results")
    return df


def clean_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean state and constituency name formatting."""
    df = df.copy()

    # Replace underscores with spaces in names
    if "state_name" in df.columns:
        df["state_name"] = (
            df["state_name"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.strip()
            .str.title()
        )

    if "constituency_name" in df.columns:
        df["constituency_name"] = (
            df["constituency_name"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.strip()
            .str.title()
        )

    if "candidate_name" in df.columns:
        df["candidate_name"] = (
            df["candidate_name"]
            .astype(str)
            .str.strip()
            .str.title()
        )

    return df


def standardize_parties(df: pd.DataFrame) -> pd.DataFrame:
    """Map party name variants to canonical names."""
    df = df.copy()
    if "party" in df.columns:
        df["party"] = df["party"].astype(str).str.strip()
        df["party"] = df["party"].replace(PARTY_NAME_MAP)
    return df


def convert_deposit_lost(df: pd.DataFrame) -> pd.DataFrame:
    """Convert deposit_lost from Yes/No text to boolean."""
    df = df.copy()
    if "deposit_lost" in df.columns:
        mapping = {
            "yes": True, "Yes": True, "YES": True, "1": True, "True": True,
            "no": False, "No": False, "NO": False, "0": False, "False": False,
        }
        df["deposit_lost"] = df["deposit_lost"].astype(str).map(mapping)
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop exact duplicate rows."""
    before = len(df)
    key_cols = ["year", "state_name", "constituency_name", "candidate_name"]
    available = [c for c in key_cols if c in df.columns]
    df = df.drop_duplicates(subset=available, keep="first")
    dropped = before - len(df)
    if dropped > 0:
        print(f"  [CLEAN] Dropped {dropped:,} duplicate rows")
    return df


def ensure_types(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure proper data types for silver layer."""
    df = df.copy()

    int_cols = ["year", "position", "votes", "electors", "constituency_no", "assembly_no"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    float_cols = ["vote_share", "turnout_percentage", "margin_percentage", "enop"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def select_silver_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order columns for the silver layer."""
    # Core columns for silver — keep the most analytically useful fields
    silver_cols = [
        "year", "state_name", "constituency_name", "constituency_no",
        "constituency_type", "candidate_name", "sex", "party",
        "votes", "vote_share", "position", "deposit_lost",
        "electors", "turnout_percentage", "valid_votes",
        "n_cand", "margin", "margin_percentage",
        "candidate_type", "incumbent", "recontest",
        "myneta_education", "election_type",
    ]
    available = [c for c in silver_cols if c in df.columns]
    return df[available]


def write_to_silver(df: pd.DataFrame):
    """Write cleaned data to silver.election_results."""
    engine = get_engine()

    # Drop and recreate silver table
    print(f"\n  [WRITE] Writing {len(df):,} rows to silver.election_results...")
    df.to_sql(
        "election_results",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM silver.election_results")).scalar()
        print(f"  [OK] Total rows in silver.election_results: {count:,}")


def print_comparison():
    """Show before/after comparison of bronze vs silver."""
    engine = get_engine()
    with engine.connect() as conn:
        bronze_count = conn.execute(text("SELECT COUNT(*) FROM bronze.election_results")).scalar()
        silver_count = conn.execute(text("SELECT COUNT(*) FROM silver.election_results")).scalar()

        # Sample party names from silver
        result = conn.execute(text("""
            SELECT party, COUNT(*) as candidates
            FROM silver.election_results
            WHERE year = 2019
            GROUP BY party
            ORDER BY candidates DESC
            LIMIT 10
        """))

        print(f"\n  --- Bronze vs Silver ---")
        print(f"  Bronze rows: {bronze_count:,}")
        print(f"  Silver rows: {silver_count:,}")
        print(f"  Dropped:     {bronze_count - silver_count:,}")

        print(f"\n  Top 10 parties (2019 LS, standardized names):")
        for row in result:
            print(f"    {row[0]:.<30} {row[1]:,} candidates")


def main():
    print("=" * 60)
    print("BEIP -- Bronze -> Silver: Election Results")
    print("=" * 60)

    print("\n[1/6] Loading bronze data...")
    df = load_bronze_data()

    print("\n[2/6] Cleaning names...")
    df = clean_names(df)

    print("\n[3/6] Standardizing party names...")
    df = standardize_parties(df)

    print("\n[4/6] Converting deposit_lost to boolean...")
    df = convert_deposit_lost(df)

    print("\n[5/6] Removing duplicates and ensuring types...")
    df = drop_duplicates(df)
    df = ensure_types(df)
    df = select_silver_columns(df)
    print(f"  [COLS] Silver columns: {list(df.columns)}")

    print("\n[6/6] Writing to silver layer...")
    write_to_silver(df)

    print_comparison()

    print("\n" + "=" * 60)
    print("[OK] Silver transform complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
