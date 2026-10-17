# 04. Validate a user-supplied path
# Standalone: copy this file as-is. Deps: stdlib + fastapi

from pathlib import Path

from fastapi import HTTPException


def safe_path(raw: str, root: str, ext: str) -> Path:
    """400 if absolute, wrong extension, or (after resolving .. and symlinks) outside root."""
    p = Path(raw)
    if not raw or p.is_absolute() or p.suffix != ext:
        raise HTTPException(400, f"bad path: {raw}")
    resolved = p.resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise HTTPException(400, f"bad path: {raw}")
    return resolved
