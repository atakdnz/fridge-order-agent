"""
Application settings and configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
AUTH_DIR = BASE_DIR / ".auth"
AUTH_FILE = AUTH_DIR / "getir_session.json"
MIGROS_AUTH_FILE = AUTH_DIR / "migros_session.json"

# Getir URLs
GETIR_BASE_URL = "https://getir.com"
GETIR_SEARCH_URL = f"{GETIR_BASE_URL}/arama"

# Migros URLs
MIGROS_BASE_URL = "https://www.migros.com.tr"
MIGROS_SEARCH_URL = f"{MIGROS_BASE_URL}/arama"

# Browser settings
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
TIMEOUT = int(os.getenv("TIMEOUT", "30")) * 1000  # Convert to milliseconds

# Ensure auth directory exists
AUTH_DIR.mkdir(exist_ok=True)
