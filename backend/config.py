import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DUCKDB_PATH = str(DATA_DIR / "reposcout.db")
QDRANT_PATH = str(DATA_DIR / "qdrant_data")
PYPI_CACHE_DIR = DATA_DIR / "pypi_cache"

# --- API Keys ---
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# --- Mistral Models ---
MISTRAL_LARGE = "mistral-large-latest"
DEVSTRAL = "devstral-small-latest"
MISTRAL_EMBED = "mistral-embed"

# --- Qdrant ---
QDRANT_COLLECTION = "packages"
EMBEDDING_DIM = 1024  # mistral-embed output dimension

# --- Scoring Weights ---
SCORE_WEIGHTS = {
    "adoption": 0.35,
    "maintenance": 0.30,
    "maturity": 0.15,
    "community": 0.20,
}

# --- Dataset Stats (updated after data load) ---
DATASET_STATS = {
    "total_packages": 0,
    "total_dependencies": 0,
    "platforms": ["PyPI"],
}
