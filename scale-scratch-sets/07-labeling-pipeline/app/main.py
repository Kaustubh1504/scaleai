from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import csv

app = FastAPI()

class RequestBody(BaseModel):
    tasks_path: str
    annotations_path: str
    output_path: str
    
def safe_path(raw, root, ext):
    root = (Path.cwd() / root).resolve()
    path = (Path.cwd() / raw).resolve()
    
    if not raw.endswith(ext) or not path.is_relative_to(root):
        raise HTTPException(status_code=400, detail="bad path")
    
    return path

def read_csv(path, required):
    rows = []
    
    with open(path,newline="", encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            temp = []
            for e in row:
                temp.append(e.strip())
            if "".join(temp)!="":
                rows.append(temp)   
    
    if not rows:
        raise HTTPException(status_code=422, detail="empty csv")
    
    header = rows[0]
    for r in required:
        if r not in header:
            raise HTTPException(status_code=422, detail="required header missing")
    return header, rows[1:]
    
def parse(tasks_path,annotations_path,errors):
    def err(file, row, id, error):
        errors.append({"file": file, "row": row, "id": id, "error": error})
        
    tasks_header, tasks = read_csv(tasks_path, ["task_id", "text"])
    
    annotations_header, annotations = read_csv(annotations_path, ["task_id", "annotator_id", "label"])
    
    seen_tasks = set()
    tasks_dict = {}
    
    for n, t in enumerate(tasks):
        if len(tasks_header)!=len(t):
            err("tasks", n, None, "malformed_row")
            continue
        tid = t[tasks_header.index("task_id")]
        
        if not tid:
            err("tasks", n, None, "missing_task_id")
            continue
        if tid in seen_tasks:
            err("tasks", n, tid, "duplicate_task_id")
            continue
        
        seen_tasks.add(tid)
        tasks_dict[tid] = dict(zip(tasks_header, tasks))
    
    annotations_dict = {}
    seen = dict()
    seen_tasks = set()
    for n, t in enumerate(annotations):
        if len(tasks_header)!=len(t):
            err("tasks", n, None, "malformed_row")
            continue
        tid = t[annotations_header.index("task_id")]
        
        if not tid:
            err("tasks", n, None, "missing_task_id")
            continue
        
        aid = t[annotations_header.index("annotator_id")]
        
        if not aid:
            err("tasks", n, None, "missing_annotator_id")
            continue
        
        if tid not in tasks_dict:
            err("tasks", n, None, "unkown_task")
        
        label = t[annotations_header.index("label")]
        
        if label not in ("safe", "spam", "harassment", "violence"):
            err("tasks", n, None, "invalid label")
            continue
        
        if tid in seen_tasks:
            err("tasks", n, tid, "duplicate_task_id")
            continue
        
    print(tasks_dict)
        
        
        
    return "ok"     
    
@app.post("/consensus")
def upload(req: RequestBody):
    tasks_path = safe_path(req.tasks_path, "data", ".csv")
    annotations_path = safe_path(req.annotations_path, "data", ".csv")
    output_path = safe_path(req.output_path, "output", ".json")
    errors = []
    parse(tasks_path, annotations_path, errors)
    
    return "ok"
    