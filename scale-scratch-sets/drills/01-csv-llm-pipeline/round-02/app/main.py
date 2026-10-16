from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import csv, io, os
import json, time
import httpx
from dotenv import load_dotenv
from openai import OpenAI
import hashlib
from concurrent.futures import ThreadPoolExecutor
import tempfile

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI()

CATEGORIES = ["data_labeling", "model_evaluation", "content_moderation", "transcription", "other"]
PROMPT = (
    "classify the given task in one of the following category: " + ",".join(CATEGORIES) +
    "the task is enclosed in <task></task>. give response in strict json format. reply with just one category"
)

class RequestBody(BaseModel):
    tasks_path: str
    users_path: str
    output_path: str

def safe_path(raw, root, ext):
    root =(Path.cwd() / root).resolve()
    path =(Path.cwd() / raw).resolve()

    if Path(raw).is_absolute() or not raw.endswith(ext) or not path.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Bad Path")
    
    return path

def read_csv(path, required):
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="not a valid utf-8")

    rows = []
    for row in csv.reader(io.StringIO(text, newline="")):
        temp = []
        for r in row:
            temp.append(r.strip())
        
        if "".join(temp)!="":
            rows.append(temp)
    
    header = rows[0]
    for r in required:
        if r not in header:
            raise HTTPException(status_code=400, detail=f"{r} is required")
    
    return header, rows[1:]

def parse(tasks_path, users_path, errors):
    def err(file, row, tid, error):
        errors.append({"file": file, "row": row, "id": tid, "error": error})

    header, rows = read_csv(users_path, ["user_id"])
    users = {}
    seen = set()
    for n, row in enumerate(rows):
        if len(row)!=len(header):
            err("users", n, None, "malformed_row")
            continue
        uid = row[header.index("user_id")]
        if not uid:
            err("users", n, None, "missing_user_id")
            continue
        if uid in seen:
            err("users", n, uid, "duplicate_user_id")
            continue

        seen.add(uid)
        users[uid]=dict(zip(header, row))

    header, rows = read_csv(tasks_path, ["task_id", "title", "description", "user_id", "priority"])
    tasks = []
    seen = set()

    for n, row in enumerate(rows):
        if len(row)!=len(header):
            err("tasks", n, None, "malformed_row")
            continue
        
        task = dict(zip(header, row))
        tid, uid = task["task_id"], task["user_id"]
        priority =int(task["priority"]) if task["priority"] in ("1","2","3") else None

        if not tid:
            err("task", n, None, "missing_task_id")
            continue
        if tid in seen:
            err("task", n, tid, "duplicate_task_id")
            continue
        
        if not priority:
           err("task", n, tid, "invalid_priority")

        task["user"] = users.get(uid)

        if not task["user"]:
            err("task", n, tid, "missing_user_id" if not uid else "invalid_user")
    
        seen.add(tid)
        tasks.append((n, task))
    
    return tasks

def llm_config():
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(503, "OPENAI_API_KEY not set")
    env = os.environ.get
    return {"key": env("OPENAI_API_KEY"), "model": env("OPENAI_MODEL", "gpt-4o-mini"),
            "url": env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
            "timeout": float(env("LLM_TIMEOUT", "10")), "backoff": float(env("LLM_BACKOFF_BASE", "0.5"))}

def call_llm(http, cfg, task):
    payload = {
            "model":cfg["model"],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            
            "messages":[{"role": "system", "content": PROMPT},
                                {"role": "user", "content": "<task>" + json.dumps(
                                    {"title": task["title"], "description": task["description"]}) + "</task>"}]   
        }
    
    for attempt in range(4):
        if attempt >=1:
            time.sleep(cfg["LLM_BACKOFF_BASE"]*2**(attempt-1))
        
        try:
            res = http.post(cfg["url"], json=payload, timeout=cfg["timeout"], headers={"Authorization": f"Bearer {cfg["key"]}"})
        except httpx.TransportError:
            continue
                
        if res.status_code == 429 or res.status_code >= 500:
            continue
        if res.status_code != 200:
            return None
        
        try:
            data = res.json()["choices"][0]["message"]["content"]
            category = json.loads(data).get("category")
            if category in CATEGORIES:
                return category
            else:
                return None
        except:
            return None
        
    return None

def add_classification(tasks, cfg, errors):
    ckpt = Path.cwd() / "output/.checkpoint/categories.json"
    done = json.loads(ckpt.read_text()) if ckpt.is_file() else {}
    
    def key(t):
        return hashlib.sha256(f"{cfg['model']}|{PROMPT}|{t['title']}|{t['description']}".encode()).hexdigest()

    todo = []
    for n,t in tasks:
        if key(t) not in done:
            todo.append((n, t))
        else:
            t["category"] = done[key(t)]
    
    with make_http_client() as http, ThreadPoolExecutor(max_workers=10) as pool:
        jobs = []
        for n, t in todo:
            job = pool.submit(call_llm, http, cfg, t)
            jobs.append((n, t, job))
        
        for n, t, job in jobs:
            cat = job.result()
            
            if cat:
                done[key(t)] = cat
            else:
                errors.append({"file": "tasks", "row": n, "id": t["task_id"], "error": "unclassified"})

            if n%50 == 0:
                atomic_write_json(ckpt,done)
                
    atomic_write_json(ckpt,done)

def atomic_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        os.remove(tmp)
        raise
    
def make_http_client():
    return httpx.Client()

@app.post("/convert")
def convert(req: RequestBody):
    tasks_path = safe_path(req.tasks_path, "data", ".csv")
    users_path = safe_path(req.users_path,"data", ".csv")
    output_path = safe_path(req.output_path, "output", ".json")

    for p in (tasks_path, users_path):
        if not p.is_file():
            raise HTTPException(status_code=400, detail="file not found")

    errors = []
    tasks = parse(tasks_path, users_path, errors)
    add_classification(tasks, llm_config(), errors)
    output = []
    for _, task in tasks:
        output.append(task)
    atomic_write_json(output_path, output)
    return {"rows_written": len(tasks), "errors": errors, "output": output}