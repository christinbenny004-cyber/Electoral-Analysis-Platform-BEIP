"""
BEIP -- Lok Dhaba Election Results Ingestion

Loads election results CSV from Lok Dhaba (TCPD, Ashoka University)
into the bronze.election_results table in Postgres.

Usage:
    1. Download the CSV from https://lokdhaba.ashoka.edu.in
       - Select: Lok Sabha -> All Years -> All States -> Download
       - Save to: data/raw/All_States_GE.csv

    2. Run this script:
       python -m src.ingestion.load_lok_dhaba

    3. Or with a custom file path:
       python -m src.ingestion.load_lok_dhaba --file data/raw/your_file.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Column mapping: Lok Dhaba CSV -> Bronze table
# ============================================
# Maps the actual Lok Dhaba CSV column names to our cleaned snake_case names.
# Bronze layer = keep everything, just normalize naming.
COLUMN_MAP = {
    "State_Name": "state_name",
    "Assembly_No": "assembly_no",
    "Constituency_No": "constituency_no",
    "Year": "year",
    "month": "month",
    "Poll_No": "poll_no",
    "DelimID": "delim_id",
    "Position": "position",
    "Candidate": "candidate_name",
    "Sex": "sex",
    "Party": "party",
    "Votes": "votes",
    "Candidate_Type": "candidate_type",
    "Valid_Votes": "valid_votes",
    "Electors": "electors",
    "Constituency_Name": "constituency_name",
    "Constituency_Type": "constituency_type",
    "Sub_Region": "sub_region",
    "N_Cand": "n_cand",
    "Turnout_Percentage": "turnout_percentage",
    "Vote_Share_Percentage": "vote_share",
    "Deposit_Lost": "deposit_lost",
    "Margin": "margin",
    "Margin_Percentage": "margin_percentage",
    "ENOP": "enop",
    "pid": "pid",
    "Party_Type_TCPD": "party_type_tcpd",
    "Party_ID": "party_id",
    "last_poll": "last_poll",
    "Contested": "contested",
    "Last_Party": "last_party",
    "Last_Party_ID": "last_party_id",
    "Last_Constituency_Name": "last_constituency_name",
    "Same_Constituency": "same_constituency",
    "Same_Party": "same_party",
    "No_Terms": "no_terms",
    "Turncoat": "turncoat",
    "Incumbent": "incumbent",
    "Recontest": "recontest",
    "MyNeta_education": "myneta_education",
    "TCPD_Prof_Main": "tcpd_prof_main",
    "TCPD_Prof_Main_Desc": "tcpd_prof_main_desc",
    "TCPD_Prof_Second": "tcpd_prof_second",
    "TCPD_Prof_Second_Desc": "tcpd_prof_second_desc",
    "Election_Type": "election_type",
}


def find_csv_file():
    """
    Look for a Lok Dhaba CSV in data/raw/.
    Returns the first matching CSV file found, or None.
    """
    raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

    # Try specific patterns first
    patterns = ["*All_States*GE*", "*lok*dhaba*", "*lok*sabha*"]
    for pattern in patterns:
        files = list(raw_dir.glob(f"{pattern}.csv"))
        if files:
            return files[0]

    # Fall back to any CSV
    csv_files = list(raw_dir.glob("*.csv"))
    return csv_files[0] if csv_files else None


def load_csv(file_path: str) -> pd.DataFrame:
    """
    Read the Lok Dhaba CSV with encoding fallback.

    Args:
        file_path: Path to the CSV file.

    Returns:
        DataFrame with raw CSV data.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    # Try UTF-8 first, then fall back to latin-1 (handles most Indian text encoding)
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
            print(f"  [FILE] Read {len(df):,} rows x {len(df.columns)} columns from {path.name}")
            print(f"         Encoding: {encoding}")
            return df
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not read {path} with any known encoding")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename CSV columns to match our bronze schema using the column map.
    Unknown columns are kept but lowercased with underscores.
    """
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Rename using our mapping
    renamed = {}
    unmapped = []
    for col in df.columns:
        if col in COLUMN_MAP:
            renamed[col] = COLUMN_MAP[col]
        else:
            # Keep unknown columns but normalize their names
            clean_name = col.lower().replace(" ", "_")
            renamed[col] = clean_name
            unmapped.append(f"{col} -> {clean_name}")

    if unmapped:
        print(f"  [WARN] Unmapped columns (kept with normalized names): {unmapped}")

    df = df.rename(columns=renamed)
    return df


def load_to_postgres(df: pd.DataFrame, source_file: str):
    """
    Write DataFrame to bronze.election_results in Postgres.

    First load uses 'replace' to create the table with all columns.
    Subsequent loads use 'append'.
    """
    engine = get_engine()

    # Add metadata
    df = df.copy()
    df["source_file"] = source_file

    # Coerce numeric columns
    numeric_cols = ["year", "assembly_no", "constituency_no", "poll_no",
                    "position", "votes", "valid_votes", "electors",
                    "n_cand", "margin", "no_terms", "party_id",
                    "last_party_id", "pid"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    float_cols = ["turnout_percentage", "vote_share", "margin_percentage", "enop"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Check if table already has data
    with engine.connect() as conn:
        try:
            existing = conn.execute(text("SELECT COUNT(*) FROM bronze.election_results")).scalar()
        except Exception:
            existing = 0

    if existing > 0:
        print(f"  [INFO] Table already has {existing:,} rows. Appending new data...")
        mode = "append"
    else:
        print(f"  [INFO] Table is empty. Creating fresh load...")
        mode = "replace"

    # Load to Postgres
    print(f"\n  [LOAD] Loading {len(df):,} rows into bronze.election_results...")
    try:
        df.to_sql(
            "election_results",
            engine,
            schema="bronze",
            if_exists=mode,
            index=False,
            method="multi",
            chunksize=1000,  # batch in chunks for large datasets
        )
        print(f"  [OK] Successfully loaded {len(df):,} rows")
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"  [WARN] Duplicate key conflict. Loading in chunks, skipping duplicates...")
            _load_chunked(df, engine)
        else:
            raise

    # Verify
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM bronze.election_results")).scalar()
        print(f"\n  [COUNT] Total rows in bronze.election_results: {count:,}")

    # Show a quick summary
    _print_summary(engine)


def _load_chunked(df: pd.DataFrame, engine):
    """Fallback: load in smaller chunks, skipping failures."""
    chunk_size = 500
    loaded = 0
    skipped = 0
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        try:
            chunk.to_sql(
                "election_results",
                engine,
                schema="bronze",
                if_exists="append",
                index=False,
                method="multi",
            )
            loaded += len(chunk)
        except Exception:
            skipped += len(chunk)
    print(f"  [OK] Loaded {loaded:,} rows, skipped {skipped:,} (duplicates/errors)")


def _print_summary(engine):
    """Print a quick summary of what's in the table."""
    with engine.connect() as conn:
        # Year range
        result = conn.execute(text(
            "SELECT MIN(year), MAX(year), COUNT(DISTINCT year) FROM bronze.election_results"
        ))
        row = result.fetchone()
        print(f"\n  --- Summary ---")
        print(f"  Years: {row[0]} to {row[1]} ({row[2]} elections)")

        # State count
        result = conn.execute(text(
            "SELECT COUNT(DISTINCT state_name) FROM bronze.election_results"
        ))
        print(f"  States/UTs: {result.scalar()}")

        # Row count per recent elections
        result = conn.execute(text("""
            SELECT year, COUNT(*) as candidates
            FROM bronze.election_results
            WHERE year >= 2009
            GROUP BY year
            ORDER BY year
        """))
        print(f"\n  Recent elections:")
        for row in result:
            print(f"    {row[0]}: {row[1]:,} candidates")


