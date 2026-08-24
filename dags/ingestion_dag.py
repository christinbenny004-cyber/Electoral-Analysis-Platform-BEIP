"""
BEIP -- Airflow DAG: Election Data Ingestion Pipeline

Orchestrates all data ingestion scripts as Airflow tasks.
Currently configured for manual trigger only (no schedule).

Usage:
    - Trigger from Airflow UI at http://localhost:8080
    - Or via CLI: airflow dags trigger beip_ingestion

Task flow:
    load_lok_dhaba ──┐
    load_census ─────┤──> verify_row_counts
    load_myneta ─────┘
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


# ============================================
# DAG Configuration
# ============================================
default_args = {
    "owner": "beip",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="beip_ingestion",
    default_args=default_args,
    description="BEIP: Ingest election data from all sources into Bronze tables",
    schedule_interval=None,  # Manual trigger only for now
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["beip", "ingestion", "bronze"],
)


# ============================================
# Task Functions
# ============================================
def run_lok_dhaba():
    """Run Lok Dhaba ingestion script."""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "src.ingestion.load_lok_dhaba"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Lok Dhaba ingestion failed: {result.stderr}")


def run_census():
    """Run Census ingestion script."""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "src.ingestion.load_census"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Census ingestion failed: {result.stderr}")


def run_myneta():
    """Run MyNeta ingestion script."""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "src.ingestion.load_myneta"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"MyNeta ingestion failed: {result.stderr}")


def verify_row_counts():
    """Check that all bronze tables have data."""
    import sys
    sys.path.insert(0, "/opt/airflow")
    from src.config import get_engine
    from sqlalchemy import text

    engine = get_engine()
    tables = [
        "bronze.election_results",
        "bronze.census_demographics",
        "bronze.candidate_affidavits",
    ]

    print("\n=== Row Count Verification ===")
    all_ok = True
    for table in tables:
        try:
            with engine.connect() as conn:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                status = "[OK]" if count > 0 else "[EMPTY]"
                print(f"  {status} {table}: {count:,} rows")
                if count == 0:
                    all_ok = False
        except Exception as e:
            print(f"  [ERROR] {table}: {e}")
            all_ok = False

    if not all_ok:
        print("\n[WARN] Some tables are empty. Check individual task logs.")


# ============================================
# Task Definitions
# ============================================
with dag:
    t_lok_dhaba = PythonOperator(
        task_id="load_lok_dhaba",
        python_callable=run_lok_dhaba,
    )

    t_census = PythonOperator(
        task_id="load_census",
        python_callable=run_census,
    )

    t_myneta = PythonOperator(
        task_id="load_myneta",
        python_callable=run_myneta,
    )

    t_verify = PythonOperator(
        task_id="verify_row_counts",
        python_callable=verify_row_counts,
    )

    # Dependencies: all ingestion tasks run in parallel, then verify
    [t_lok_dhaba, t_census, t_myneta] >> t_verify
