"""Local fakes for external services. You do not need to modify anything here.

Importing this package makes the shared mock library (``shared``) importable.
"""

import os
import sys
from pathlib import Path


def _shared_root() -> Path:
    env = os.environ.get("SCALE_SHARED_PATH")
    for base in ([Path(env)] if env else []) + list(Path(__file__).resolve().parents):
        if (base / "shared" / "mock_llm").is_dir():
            return base
    raise ImportError(
        "Cannot find the shared/ mock library. Keep this folder inside scale-backend-sets/, "
        "or set SCALE_SHARED_PATH to the directory that contains shared/."
    )


_root = str(_shared_root())
if _root not in sys.path:
    sys.path.append(_root)
