import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import nzherald


TEST_DATA_DIR = Path(ROOT) / "tests" / "data"
