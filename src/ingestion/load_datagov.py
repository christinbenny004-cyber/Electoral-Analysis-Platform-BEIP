"""
BEIP -- data.gov.in API Client Ingestion

Pulls open government datasets from data.gov.in REST API
and loads into a bronze table.

Usage:
    1. Get an API key from https://data.gov.in/ogpl/apis
       - Register and create an API key
       - Add it to your .env file: DATAGOV_API_KEY=your_key_here

    2. Run this script:
       python -m src.ingestion.load_datagov

    3. Or with a specific resource ID:
       python -m src.ingestion.load_datagov --resource-id <id>

Default dataset: Election Commission constituency-wise voter data
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine

# ============================================
# Configuration
# ============================================
API_BASE = "https://api.data.gov.in/resource"

# Curated list of election-relevant datasets on data.gov.in
# Resource IDs can be found on the dataset pages
DATASETS = {
    "voter_turnout": {
        "resource_id": "8b77c77e-3db5-4f30-a233-e284e4e20959",
        "description": "Voter turnout data by state",
        "table_name": "datagov_voter_turnout",
    },
    "electors_constituency": {
        "resource_id": "8f5e3b2f-5f95-45f3-8abc-4e5e6e889e71",
        "description": "Number of electors by constituency",
        "table_name": "datagov_electors",
    },
}

DEFAULT_DATASET = "voter_turnout"


def get_api_key() -> str:
    """Get data.gov.in API key from environment."""
    key = os.getenv("DATAGOV_API_KEY")
    if not key:
        print(
            "\n[ERROR] No data.gov.in API key found.\n"
            "\nTo get an API key:\n"
            "  1. Go to https://data.gov.in\n"
            "  2. Register for an account\n"
            "  3. Go to APIs section and generate a key\n"
            "  4. Add to your .env file:\n"
            "     DATAGOV_API_KEY=your_api_key_here\n"
        )
        return None
    return key


def fetch_dataset(resource_id: str, api_key: str, limit: int = 1000) -> pd.DataFrame:
    """
    Fetch a dataset from data.gov.in REST API with pagination.

    Args:
        resource_id: The resource identifier from data.gov.in
        api_key: Your API key
        limit: Records per page (max usually 1000)

    Returns:
        DataFrame with all records
    """
    all_records = []
    offset = 0
    total = None

    print(f"  [API] Fetching resource: {resource_id}")
    print(f"  [API] Page size: {limit}")

    while True:
        params = {
            "api-key": api_key,
            "format": "json",
            "offset": offset,
            "limit": limit,
        }

        try:
            resp = requests.get(
                f"{API_BASE}/{resource_id}",
                params=params,
                timeout=120,
                verify=False
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  [ERROR] API request failed: {e}")
            break
        except ValueError as e:
            print(f"  [ERROR] Invalid JSON response: {e}")
            break

        # Extract records
        records = data.get("records", [])
        if not records:
            break

        all_records.extend(records)

        # Get total count on first request
        if total is None:
            total = data.get("total", len(records))
            print(f"  [API] Total records available: {total:,}")

        offset += limit
        print(f"  [API] Fetched {len(all_records):,} / {total:,} records...")

        # Stop if we've got everything
        if len(all_records) >= total:
            break

    if not all_records:
        print("  [ERROR] No records returned from API")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"  [OK] Fetched {len(df):,} total records")
    return df


def load_to_postgres(df: pd.DataFrame, table_name: str, source_info: str):
    """Write DataFrame to a bronze table."""
    engine = get_engine()

    df = df.copy()
    df["source_api"] = "data.gov.in"
    df["source_resource_id"] = source_info

    # Check existing data
    with engine.connect() as conn:
        try:
            existing = conn.execute(text(f"SELECT COUNT(*) FROM bronze.{table_name}")).scalar()
            mode = "append" if existing > 0 else "replace"
        except Exception:
            mode = "replace"

    print(f"\n  [LOAD] Loading {len(df):,} rows into bronze.{table_name}...")
    df.to_sql(
        table_name,
        engine,
        schema="bronze",
        if_exists=mode,
        index=False,
        method="multi",
        chunksize=500,
    )

    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM bronze.{table_name}")).scalar()
        print(f"  [OK] Total rows in bronze.{table_name}: {count:,}")


def load_from_file(file_path: str) -> pd.DataFrame:
    """Load from a pre-downloaded data.gov.in export file."""
    path = Path(file_path)
    if path.suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(path, encoding=enc, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not read {path}")
    print(f"  [FILE] Read {len(df):,} rows from {path.name}")
    return df


def find_datagov_file():
    """Look for pre-downloaded data.gov.in files in data/raw/."""
    raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
    patterns = ["*datagov*", "*data_gov*", "*voter*turnout*"]
    for pattern in patterns:
        for ext in [".csv", ".xlsx", ".xls"]:
            files = list(raw_dir.glob(f"{pattern}{ext}"))
            if files:
                return files[0]
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Load data from data.gov.in into bronze tables"
    )
    parser.add_argument("--file", "-f", type=str, help="Path to pre-downloaded data file")
    parser.add_argument("--resource-id", "-r", type=str, help="data.gov.in resource ID")
    parser.add_argument("--dataset", "-d", type=str, default=DEFAULT_DATASET,
                        choices=list(DATASETS.keys()),
                        help=f"Predefined dataset to fetch (default: {DEFAULT_DATASET})")
    parser.add_argument("--table", "-t", type=str, help="Target bronze table name")
    args = parser.parse_args()

    print("=" * 60)
    print("BEIP -- data.gov.in Ingestion")
    print("=" * 60)

    if args.file:
        # Load from file
        print(f"\n  [PATH] Source file: {args.file}")
        df = load_from_file(args.file)
        table_name = args.table or "datagov_import"
        source_info = Path(args.file).name
    else:
        # Try pre-downloaded file first
        found = find_datagov_file()
        if found:
            print(f"\n  [PATH] Found pre-downloaded file: {found}")
            df = load_from_file(str(found))
            table_name = args.table or "datagov_import"
            source_info = found.name
        else:
            # Use API
            api_key = get_api_key()
            if not api_key:
                sys.exit(1)

            dataset_config = DATASETS[args.dataset]
            resource_id = args.resource_id or dataset_config["resource_id"]
            table_name = args.table or dataset_config["table_name"]

            print(f"\n  [INFO] Dataset: {dataset_config['description']}")
            print(f"  [INFO] Resource ID: {resource_id}")

            print("\n[1/2] Fetching from API...")
            df = fetch_dataset(resource_id, api_key)

            if df.empty:
                print("\n[ERROR] No data fetched. Check your API key and resource ID.")
                sys.exit(1)

            source_info = resource_id

    print(f"\n  [COLS] Columns ({len(df.columns)}): {list(df.columns)[:10]}...")

    print("\n[2/2] Loading to Postgres...")
    load_to_postgres(df, table_name, source_info)

    print("\n" + "=" * 60)
    print("[OK] data.gov.in ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
