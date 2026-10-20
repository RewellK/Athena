"""Pinned OpenJarvis orchestration with Athena-owned tools and memory."""
from pathlib import Path
import sys

VENDOR = Path(__file__).resolve().parents[2] / 'third_party' / 'openjarvis'
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
