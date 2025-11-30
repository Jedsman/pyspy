"""
Central configuration for the voice-to-code system.
Defines shared paths and settings.
"""
from pathlib import Path
import os

# Get the shared drive path from an environment variable, defaulting to "z:/"
# This allows you to configure the shared location without modifying the code.
# Example for PC2: set SHARED_DRIVE_PATH=z:/
# Example for PC1: set SHARED_DRIVE_PATH=c:/path/to/your/shared/folder
SHARED_DRIVE_PATH = Path(os.getenv("SHARED_DRIVE_PATH", "/"))

# Define the main directory for all generated outputs
GENERATED_CODE_DIR = SHARED_DRIVE_PATH / "generated_code"
COMMAND_FILE = GENERATED_CODE_DIR / ".command"
SCREENSHOTS_DIR = GENERATED_CODE_DIR / "screenshots"

# Ensure the core directories exist when this config is loaded
GENERATED_CODE_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
