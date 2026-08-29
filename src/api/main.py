"""
BEIP — FastAPI Application Entry Point

Serves the REST API for the React frontend dashboard.
Loads the trained ML model on startup and mounts all route modules.

Usage:
    uvicorn src.api.main:app --reload
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Global model reference — loaded once on startup
ml_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML model on startup, release on shutdown."""
    global ml_model
    model_path = Path(__file__).resolve().parent.parent.parent / "models" / "election_predictor.pkl"
    if model_path.exists():
        ml_model = joblib.load(model_path)
        print(f"[API] Loaded ML model from {model_path}")
    else:
        print(f"[API] WARNING: Model not found at {model_path}. /predict will not work.")
    yield
    ml_model = None


app = FastAPI(
    title="BEIP — Bharat Election Intelligence Platform",
    description="REST API for election data, insights, and ML predictions",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and mount route modules
from src.api.routes import elections, predictions, insights

app.include_router(elections.router, prefix="/api", tags=["Elections"])
app.include_router(predictions.router, prefix="/api", tags=["Predictions"])
app.include_router(insights.router, prefix="/api", tags=["Insights"])


@app.get("/api/health")
def health_check():
    """Quick health check endpoint."""
    return {"status": "ok", "model_loaded": ml_model is not None}
