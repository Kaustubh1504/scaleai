# 46. Validate a file upload (size, type, encoding)
# Standalone: copy this file as-is. Deps: stdlib + fastapi

from pathlib import Path

from fastapi import HTTPException, UploadFile


async def read_upload(file: UploadFile, max_bytes: int = 5_000_000, extensions=(".csv",)) -> str:
    """415 wrong extension, 413 too large, 422 empty or not UTF-8. Returns the decoded text (BOM stripped).
    Reads at most max_bytes + 1, so a huge upload is never fully loaded."""
    if not file.filename or Path(file.filename).suffix.lower() not in extensions:
        raise HTTPException(415, f"expected one of {', '.join(extensions)}")
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"file larger than {max_bytes} bytes")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "file is not valid UTF-8") from None
    if not text.strip():
        raise HTTPException(422, "file is empty")
    return text
