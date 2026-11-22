"""Configuration for CodeTutor."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ollama settings — 127.0.0.1 avoids Windows localhost/IPv6 issues
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b-instruct-q4_0")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

# RAG settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RETRIEVAL = 3
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
COURSE_DOCS_DIR = DATA_DIR / "course_docs"
EXERCISES_DIR = DATA_DIR / "exercises"
CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"

# Chroma collection name
CHROMA_COLLECTION_NAME = "course_docs"

# App version (shown in UI — verify you restarted after updates)
APP_VERSION = "1.2.0"
