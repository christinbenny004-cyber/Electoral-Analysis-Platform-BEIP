"""
BEIP -- Great Expectations Data Quality Suite

Validates bronze.election_results before promotion to Silver layer.

Checks:
    1. No nulls in constituency_name
    2. vote_share between 0 and 100
    3. No duplicate (year, state_name, constituency_name, candidate_name) rows
    4. Sum of vote shares per constituency is approximately 100%

Usage:
    python -m src.validation.expectations
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import get_engine


# ============================================
# Validation checks
# ============================================
class ValidationResult:
    """Simple container for a validation check result."""
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

    def __str__(self):
        status = "[PASS]" if self.passed else "[FAIL]"
        detail = f" -- {self.detail}" if self.detail else ""
        return f"  {status} {self.name}{detail}"


def load_election_results() -> pd.DataFrame:
    """Load bronze.election_results into a DataFrame for validation."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM bronze.election_results", conn)
    print(f"  [DATA] Loaded {len(df):,} rows from bronze.election_results")
    return df


def check_no_null_constituency(df: pd.DataFrame) -> ValidationResult:
    """Check 1: No nulls in constituency_name."""
    nulls = df["constituency_name"].isna().sum()
    return ValidationResult(
        name="No nulls in constituency_name",
        passed=nulls == 0,
        detail=f"{nulls:,} null values found" if nulls > 0 else f"All {len(df):,} rows have values"
    )


def check_vote_share_range(df: pd.DataFrame) -> ValidationResult:
    """Check 2: vote_share is between 0 and 100."""
    if "vote_share" not in df.columns:
        return ValidationResult("vote_share range [0, 100]", False, "Column not found")

    valid = df["vote_share"].dropna()
    out_of_range = valid[(valid < 0) | (valid > 100)]
    return ValidationResult(
        name="vote_share between 0 and 100",
        passed=len(out_of_range) == 0,
        detail=f"{len(out_of_range):,} values outside range" if len(out_of_range) > 0
               else f"All {len(valid):,} non-null values in range"
    )


def check_no_duplicate_candidates(df: pd.DataFrame) -> ValidationResult:
    """Check 3: No duplicate (year, state, constituency, candidate) rows."""
    key_cols = ["year", "state_name", "constituency_name", "candidate_name"]
    available_keys = [c for c in key_cols if c in df.columns]

    if len(available_keys) < 4:
        return ValidationResult("No duplicate candidates", False,
                                f"Missing columns: {set(key_cols) - set(available_keys)}")

    dupes = df.duplicated(subset=available_keys, keep=False)
    n_dupes = dupes.sum()
    return ValidationResult(
        name="No duplicate (year, state, constituency, candidate) rows",
        passed=n_dupes == 0,
        detail=f"{n_dupes:,} duplicate rows found" if n_dupes > 0
               else f"All {len(df):,} rows are unique on key columns"
    )


def check_vote_share_sum(df: pd.DataFrame, tolerance: float = 5.0) -> ValidationResult:
    """
    Check 4: Sum of vote shares per constituency is approximately 100%.
    Allows a tolerance since NOTA, rejected votes, etc. may cause slight deviations.
    """
    if "vote_share" not in df.columns or "constituency_name" not in df.columns:
        return ValidationResult("Vote share sums ~100%", False, "Required columns not found")

    # Group by year + constituency
    group_cols = ["year", "state_name", "constituency_name"]
    available = [c for c in group_cols if c in df.columns]

    sums = df.groupby(available)["vote_share"].sum()
    
    # Check how many are within tolerance of 100
    within_tolerance = ((sums >= 100 - tolerance) & (sums <= 100 + tolerance)).sum()
    total_groups = len(sums)
    far_off = sums[(sums < 100 - tolerance) | (sums > 100 + tolerance)]

    pct_ok = (within_tolerance / total_groups * 100) if total_groups > 0 else 0

    return ValidationResult(
        name=f"Vote share sums ~100% (tolerance: +/-{tolerance}%)",
        passed=pct_ok >= 95,  # Allow 5% of constituencies to be off
        detail=f"{within_tolerance:,}/{total_groups:,} constituencies within tolerance ({pct_ok:.1f}%)"
    )


def check_position_values(df: pd.DataFrame) -> ValidationResult:
    """Bonus check: position values are positive integers."""
    if "position" not in df.columns:
        return ValidationResult("Position values valid", False, "Column not found")

    valid = df["position"].dropna()
    invalid = valid[valid <= 0]
    return ValidationResult(
        name="Position values are positive",
        passed=len(invalid) == 0,
        detail=f"{len(invalid):,} non-positive values" if len(invalid) > 0
               else f"All {len(valid):,} values are positive"
    )


def check_year_range(df: pd.DataFrame) -> ValidationResult:
    """Bonus check: years are in a sensible range."""
    if "year" not in df.columns:
        return ValidationResult("Year range valid", False, "Column not found")

    min_year = df["year"].min()
    max_year = df["year"].max()
    sensible = min_year >= 1950 and max_year <= 2030

    return ValidationResult(
        name="Years in sensible range (1950-2030)",
        passed=sensible,
        detail=f"Range: {min_year} to {max_year}"
    )


def run_all_checks():
    """Run all validation checks and report results."""
    print("=" * 60)
    print("BEIP -- Data Quality Validation")
    print("=" * 60)

    print("\n[1/2] Loading data...")
    df = load_election_results()

    print("\n[2/2] Running checks...\n")

    checks = [
        check_no_null_constituency(df),
        check_vote_share_range(df),
        check_no_duplicate_candidates(df),
        check_vote_share_sum(df),
        check_position_values(df),
        check_year_range(df),
    ]

    for check in checks:
        print(check)

    # Summary
    passed = sum(1 for c in checks if c.passed)
    total = len(checks)
    all_passed = passed == total

    print(f"\n{'=' * 60}")
    if all_passed:
        print(f"[OK] All {total} checks passed!")
    else:
        print(f"[WARN] {passed}/{total} checks passed, {total - passed} failed")
    print(f"{'=' * 60}")

    return all_passed


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
