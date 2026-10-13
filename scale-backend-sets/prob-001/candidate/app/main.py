"""Ticket triage service.

Run:    uvicorn app.main:app --reload
Tests:  python -m pytest

Keep the ``create_app`` signature: the interviewer's tests build the app with
their own storage directory, LLM client and clock.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException

from mock_services.clock import Clock, RealClock
from mock_services.llm import make_llm
import csv
import io
import re
from datetime import datetime
import uuid
import json
import random
from concurrent.futures import ThreadPoolExecutor
from shared.mock_llm import LLMError, LLMRateLimitError

REQUIRED_COLUMNS = ["ticket_id", "customer_email", "subject", "body", "created_at"]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

def _is_blank(row: list[str])->bool:
    if len(row)==0:
        return True
    if len(row)==1 and row[0].strip()=="":
        return True
    return False


def check_row(ticket, seen_ids):
    if not ticket["ticket_id"]:
        return "ticket_id", "ticket id is empty"
    if ticket["ticket_id"] in seen_ids:
        return "ticket_id", "duplicate id"
    
    if not re.match(EMAIL_PATTERN, ticket["customer_email"]):
        return "customer_email", "invalid email"
    
    if ticket["subject"] == "":
        return "subject", "subject is empty"
     
    if ticket["body"] == "":
        return "body", "body is empty"
    
    try:
        datetime.fromisoformat(ticket["created_at"].replace("Z","+00:00"))
    except ValueError:
        return "created_at","invalid date"

    return None
    



LABELS = ["billing","bug","account_access","feature_request","other"]
MAX_ATTEMPTS = 3

def build_prompt(ticket):
    return (
        "Classify support ticket " + ticket["ticket_id"] + ". "
        "Allowed labels: billing, bug, account_access, feature_request, other. "
        'Answer only with JSON like {"label": "billing", "confidence": 0.9}.\n'
        "<item>" + ticket["subject"] + "\n" + ticket["body"] + "</item>"
    )
    
def parse_llm_output(text):
    text = text.strip()
    
    if text.startswith("```"):
        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("output is not a JSON object")
    
    label = data.get("label")
    if not isinstance(label, str):
        raise ValueError("lable is not a string")
    
    label = label.strip().lower()
    if label not in LABELS:
        raise ValueError("unknown labels: "+ label)
    
    confidence = data.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int,float)):
        raise ValueError("confidence is not a number")
    
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence should be between 0 and 1")

    return label, float(confidence)


def create_app(
    storage_dir: Path | str = "storage",
    llm=None,
    clock: Clock | None = None,
    max_concurrency: int = 4,
) -> FastAPI:
    storage_dir = Path(storage_dir)
    llm = llm or make_llm()
    clock = clock or RealClock()

    app = FastAPI(title="Ticket triage")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}
    
    def wait_before_retry(attempt, error):
        if isinstance(error, LLMRateLimitError):
            clock.sleep(error.retry_after)
        else:
            d = min(8, 0.5*2**(attempt-1))
            clock.sleep(random.uniform(d/2, d))

    # TODO: implement the endpoints described in PART1.md.
    @app.post("/uploads", status_code=201)
    def upload(file: UploadFile = File(...)):
        filename = file.filename or ""
        if not filename.lower().endswith(".csv"):
            raise HTTPException(415, "file must be a csv")
        
        raw = file.file.read()
        
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeEncodeError:
            raise HTTPException(400, "file is not valid utf8")
        
        all_rows = list(csv.reader(io.StringIO(text)))
        
        rows =[]
        for row in all_rows:
            print(row)
            if not _is_blank(row):
                rows.append(row)
  
        if len(rows) ==0:
            raise HTTPException(400, "file is empty")
        
        header=[]
        for name in rows[0]:
            header.append(name.strip())
            
        for column in REQUIRED_COLUMNS:
            if column not in header:
                raise HTTPException(400, "missing column: "+ column)
        
        tickets = []
        errors =[]
        seen_ids = set()
        
        data_rows = rows[1:]
        
        for i in range(len(data_rows)):
            values = data_rows[i]
            row_number = i + 1 
            
            if len(values) != len(header):
                errors.append({"row": row_number, "field": None, "message": "wrong number of values"})
                continue
            
            ticket = {}
            for column in REQUIRED_COLUMNS:
                position = header.index(column)
                ticket[column] = values[position].strip()
            
            problem = check_row(ticket, seen_ids)
            if problem is not None:
                field, message = problem
                errors.append({"row": row_number, "field": field, "message": message})
                continue
            
            seen_ids.add(ticket["ticket_id"])
            tickets.append(ticket)
            
        upload_id = uuid.uuid4().hex
        result = {
            "upload_id": upload_id,
            "filename": filename,
            "total_rows": len(data_rows),
            "valid_rows": len(tickets),
            "invalid_rows": len(errors),
            "errors": errors
        }
        
        folder = storage_dir / "uploads"
        folder.mkdir(parents=True, exist_ok=True)
        
        saved = dict(result)
        saved["tickets"] = tickets
        with open(folder/(upload_id+".json"),'w', encoding="utf-8") as f:
            json.dump(saved, f)
            
        return result
        
                
    
    @app.get("/uploads/{upload_id}")
    def get_uploads(upload_id: str):
        path = storage_dir / "uploads" / (upload_id + ".json")
        if not upload_id.isalnum() or not path.exists():
            raise HTTPException(404, "upload not found")
        
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    
    def classify_ticket(ticket):
        prompt=build_prompt(ticket)
        error = None
        
        for attempt in range(1, MAX_ATTEMPTS+1):
            try:
                response = llm.complete(prompt, timeout=10)
                label, confidence = parse_llm_output(response.text)
                # success
                return {
                        "ticket_id":ticket["ticket_id"],
                        "status":"classified",
                        "label": label,
                        "confidence": confidence,
                        "attempts": attempt, 
                        "error": None
                }
            except LLMError as e:
                error = type(e).__name__+": "+str(e)
                
                if not e.retryable:
                    return {
                        "ticket_id":ticket["ticket_id"],
                        "status":"failed",
                        "label": None,
                        "confidence": None,
                        "attempts": attempt, 
                        "error": error
                    }
                
                last_error = e
            except ValueError as e:
                error = "invalid output: " + str(e)
                last_error = e
            
            
            if attempt < MAX_ATTEMPTS:
                wait_before_retry(attempt, last_error)
        
        return {
                "ticket_id":ticket["ticket_id"],
                "status":"failed",
                "label": None,
                "confidence": None,
                "attempts": MAX_ATTEMPTS, 
                "error": error
        }

    
    @app.post("/uploads/{upload_id}/classify")
    def classify_upload(upload_id: str):
        path = storage_dir / "uploads" / (upload_id + ".json")
        if not upload_id.isalnum() or not path.exists():
            raise HTTPException(404, "upload not found")
        
        with open(path, encoding="utf-8") as f:
            upload = json.load(f)
        
        result_file = storage_dir / "classifications" / (upload_id + ".json")
        already_done = {}
        if result_file.exists():
            with open(result_file, encoding="utf-8") as f:
                previous = json.load(f)
            for r in previous["results"]:
                if r["status"] == "classified":
                    already_done[r["ticket_id"]] = r
                    
        
        todo = []
        for ticket in upload["tickets"]:
            if ticket["ticket_id"] not in already_done:
                todo.append(ticket)
        
        with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
            new_results = list(pool.map(classify_ticket, todo))
            
        new_by_id = {}
        for r in new_results:
            new_by_id[r["ticket_id"]] = r
        
        results = []
        for ticket in upload["tickets"]:
            tid = ticket["ticket_id"]
            if tid in already_done:
                results.append(already_done[tid])
            else:
                results.append(new_by_id[tid])
        
        classified = 0
        for r in results:
            if r["status"] == "classified":
                classified+=1
        
        response ={
            "upload_id": upload_id,
            "classified": classified,
            "failed": len(results) - classified,
            "results": results,
        }
        
        folder = storage_dir / "classifications"
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder/(upload_id+".json"),"w",encoding="utf-8") as f:
            json.dump(response, f)
        
        return response
    
    @app.get("/uploads/{upload_id}/classifications")
    def get_classifications(upload_id: str):
        upload_file = storage_dir / "uploads" / (upload_id + ".json")
        result_file = storage_dir / "classifications" / (upload_id + ".json")
        
        if not upload_id.isalnum() or not upload_file.exists():
            raise HTTPException(404, "upload not found")
        if not result_file.exists():
            raise HTTPException(404, "not classified yet")
        
        with open(result_file, encoding="utf-8") as f:
            return json.load(f)
    return app


app = create_app()
