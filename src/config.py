import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CLONE_BASE_DIR = Path(os.getenv("CLONE_BASE_DIR", "/tmp/repo-onboarding-agent/repos"))
MAX_ITERATIONS_DEFAULT = int(os.getenv("MAX_ITERATIONS", "8"))
