# 08. Endpoint skeleton
# Standalone: copy this file as-is. Deps: stdlib + fastapi

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Req(BaseModel):
    input_path: str
    output_path: str


@app.post("/process")
def process(req: Req):                        # def, not async: blocking work runs in a thread pool
    # 1. config (503) -> 2. paths (400) -> 3. files exist (404) -> 4. parse (422) -> 5. work -> 6. write
    missing = [n for n in ("OPENAI_API_KEY",) if not os.environ.get(n)]
    if missing:
        raise HTTPException(503, f"missing config: {', '.join(missing)}")
    errors: list[dict] = []
    results: list[dict] = []
    # ... paste safe_path / read_csv / rows_by_id / ask_llm / atomic_write_json here ...
    return {"rows_written": len(results), "errors": errors}
