"""
BEIP — Election Data Endpoints

Serves historical election data from the Gold layer for the React dashboard.
"""

from fastapi import APIRouter, Query
from typing import Optional
import pandas as pd

from src.config import get_engine

router = APIRouter()


@router.get("/elections/summary")
def get_summary():
    """High-level stats for the Dashboard page."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM gold.candidate_features", conn)

    total_candidates = len(df)
    total_constituencies = df["constituency_name"].nunique()
    total_states = df["state_name"].nunique()
    winners = df[df["won"] == 1]

    # Top party by win count
    party_wins = winners["party"].value_counts()
    top_party = party_wins.index[0] if len(party_wins) > 0 else "N/A"
    top_party_wins = int(party_wins.iloc[0]) if len(party_wins) > 0 else 0

    # Win rate by party (top 10)
    party_stats = df.groupby("party").agg(
        candidates=("candidate_name", "count"),
        wins=("won", "sum"),
    ).reset_index()
    party_stats["win_rate"] = (party_stats["wins"] / party_stats["candidates"] * 100).round(2)
    party_stats = party_stats[party_stats["candidates"] >= 5].sort_values("wins", ascending=False).head(10)

    return {
        "total_candidates": total_candidates,
        "total_constituencies": total_constituencies,
        "total_states": total_states,
        "top_party": top_party,
        "top_party_wins": top_party_wins,
        "party_stats": party_stats.to_dict(orient="records"),
    }


@router.get("/elections/results")
def get_results(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=200),
    state: Optional[str] = None,
    party: Optional[str] = None,
    year: Optional[int] = None,
    search: Optional[str] = None,
):
    """Paginated, filterable election results for the Explorer page."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM gold.candidate_features ORDER BY year DESC, state_name, constituency_name", conn)

    # Apply filters
    if state:
        df = df[df["state_name"] == state]
    if party:
        df = df[df["party"] == party]
    if year:
        df = df[df["year"] == year]
    if search:
        mask = (
            df["candidate_name"].str.contains(search, case=False, na=False)
            | df["constituency_name"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    total = len(df)
    start = (page - 1) * per_page
    end = start + per_page
    page_df = df.iloc[start:end]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "results": page_df.fillna("").to_dict(orient="records"),
    }


@router.get("/elections/states")
def get_states():
    """List of all available states."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT DISTINCT state_name FROM gold.candidate_features ORDER BY state_name", conn)
    return {"states": df["state_name"].tolist()}


@router.get("/elections/parties")
def get_parties():
    """List of all available parties (with candidate count >= 5)."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT party, COUNT(*) as cnt FROM gold.candidate_features "
            "GROUP BY party HAVING COUNT(*) >= 5 ORDER BY cnt DESC",
            conn
        )
    return {"parties": df["party"].tolist()}
