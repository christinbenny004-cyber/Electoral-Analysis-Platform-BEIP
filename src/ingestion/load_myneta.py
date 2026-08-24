"""
BEIP -- MyNeta / ADR Candidate Affidavit Ingestion

Scrapes candidate affidavit data (assets, criminal cases, education)
from MyNeta.info and loads into bronze.candidate_affidavits.

Usage:
    python -m src.ingestion.load_myneta
    python -m src.ingestion.load_myneta --year 2019 --type LS
    python -m src.ingestion.load_myneta --file data/raw/myneta_2019.csv

Notes:
    - MyNeta.info is run by the Association for Democratic Reforms (ADR)
    - This scraper respects rate limits (1 request per 2 seconds)
    - If you have a pre-downloaded CSV/Excel file, use --file instead
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Configuration
# ============================================
BASE_URL = "https://www.myneta.info"
REQUEST_DELAY = 2.0  # seconds between requests (be respectful)
HEADERS = {
    "User-Agent": "BEIP-Academic-Research/1.0 (election data project)",
    "Accept": "text/html,application/xhtml+xml",
}

# Lok Sabha election pages on MyNeta
ELECTION_PAGES = {
    2019: f"{BASE_URL}/LokSabha2019/",
    2014: f"{BASE_URL}/LokSabha2014/",
    2009: f"{BASE_URL}/ls2009/",
}

COLUMN_MAP = {
    "Candidate": "candidate_name",
    "candidate": "candidate_name",
    "Name": "candidate_name",
    "Constituency": "constituency_name",
    "constituency": "constituency_name",
    "Party": "party",
    "party": "party",
    "Criminal Cases": "criminal_cases",
    "criminal_cases": "criminal_cases",
    "Criminal\nCases": "criminal_cases",
    "Serious Criminal Cases": "serious_criminal_cases",
    "Education": "education",
    "education": "education",
    "Total Assets": "total_assets",
    "total_assets": "total_assets",
    "Liabilities": "total_liabilities",
    "Total Liabilities": "total_liabilities",
    "total_liabilities": "total_liabilities",
    "State": "state_name",
    "state": "state_name",
}


def find_myneta_file():
    """Look for pre-downloaded MyNeta data in data/raw/."""
    raw_dir = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
    
    patterns = ["*myneta*", "*MyNeta*", "*MYNETA*", "*adr*", "*ADR*", "*affidavit*"]
    extensions = [".csv", ".xlsx", ".xls"]
    
    for pattern in patterns:
        for ext in extensions:
            files = list(raw_dir.glob(f"{pattern}{ext}"))
            if files:
                return files[0]
    return None


def load_from_file(file_path: str) -> pd.DataFrame:
    """Load pre-downloaded MyNeta data from file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(path, encoding=encoding, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not read {path}")

    print(f"  [FILE] Read {len(df):,} rows from {path.name}")
    return df


def scrape_constituency_list(election_url: str) -> list:
    """Get list of constituency URLs from a MyNeta election page."""
    print(f"  [SCRAPE] Fetching constituency list from {election_url}")
    
    try:
        resp = requests.get(election_url, headers=HEADERS, timeout=30, verify=False)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] Failed to fetch {election_url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    
    # MyNeta lists constituencies as links in the main content
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Constituency pages typically have numeric IDs
        if "index.php?action=show_candidates&constituency_id=" in href:
            full_url = href if href.startswith("http") else f"{election_url.rstrip('/')}/{href}"
            name = a_tag.get_text(strip=True)
            links.append({"name": name, "url": full_url})

    print(f"  [SCRAPE] Found {len(links)} constituencies")
    time.sleep(REQUEST_DELAY)
    return links


def scrape_constituency_candidates(url: str, constituency_name: str) -> list:
    """Scrape candidate data from a single constituency page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] Failed to fetch {constituency_name}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    candidates = []

    # MyNeta typically presents candidate data in a table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Check if this looks like a candidate table
        header_text = rows[0].get_text().lower()
        if "candidate" not in header_text and "party" not in header_text:
            continue

        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]

        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= len(headers):
                candidate = dict(zip(headers, cells[:len(headers)]))
                candidate["constituency_name"] = constituency_name
                candidate["source_url"] = url
                candidates.append(candidate)

    time.sleep(REQUEST_DELAY)
    return candidates


def scrape_election(year: int) -> pd.DataFrame:
    """
    Scrape all candidate data for a given election year.
    This is the main scraping entry point.
    """
    if year not in ELECTION_PAGES:
        print(f"  [ERROR] No MyNeta URL configured for year {year}")
        print(f"  [INFO] Available years: {list(ELECTION_PAGES.keys())}")
        return pd.DataFrame()

    election_url = ELECTION_PAGES[year]
    print(f"\n  [SCRAPE] Scraping MyNeta data for {year}...")
    print(f"  [INFO] URL: {election_url}")
    print(f"  [INFO] Rate limit: {REQUEST_DELAY}s between requests")

    # Step 1: Get constituency list
    constituencies = scrape_constituency_list(election_url)
    if not constituencies:
        print("  [ERROR] No constituencies found. The page structure may have changed.")
        return pd.DataFrame()

    # Step 2: Scrape each constituency
    all_candidates = []
    total = len(constituencies)
    for i, const in enumerate(constituencies, 1):
        print(f"  [SCRAPE] [{i}/{total}] {const['name']}...", end=" ")
        candidates = scrape_constituency_candidates(const["url"], const["name"])
        all_candidates.extend(candidates)
        print(f"{len(candidates)} candidates")

    if not all_candidates:
        print("  [ERROR] No candidate data scraped.")
        return pd.DataFrame()

    df = pd.DataFrame(all_candidates)
    df["year"] = year
    print(f"\n  [OK] Scraped {len(df):,} candidates from {total} constituencies")
    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names."""
    df.columns = df.columns.str.strip()
    renamed = {col: COLUMN_MAP[col] for col in df.columns if col in COLUMN_MAP}
    df = df.rename(columns=renamed)
    return df


def parse_money(value) -> int:
    """Parse Indian currency strings like '1,23,456' or '1.5 Crore' to integer."""
    if pd.isna(value):
        return None
    s = str(value).strip().replace(",", "").replace(" ", "")
    
    # Handle Crore/Lakh notation
    s_lower = s.lower()
    if "crore" in s_lower or "cr" in s_lower:
        try:
            num = float(s_lower.replace("crore", "").replace("cr", "").replace("rs", "").replace(".", "").strip())
            return int(num * 10000000)
        except ValueError:
            pass
    if "lakh" in s_lower or "lac" in s_lower:
        try:
            num = float(s_lower.replace("lakh", "").replace("lac", "").replace("rs", "").replace(".", "").strip())
            return int(num * 100000)
        except ValueError:
            pass

    # Try direct parse
    try:
        return int(float(s.replace("Rs", "").replace("rs", "").strip()))
    except (ValueError, OverflowError):
        return None


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and type-cast MyNeta data."""
    df = df.copy()

    if "criminal_cases" in df.columns:
        df["criminal_cases"] = pd.to_numeric(df["criminal_cases"], errors="coerce")
    if "serious_criminal_cases" in df.columns:
        df["serious_criminal_cases"] = pd.to_numeric(df["serious_criminal_cases"], errors="coerce")
    if "total_assets" in df.columns:
        df["total_assets"] = df["total_assets"].apply(parse_money)
    if "total_liabilities" in df.columns:
        df["total_liabilities"] = df["total_liabilities"].apply(parse_money)

    return df


def load_to_postgres(df: pd.DataFrame, source_file: str):
    """Write DataFrame to bronze.candidate_affidavits."""
    engine = get_engine()

    df = df.copy()
    df["source_file"] = source_file

    with engine.connect() as conn:
        try:
            existing = conn.execute(text("SELECT COUNT(*) FROM bronze.candidate_affidavits")).scalar()
        except Exception:
            existing = 0

    mode = "replace" if existing == 0 else "append"

    print(f"\n  [LOAD] Loading {len(df):,} rows into bronze.candidate_affidavits...")
    df.to_sql(
        "candidate_affidavits",
        engine,
        schema="bronze",
        if_exists=mode,
        index=False,
        method="multi",
        chunksize=500,
    )

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM bronze.candidate_affidavits")).scalar()
        print(f"  [OK] Total rows in bronze.candidate_affidavits: {count:,}")


def main():
    parser = argparse.ArgumentParser(
        description="Load MyNeta candidate affidavit data into bronze.candidate_affidavits"
    )
    parser.add_argument("--file", "-f", type=str, help="Path to pre-downloaded data file")
    parser.add_argument("--year", "-y", type=int, default=2019, help="Election year to scrape (default: 2019)")
    parser.add_argument("--type", "-t", type=str, default="LS", help="Election type: LS (Lok Sabha)")
    args = parser.parse_args()

    print("=" * 60)
    print("BEIP -- MyNeta Candidate Affidavit Ingestion")
    print("=" * 60)

    if args.file:
        # Load from pre-downloaded file
        print(f"\n  [PATH] Source file: {args.file}")
        print("\n[1/3] Reading file...")
        df = load_from_file(args.file)
        source = Path(args.file).name
    else:
        # Try to find a pre-downloaded file first
        found = find_myneta_file()
        if found:
            print(f"\n  [PATH] Found pre-downloaded file: {found}")
            print("\n[1/3] Reading file...")
            df = load_from_file(str(found))
            source = found.name
        else:
            # Scrape from MyNeta
            print(f"\n  [INFO] No pre-downloaded file found. Will scrape MyNeta.")
            print(f"  [INFO] This will take a while due to rate limiting.")
            print(f"  [INFO] Target: Lok Sabha {args.year}")
            print("\n[1/3] Scraping MyNeta...")
            df = scrape_election(args.year)
            source = f"myneta_scrape_ls_{args.year}"

            if df.empty:
                print("\n[ERROR] No data obtained. Try downloading manually from myneta.info")
                print("  and saving to data/raw/myneta_2019.csv, then run with --file flag.")
                sys.exit(1)

    print("\n[2/3] Normalizing and cleaning...")
    df = normalize_columns(df)
    df = clean_data(df)
    print(f"  [COLS] Columns: {list(df.columns)}")

    print("\n[3/3] Loading to Postgres...")
    load_to_postgres(df, source_file=source)

    print("\n" + "=" * 60)
    print("[OK] MyNeta ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
