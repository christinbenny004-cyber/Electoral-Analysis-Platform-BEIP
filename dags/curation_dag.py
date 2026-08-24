"""
BEIP -- Airflow DAG: Data Curation Pipeline (Bronze -> Silver)

Orchestrates validation and transformation of all Bronze tables
into the clean Silver layer.

This DAG should be triggered AFTER beip_ingestion completes successfully.

Task flow:
    validate_election_results ──> transform_election_results ──┐
                                                                ├──> verify_silver_counts
    transform_census ───────────────────────────────────────────┤
    transform_myneta ───────────────────────────────────────────┘

Usage:
    - Trigger from Airflow UI at http://localhost:8080
    - Or via CLI: airflow dags trigger beip_curation
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


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
    dag_id="beip_curation",
    default_args=default_args,
    description="BEIP: Validate Bronze data and promote clean data to Silver tables",
    schedule_interval=None,  # Manual trigger — run after beip_ingestion
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["beip", "validation", "silver"],
)


# ============================================
# Task Functions
# ============================================
def run_validate_election_results():
    """Run Great Expectations checks on bronze.election_results."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "src.validation.expectations"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(
            f"Data validation failed — stopping pipeline before Silver write.\n{result.stderr}"
        )


def run_transform_election_results():
    """Run Bronze -> Silver transform for election results."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "src.validation.transform_election_results"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Election results transform failed: {result.stderr}")


def run_transform_census():
    """Run Bronze -> Silver transform for census demographics."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "src.validation.transform_census"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"Census transform failed: {result.stderr}")


def run_transform_myneta():
    """Run Bronze -> Silver transform for candidate affidavits."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "src.validation.transform_myneta"],
        capture_output=True, text=True, cwd="/opt/airflow"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise Exception(f"MyNeta transform failed: {result.stderr}")


def verify_silver_counts():
    """Check that all Silver tables have data after transforms."""
    import sys
    sys.path.insert(0, "/opt/airflow")
    from src.config import get_engine
    from sqlalchemy import text

    engine = get_engine()
    tables = [
        "silver.election_results",
        "silver.census_demographics",
        "silver.candidate_affidavits",
    ]

    print("\n=== Silver Layer Row Count Verification ===")
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
        raise Exception("[FAIL] One or more Silver tables are empty. Check transform task logs.")

    print("\n[OK] All Silver tables populated successfully.")


# ============================================
# Task Definitions
# ============================================
with dag:
    # --- Validation Gate ---
    # Must pass before election results are written to Silver
    t_validate = PythonOperator(
        task_id="validate_election_results",
        python_callable=run_validate_election_results,
    )

    # --- Silver Transforms ---
    t_transform_elections = PythonOperator(
        task_id="transform_election_results",
        python_callable=run_transform_election_results,
    )

    t_transform_census = PythonOperator(
        task_id="transform_census",
        python_callable=run_transform_census,
    )

    t_transform_myneta = PythonOperator(
        task_id="transform_myneta",
        python_callable=run_transform_myneta,
    )

    # --- Final Verification ---
    t_verify_silver = PythonOperator(
        task_id="verify_silver_counts",
        python_callable=verify_silver_counts,
    )

    # --- Pipeline Dependencies ---
    # 1. Validate election data first (acts as a gate)
    # 2. Transform elections only if validation passes
    # 3. Census and MyNeta transforms run in parallel (no dependency on elections)
    # 4. Final verification runs only after ALL three transforms complete
    t_validate >> t_transform_elections
    [t_transform_elections, t_transform_census, t_transform_myneta] >> t_verify_silver
