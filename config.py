"""
Central configuration for the voice-to-code system.
Defines shared paths and settings.
"""
from pathlib import Path
import os

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
