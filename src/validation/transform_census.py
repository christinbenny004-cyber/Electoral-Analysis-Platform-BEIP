"""
BEIP -- Bronze -> Silver Transform: Census Demographics

Reads from bronze.census_demographics, computes derived metrics,
standardizes state/district names, and writes to silver.census_demographics.

Transformations:
    - Standardize state and district name formatting (Title Case, strip whitespace)
    - Compute literacy_rate     = total_literate / total_population * 100
    - Compute sex_ratio         = female_population / male_population * 1000
    - Compute sc_percentage     = sc_population / total_population * 100
    - Compute st_percentage     = st_population / total_population * 100
    - Compute worker_participation = total_workers / total_population * 100
    - Drop rows with no population data
    - Preserve bronze_id for lineage tracking

Usage:
    python -m src.validation.transform_census
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Known state name variants -> canonical names
# Ensures census state names match election data
# ============================================
STATE_NAME_MAP = {
    "Andaman & Nicobar Island": "Andaman And Nicobar Islands",
    "Andaman And Nicobar Island": "Andaman And Nicobar Islands",
    "Dadra & Nagar Haveli": "Dadra And Nagar Haveli",
    "Daman & Diu": "Daman And Diu",
    "Delhi": "Delhi",
    "NCT of Delhi": "Delhi",
    "Jammu & Kashmir": "Jammu And Kashmir",
    "Odisha": "Odisha",
    "Orissa": "Odisha",
    "Uttarakhand": "Uttarakhand",
    "Uttaranchal": "Uttarakhand",
    "Pondicherry": "Puducherry",
}


def load_bronze_data() -> pd.DataFrame:
    """Load all data from bronze.census_demographics."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT id, state_code, district_code, state_name, district_name, "
            "total_population, male_population, female_population, "
            "total_literate, sc_population, st_population, total_workers "
            "FROM bronze.census_demographics",
            conn
        )
    print(f"  [LOAD] Read {len(df):,} rows from bronze.census_demographics")
    return df


def clean_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize state and district name formatting."""
    df = df.copy()

    for col in ["state_name", "district_name"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.replace("_", " ", regex=False)
                .str.replace(r"\s+", " ", regex=True)  # collapse multiple spaces
                .str.title()
            )

    return df


def standardize_state_names(df: pd.DataFrame) -> pd.DataFrame:
    """Map Census state name variants to canonical names used in election data."""
    df = df.copy()
    if "state_name" in df.columns:
        df["state_name"] = df["state_name"].replace(STATE_NAME_MAP)
    return df


def drop_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with missing or zero population — cannot compute derived metrics."""
    before = len(df)
    df = df.dropna(subset=["total_population"])
    df = df[df["total_population"] > 0]
    dropped = before - len(df)
    if dropped > 0:
        print(f"  [CLEAN] Dropped {dropped:,} rows with null/zero population")
    return df


def compute_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the analytical columns expected by silver.census_demographics.

    Derived columns (not in Bronze):
        - literacy_rate:        total_literate / total_population * 100
        - sex_ratio:            female_population / male_population * 1000
        - sc_percentage:        sc_population / total_population * 100
        - st_percentage:        st_population / total_population * 100
        - worker_participation: total_workers / total_population * 100
    """
    df = df.copy()

    # Ensure all numeric before dividing
    numeric_cols = [
        "total_population", "male_population", "female_population",
        "total_literate", "sc_population", "st_population", "total_workers"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Literacy rate
    df["literacy_rate"] = (
        df["total_literate"] / df["total_population"] * 100
    ).round(2)

    # Sex ratio (females per 1000 males)
    df["sex_ratio"] = (
        df["female_population"] / df["male_population"] * 1000
    ).round(2)

    # SC percentage
    df["sc_percentage"] = (
        df["sc_population"] / df["total_population"] * 100
    ).round(2)

    # ST percentage
    df["st_percentage"] = (
        df["st_population"] / df["total_population"] * 100
    ).round(2)

    # Worker participation rate
    df["worker_participation"] = (
        df["total_workers"] / df["total_population"] * 100
    ).round(2)

    print(
        f"  [METRICS] Computed: literacy_rate, sex_ratio, sc_percentage, "
        f"st_percentage, worker_participation"
    )
    return df


def select_silver_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order columns matching silver.census_demographics schema."""
    silver_cols = [
        "state_name",
        "district_name",
        "total_population",
        "male_population",
        "female_population",
        "literacy_rate",
        "sex_ratio",
        "sc_percentage",
        "st_percentage",
        "worker_participation",
        "id",  # will be renamed to bronze_id
    ]
    available = [c for c in silver_cols if c in df.columns]
    df = df[available].rename(columns={"id": "bronze_id"})
    return df


def write_to_silver(df: pd.DataFrame):
    """Write cleaned data to silver.census_demographics."""
    engine = get_engine()

    print(f"\n  [WRITE] Writing {len(df):,} rows to silver.census_demographics...")
    df.to_sql(
        "census_demographics",
        engine,
        schema="silver",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=500,
    )

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM silver.census_demographics")
        ).scalar()
        print(f"  [OK] Total rows in silver.census_demographics: {count:,}")


def print_summary():
    """Show a sample of the Silver data to verify correctness."""
    engine = get_engine()
    with engine.connect() as conn:
        bronze_count = conn.execute(
            text("SELECT COUNT(*) FROM bronze.census_demographics")
        ).scalar()
        silver_count = conn.execute(
            text("SELECT COUNT(*) FROM silver.census_demographics")
        ).scalar()

        result = conn.execute(text("""
            SELECT state_name, district_name, total_population,
                   literacy_rate, sex_ratio
            FROM silver.census_demographics
            ORDER BY total_population DESC
            LIMIT 10
        """))

        print(f"\n  --- Bronze vs Silver ---")
        print(f"  Bronze rows: {bronze_count:,}")
        print(f"  Silver rows: {silver_count:,}")

        print(f"\n  Top 10 districts by population (sample):")
        print(f"  {'State':<20} {'District':<20} {'Population':>12} {'Literacy%':>10} {'SexRatio':>9}")
        print(f"  {'-'*73}")
        for row in result:
            print(
                f"  {str(row[0]):<20} {str(row[1]):<20} "
                f"{row[2]:>12,} {str(row[3]):>10} {str(row[4]):>9}"
            )


def main():
    print("=" * 60)
    print("BEIP -- Bronze -> Silver: Census Demographics")
    print("=" * 60)

    print("\n[1/6] Loading bronze data...")
    df = load_bronze_data()

    print("\n[2/6] Cleaning names...")
    df = clean_names(df)

    print("\n[3/6] Standardizing state names...")
    df = standardize_state_names(df)

    print("\n[4/6] Dropping invalid rows...")
    df = drop_invalid_rows(df)

    print("\n[5/6] Computing derived metrics...")
    df = compute_derived_metrics(df)
    df = select_silver_columns(df)
    print(f"  [COLS] Silver columns: {list(df.columns)}")

    print("\n[6/6] Writing to silver layer...")
    write_to_silver(df)

    print_summary()

    print("\n" + "=" * 60)
    print("[OK] Census Silver transform complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
