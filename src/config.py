"""
BEIP — Database Configuration

Provides a reusable SQLAlchemy engine connected to the BEIP Postgres warehouse.
All ingestion and validation scripts import from here.

Usage:
    from src.config import get_engine
    engine = get_engine()
    df.to_sql("election_results", engine, schema="bronze", if_exists="append")
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env from project root (works whether you run from root or src/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def get_engine():
    """
    Create and return a SQLAlchemy engine using .env credentials.

    Returns:
        sqlalchemy.Engine connected to the BEIP Postgres warehouse.

    Raises:
        ValueError: If required environment variables are missing.
    """
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB")

    if not all([user, password, db]):
        raise ValueError(
            "Missing database credentials. "
            "Make sure POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB "
            "are set in your .env file. "
            f"Looking for .env at: {_env_path}"
        )

    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url, echo=False)


def test_connection():
    """
    Quick connectivity check. Prints schema list if successful.
    Run directly: python -m src.config
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;")
        )
        schemas = [row[0] for row in result]
        print(f"[OK] Connected to Postgres successfully!")
        print(f"     Schemas: {', '.join(schemas)}")
    return True


if __name__ == "__main__":
    test_connection()
