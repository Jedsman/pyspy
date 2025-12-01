"""
Central configuration for the voice-to-code system.
Defines shared paths and settings.
"""
from pathlib import Path
import os
import socket

# --- Hostname-based configuration for SHARED_DRIVE_PATH ---
HOSTNAME = socket.gethostname()

# Define the paths for each machine.
PATH_CONFIG = {
    "AYAR": "c:/Users/theje/code/pyspy",  # Path on PC1 (AYAR)
    "Mithrim": "z:/",                     # Path on PC2 (Mithrim)
}

# Determine the shared drive path based on the hostname.
# It will fall back to a default if the hostname is not found.
DEFAULT_PATH = "z:/"
SHARED_DRIVE_PATH_STR = PATH_CONFIG.get(HOSTNAME, DEFAULT_PATH)
SHARED_DRIVE_PATH = Path(SHARED_DRIVE_PATH_STR)

print(f"INFO: Hostname: '{HOSTNAME}', Shared Drive Path: '{SHARED_DRIVE_PATH}'")

# Define the main directory for all generated outputs
GENERATED_CODE_DIR = SHARED_DRIVE_PATH / "generated_code"
COMMAND_FILE = GENERATED_CODE_DIR / ".command"
SCREENSHOTS_DIR = GENERATED_CODE_DIR / "screenshots"

# Ensure the core directories exist when this config is loaded
GENERATED_CODE_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
