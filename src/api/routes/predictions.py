"""
BEIP — Prediction Endpoint

Accepts a candidate profile and returns a win probability
from the trained Random Forest model.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import pandas as pd

router = APIRouter()


class CandidateProfile(BaseModel):
    """Input schema for the prediction form."""
    party: str = Field(default="IND", description="Political party abbreviation")
    criminal_cases: int = Field(default=0, ge=0, description="Number of declared criminal cases")
    serious_criminal_cases: int = Field(default=0, ge=0)
    education: str = Field(default="Graduate", description="Education level")
    total_assets: Optional[float] = Field(default=None, description="Total declared assets in INR")
    total_liabilities: Optional[float] = Field(default=None, description="Total declared liabilities in INR")
    total_population: Optional[int] = Field(default=None)
    literacy_rate: Optional[float] = Field(default=None)
    sex_ratio: Optional[float] = Field(default=None)
    sc_percentage: Optional[float] = Field(default=None)
    st_percentage: Optional[float] = Field(default=None)
    worker_participation: Optional[float] = Field(default=None)
    electors: Optional[float] = Field(default=None)
    turnout_percentage: float = Field(default=65.0, ge=0, le=100)
    total_candidates: int = Field(default=10, ge=2)


@router.post("/predict")
def predict_outcome(profile: CandidateProfile):
    """Predict win probability for a given candidate profile."""
    # Import here to access the global model loaded in main.py
    from src.api.main import ml_model

    if ml_model is None:
        raise HTTPException(status_code=503, detail="ML model not loaded. Run train_model.py first.")

    # Build a single-row DataFrame matching the model's expected input
    input_data = pd.DataFrame([{
        "party": profile.party,
        "education": profile.education,
        "criminal_cases": profile.criminal_cases,
        "serious_criminal_cases": profile.serious_criminal_cases,
        "total_assets": profile.total_assets,
        "total_liabilities": profile.total_liabilities,
        "total_population": profile.total_population,
        "literacy_rate": profile.literacy_rate,
        "sex_ratio": profile.sex_ratio,
        "sc_percentage": profile.sc_percentage,
        "st_percentage": profile.st_percentage,
        "worker_participation": profile.worker_participation,
        "electors": profile.electors,
        "turnout_percentage": profile.turnout_percentage,
        "total_candidates": profile.total_candidates,
    }])

    # Get prediction and probability
    prediction = int(ml_model.predict(input_data)[0])
    probabilities = ml_model.predict_proba(input_data)[0]
    win_probability = round(float(probabilities[1]) * 100, 2)

    return {
        "prediction": "WIN" if prediction == 1 else "LOSE",
        "win_probability": win_probability,
        "lose_probability": round(100 - win_probability, 2),
        "input_summary": {
            "party": profile.party,
            "criminal_cases": profile.criminal_cases,
            "education": profile.education,
            "turnout_percentage": profile.turnout_percentage,
            "total_candidates": profile.total_candidates,
        }
    }
