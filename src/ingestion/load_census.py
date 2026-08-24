"""
BEIP -- Census 2011 PCA (Primary Census Abstract) Ingestion

Loads district-level Census 2011 demographic data into
bronze.census_demographics in Postgres.

Usage:
    1. Download PCA data from https://censusindia.gov.in
       - Go to: Census Tables -> Primary Census Abstract
       - Download district-level data (Excel format)
       - Save to: data/raw/census_2011_pca.xlsx (or .xls / .csv)

    2. Run this script:
       python -m src.ingestion.load_census

    3. Or with a custom file path:
       python -m src.ingestion.load_census --file data/raw/your_file.xlsx
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Known Census PCA column patterns
# ============================================
# Census Excel files have notoriously messy headers (multi-row, merged cells).
# This mapping handles common variations found in PCA district tables.
COLUMN_MAP = {
    # State/District identifiers
    "State Code": "state_code",
    "State code": "state_code",
    "state_code": "state_code",
    "District Code": "district_code",
    "District code": "district_code",
    "district_code": "district_code",
    "State": "state_name",
    "State Name": "state_name",
    "State/UT": "state_name",
    "state_name": "state_name",
    "District": "district_name",
    "District Name": "district_name",
    "district_name": "district_name",
    "Name": "district_name",
    # Population
    "Total Population": "total_population",
    "Total_Population": "total_population",
    "TOT_P": "total_population",
    "Population": "total_population",
    "Total population Person": "total_population",
    "TOT_M": "male_population",
    "Male Population": "male_population",
    "Male_Population": "male_population",
    "Total population Male": "male_population",
    "TOT_F": "female_population",
    "Female Population": "female_population",
    "Female_Population": "female_population",
    "Total population Female": "female_population",
    # Literacy
    "Literate Population": "total_literate",
    "Literate_Population": "total_literate",
    "P_LIT": "total_literate",
    "Literate Person": "total_literate",
    "M_LIT": "male_literate",
    "Literate Male": "male_literate",
    "F_LIT": "female_literate",
    "Literate Female": "female_literate",
    # SC/ST
    "SC Population": "sc_population",
    "SC_Population": "sc_population",
    "P_SC": "sc_population",
    "ST Population": "st_population",
    "ST_Population": "st_population",
    "P_ST": "st_population",
    # Workers
    "Total Workers": "total_workers",
    "Total_Workers": "total_workers",
    "TOT_WORK_P": "total_workers",
    "Main Workers": "total_workers",
}

EXPECTED_COLUMNS = [
    "state_code", "district_code", "state_name", "district_name",
    "total_population", "male_population", "female_population",
    "total_literate", "male_literate", "female_literate",
    "sc_population", "st_population", "total_workers",
    "source_file",
]


def find_census_file():
    """Look for Census data files in data/raw/."""
    raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
    
    patterns = ["*census*", "*pca*", "*PCA*", "*Census*"]
    extensions = [".xlsx", ".xls", ".csv"]
    
    for pattern in patterns:
        for ext in extensions:
            files = list(raw_dir.glob(f"{pattern}{ext}"))
            if files:
                return files[0]
    return None


def load_file(file_path: str) -> pd.DataFrame:
    """
    Read Census data file (Excel or CSV) with messy header handling.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix in [".xlsx", ".xls"]:
        # Census Excel files often have:
        # - Multiple header rows (try rows 0-5)
        # - Merged cells
        # - Summary rows at top
        df = _read_excel_with_header_detection(path)
    else:
        # CSV
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(path, encoding=encoding, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not read {path} with any known encoding")

    print(f"  [FILE] Read {len(df):,} rows x {len(df.columns)} columns from {path.name}")
    return df


def _read_excel_with_header_detection(path: Path) -> pd.DataFrame:
    """
    Try different header rows to find the actual data header in messy Excel files.
    Census files often have title rows, merged cells, etc. before the real header.
    """
    best_df = None
    best_score = 0

    for header_row in range(0, 8):
        try:
            df = pd.read_excel(path, header=header_row)
            
            # Score: how many of our known column names appear?
            score = sum(1 for col in df.columns if col in COLUMN_MAP)
            
            if score > best_score:
                best_score = score
                best_df = df
                
            # If we found a lot of matches, stop searching
            if score >= 5:
                print(f"  [INFO] Found data header at row {header_row} ({score} known columns)")
                return df
        except Exception:
            continue

    if best_df is not None:
        print(f"  [INFO] Best header match: {best_score} known columns")
        return best_df

    # Last resort: just read with default header
    return pd.read_excel(path)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to our schema, filtering to district-level data only."""
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Rename using mapping
    renamed = {}
    for col in df.columns:
        if col in COLUMN_MAP:
            renamed[col] = COLUMN_MAP[col]

    df = df.rename(columns=renamed)
    
    # Drop duplicate columns that might result from multiple headers mapping to the same name
    df = df.loc[:, ~df.columns.duplicated()]

    # Keep only columns we need
    valid_cols = [c for c in EXPECTED_COLUMNS if c in df.columns and c != "source_file"]
    if len(valid_cols) < 3:
        print(f"  [WARN] Only found {len(valid_cols)} expected columns: {valid_cols}")
        print(f"  [WARN] Available columns: {list(df.columns)[:20]}")

    return df[valid_cols]


def clean_census_data(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning specific to Census data."""
    df = df.copy()

    # Remove rows where district_name is null or looks like a header/total row
    if "district_name" in df.columns:
        df = df.dropna(subset=["district_name"])
        # Remove aggregate rows (state totals, India total)
        skip_patterns = ["total", "india", "state", "all district"]
        mask = df["district_name"].astype(str).str.lower().str.strip()
        for pattern in skip_patterns:
            df = df[~mask.str.startswith(pattern)]

    # Ensure numeric columns are numeric
    numeric_cols = [
        "total_population", "male_population", "female_population",
        "total_literate", "male_literate", "female_literate",
        "sc_population", "st_population", "total_workers"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_to_postgres(df: pd.DataFrame, source_file: str):
    """Write DataFrame to bronze.census_demographics."""
    engine = get_engine()

    df = df.copy()
    df["source_file"] = source_file

    # Check existing data
    with engine.connect() as conn:
        try:
            existing = conn.execute(text("SELECT COUNT(*) FROM bronze.census_demographics")).scalar()
        except Exception:
            existing = 0

    mode = "replace" if existing == 0 else "append"
    if existing > 0:
        print(f"  [INFO] Table already has {existing:,} rows. Appending...")

    print(f"\n  [LOAD] Loading {len(df):,} rows into bronze.census_demographics...")
    df.to_sql(
        "census_demographics",
        engine,
        schema="bronze",
        if_exists=mode,
        index=False,
        method="multi",
        chunksize=500,
    )
    
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM bronze.census_demographics")).scalar()
        print(f"  [OK] Total rows in bronze.census_demographics: {count:,}")


def main():
    parser = argparse.ArgumentParser(
        description="Load Census 2011 PCA data into bronze.census_demographics"
    )
    parser.add_argument("--file", "-f", type=str, help="Path to Census data file")
    args = parser.parse_args()

    print("=" * 60)
    print("BEIP -- Census 2011 Ingestion")
    print("=" * 60)

    if args.file:
        data_path = args.file
    else:
        data_path = find_census_file()
        if data_path is None:
            print(
                "\n[ERROR] No Census data file found in data/raw/\n"
                "\nTo get the data:\n"
                "  1. Go to https://censusindia.gov.in\n"
                "  2. Navigate to: Census Data -> Primary Census Abstract\n"
                "  3. Download district-level PCA tables (Excel format)\n"
                "  4. Save to: data/raw/census_2011_pca.xlsx\n"
                "  5. Run this script again\n"
                "\nAlternatively, search for 'Census 2011 PCA district level' on data.gov.in"
            )
            sys.exit(1)

    print(f"\n  [PATH] Source file: {data_path}")

    print("\n[1/4] Reading file...")
    df = load_file(str(data_path))

    print("\n[2/4] Normalizing columns...")
    df = normalize_columns(df)
    print(f"  [COLS] Columns: {list(df.columns)}")

    print("\n[3/4] Cleaning data...")
    before = len(df)
    df = clean_census_data(df)
    print(f"  [CLEAN] {before:,} -> {len(df):,} rows (removed {before - len(df):,} header/total rows)")

    print("\n[4/4] Loading to Postgres...")
    load_to_postgres(df, source_file=Path(str(data_path)).name)

    print("\n" + "=" * 60)
    print("[OK] Census ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