def main():
    parser = argparse.ArgumentParser(
        description="Load Lok Dhaba election results into bronze.election_results"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to the Lok Dhaba CSV file (default: auto-detect in data/raw/)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BEIP -- Lok Dhaba Ingestion")
    print("=" * 60)

    # Find the CSV
    if args.file:
        csv_path = args.file
    else:
        csv_path = find_csv_file()
        if csv_path is None:
            print(
                "\n[ERROR] No CSV file found in data/raw/\n"
                "\nTo get the data:\n"
                "  1. Go to https://lokdhaba.ashoka.edu.in\n"
                "  2. Register (free) and log in\n"
                "  3. Select: Lok Sabha -> All Years -> All States\n"
                "  4. Download the CSV\n"
                "  5. Save it to: data/raw/All_States_GE.csv\n"
                "  6. Run this script again\n"
                "\nOr specify a file: python -m src.ingestion.load_lok_dhaba --file path/to/file.csv"
            )
            sys.exit(1)

    print(f"\n  [PATH] Source file: {csv_path}")

    # Step 1: Read CSV
    print("\n[1/3] Reading CSV...")
    df = load_csv(str(csv_path))

    # Step 2: Normalize columns
    print("\n[2/3] Normalizing columns...")
    print(f"  [COLS] Original columns ({len(df.columns)}): {list(df.columns)[:10]}...")
    df = normalize_columns(df)
    print(f"  [COLS] Mapped columns ({len(df.columns)}):   {list(df.columns)[:10]}...")

    # Step 3: Load to Postgres
    print("\n[3/3] Loading to Postgres...")
    load_to_postgres(df, source_file=Path(str(csv_path)).name)

    print("\n" + "=" * 60)
    print("[OK] Ingestion complete!")
    print("=" * 60)
    print("\nNext step: verify with SQL:")
    print("  docker compose exec postgres psql -U beip -d beip_warehouse \\")
    print('    -c "SELECT COUNT(*) FROM bronze.election_results;"')


if __name__ == "__main__":
    main()
