"""Global state and configuration for PMOVES-DoX backend.

This module initializes all singleton services and global constants used
throughout the application. It must be imported before other app modules
to ensure proper initialization order.

Globals:
    UPLOAD_DIR: Directory for uploaded files
    ARTIFACTS_DIR: Directory for processed artifacts
    db: Database instance (SQLite or Supabase)
    DB_BACKEND_META: Metadata about the database backend
    qa_engine: Question-answering engine instance
    search_index: Vector search index instance
    summary_service: Document summarization service
    HRM_ENABLED: Whether Halting Reasoning Module is enabled
    HRM_CFG: HRM configuration parameters
    HRM_STATS: HRM metrics collector
    TASKS: In-memory task registry for background jobs
    START_TIME: Application startup timestamp
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from app.database_factory import init_database
from app.qa_engine import QAEngine
from app.search import SearchIndex
from app.analysis.summarization import SummarizationService
from app.hrm import HRMConfig, HRMMetrics

load_dotenv()

# Initialize directories
UPLOAD_DIR = Path("uploads")
ARTIFACTS_DIR = Path("artifacts")
UPLOAD_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Database and Services
db, DB_BACKEND_META = init_database()
qa_engine = QAEngine(db)
search_index = SearchIndex(db)
summary_service = SummarizationService(db)

# HRM Config
HRM_ENABLED = os.getenv("HRM_ENABLED", "false").lower() == "true"
HRM_CFG = HRMConfig(
    Mmax=int(os.getenv("HRM_MMAX", "6")),
    Mmin=int(os.getenv("HRM_MMIN", "2")),
    threshold=float(os.getenv("HRM_THRESHOLD", "0.5")),
)
HRM_STATS = HRMMetrics()

# Global State
TASKS: dict[str, dict] = {}
START_TIME = time.time()

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MEDIA_SUFFIXES = AUDIO_SUFFIXES | VIDEO_SUFFIXES

def env_flag(name: str, default: bool = False) -> bool:
    """Parse an environment variable as a boolean flag.

    Args:
        name: Environment variable name to look up.
        default: Default value if variable is not set.

    Returns:
        True if the variable is set to "1", "true", "yes", or "on" (case-insensitive).
        False if set to any other value or not set (uses default).
    """
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip()
    if not val:
        return default
    return val.lower() in {"1", "true", "yes", "on"}
