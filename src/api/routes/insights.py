"""
BEIP — Insights Endpoints

Serves pre-computed analytics for the Insights page:
feature importance, party win rates, criminal analysis, education analysis.
"""

from fastapi import APIRouter
import pandas as pd
import joblib
from pathlib import Path

from src.config import get_engine

router = APIRouter()


@router.get("/insights/feature-importance")
def get_feature_importance():
    """Return top 10 feature importances from the trained model."""
    model_path = Path(__file__).resolve().parent.parent.parent.parent / "models" / "election_predictor.pkl"
    if not model_path.exists():
        return {"features": [], "error": "Model not found"}

    model = joblib.load(model_path)

    # Extract feature names from the preprocessor
    numeric_features = [
        'criminal_cases', 'serious_criminal_cases', 'total_assets', 'total_liabilities',
        'total_population', 'literacy_rate', 'sex_ratio', 'sc_percentage', 'st_percentage',
        'worker_participation', 'electors', 'turnout_percentage', 'total_candidates'
    ]
    categorical_features = ['party', 'education']

    num_names = list(model.named_steps['preprocessor'].named_transformers_['num'].get_feature_names_out(numeric_features))
    cat_names = list(model.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out(categorical_features))
    all_names = num_names + cat_names

    importances = model.named_steps['classifier'].feature_importances_
    feat_df = pd.DataFrame({'feature': all_names, 'importance': importances})
    feat_df = feat_df.sort_values('importance', ascending=False).head(10)

    return {"features": feat_df.to_dict(orient="records")}


@router.get("/insights/party-winrates")
def get_party_winrates():
    """Win rates by party (minimum 10 candidates)."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT party, won FROM gold.candidate_features", conn)

    stats = df.groupby("party").agg(
        candidates=("won", "count"),
        wins=("won", "sum"),
    ).reset_index()
    stats["win_rate"] = (stats["wins"] / stats["candidates"] * 100).round(2)
    stats = stats[stats["candidates"] >= 10].sort_values("win_rate", ascending=False).head(15)

    return {"party_winrates": stats.to_dict(orient="records")}


@router.get("/insights/criminal-analysis")
def get_criminal_analysis():
    """Win rate comparison: candidates with criminal cases vs clean record."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT criminal_cases, won FROM gold.candidate_features", conn)

    df["has_cases"] = df["criminal_cases"] > 0
    stats = df.groupby("has_cases").agg(
        candidates=("won", "count"),
        wins=("won", "sum"),
    ).reset_index()
    stats["win_rate"] = (stats["wins"] / stats["candidates"] * 100).round(2)
    stats["label"] = stats["has_cases"].map({True: "Has Criminal Cases", False: "Clean Record"})

    return {"criminal_analysis": stats[["label", "candidates", "wins", "win_rate"]].to_dict(orient="records")}


@router.get("/insights/education-analysis")
def get_education_analysis():
    """Win rates by education level."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT education, won FROM gold.candidate_features", conn)

    stats = df.groupby("education").agg(
        candidates=("won", "count"),
        wins=("won", "sum"),
    ).reset_index()
    stats["win_rate"] = (stats["wins"] / stats["candidates"] * 100).round(2)
    stats = stats.sort_values("win_rate", ascending=False)

    return {"education_analysis": stats.to_dict(orient="records")}
