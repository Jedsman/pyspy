"""
Central configuration for the voice-to-code system.
Defines shared paths and settings.
"""
from pathlib import Path
import os
import json

from dotenv import load_dotenv

load_dotenv()

# Get the shared drive path from an environment variable, defaulting to current directory
# This allows you to configure the shared location without modifying the code.
# On PC2: Z:\ (network share that points to generated_code on PC1)
# On PC1: c:/Users/theje/code/pyspy (local development)
SHARED_DRIVE_PATH = Path(os.getenv("SHARED_DRIVE_PATH", os.getcwd()))

# If SHARED_DRIVE_PATH points to generated_code already (like Z:\), use it directly
# Otherwise (like local dev), create a generated_code subdirectory
if SHARED_DRIVE_PATH.name == "generated_code" or str(SHARED_DRIVE_PATH) == "Z:\\":
    GENERATED_CODE_DIR = SHARED_DRIVE_PATH
else:
    GENERATED_CODE_DIR = SHARED_DRIVE_PATH / "generated_code"

COMMAND_FILE = GENERATED_CODE_DIR / ".command"
SCREENSHOTS_DIR = GENERATED_CODE_DIR / "screenshots"

# Ensure the core directories exist when this config is loaded
GENERATED_CODE_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Interview Coach Configuration
INTERVIEW_COACH_BASE_PATH = Path(os.getenv("INTERVIEW_COACH_BASE_PATH", Path.home() / ".interview_coach"))
KB_CONFIG_FILE = INTERVIEW_COACH_BASE_PATH / "knowledge_base_config.json"

def load_kb_config():
    """Load knowledge base configuration from JSON file."""
    if not KB_CONFIG_FILE.exists():
        return None
    try:
        with open(KB_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load KB config from {KB_CONFIG_FILE}: {e}")
        return None

def get_active_kb_profile():
    """Get the active knowledge base profile and its paths."""
    config = load_kb_config()
    if not config:
        return None

    active = config.get("active_profile", "default")
    profile = config.get("profiles", {}).get(active)

    if not profile:
        return None

    return {
        "name": active,
        "documents_path": Path(profile.get("documents_path", "")),
        "career_history_file": Path(profile.get("career_history_file", "")),
        "domain_context_file": Path(profile.get("domain_context_file", ""))
    }

def validate_profile_paths(profile):
    """Check if profile paths exist and are readable."""
    if not profile:
        return False, "No profile found"

    if not profile["documents_path"].exists():
        return False, f"Documents path not found: {profile['documents_path']}"

    if not profile["career_history_file"].exists():
        return False, f"Career history file not found: {profile['career_history_file']}"

    return True, "Profile valid"
