"""
Configuration management for GoodFoods AI Reservation System
Loads environment variables and provides centralized config access
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"

# LLM Configuration - Using Llama-3.1-8B via Groq (FREE & Lightweight!)
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Get the appropriate API key
def get_api_key() -> str:
    """Get the API key for Groq"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is not set. Get your free key at https://console.groq.com/keys")
    return GROQ_API_KEY

# Database Configuration
RESTAURANT_DB_PATH = PROJECT_ROOT / os.getenv("RESTAURANT_DB_PATH", "data/restaurants.json")
RESERVATION_DB_PATH = PROJECT_ROOT / os.getenv("RESERVATION_DB_PATH", "data/reservations.json")

# Application Settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Reservation Settings
MAX_PARTY_SIZE = 20
MIN_PARTY_SIZE = 1
BOOKING_HORIZON_DAYS = 90  # How far ahead can people book
CANCELLATION_HOURS = 2  # Minimum hours before reservation to cancel

# Restaurant Operation Defaults
DEFAULT_OPERATING_HOURS = {
    "open": "11:00",
    "close": "22:00"
}

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Validate configuration
def validate_config():
    """Validate that required configuration is present"""
    errors = []
    
    try:
        api_key = get_api_key()
        if not api_key:
            errors.append("GEMINI_API_KEY is not set")
    except ValueError as e:
        errors.append(str(e))
    
    if not MODEL_NAME:
        errors.append("MODEL_NAME is not set")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
