from fastapi import FastAPI, File, UploadFile
import csv
from pydantic import BaseModel
from fastapi import HTTPException
from pathlib import Path

app = FastAPI()

class RequestBody(BaseModel):
    tasks_path: str
    users_path: str
    output_path: str
    

ROOT_DIR = Path("/Users/kaustubh/Desktop/scaleai/scale-scratch-sets/01-csv-llm-pipeline").resolve()

@app.get("/")
def welcome():
    return "hello"

# {"tasks_path": "data/tasks.csv", "users_path": "data/users.csv", "output_path": "output/tasks.json"}

REQUIRED = ["task_id", "title", "description", "user_id", "priority"]

@app.post("/csv2json")
def csv2json(req: RequestBody):
    tasks_path = req.tasks_path
    users_path = req.users_path
    output_path = req.output_path
    
    print(tasks_path,users_path,output_path)
    
    if not tasks_path.endswith(".csv"):
        raise HTTPException(422, detail="task path should end with .csv", headers=None)
    
    if not users_path.endswith(".csv"):
        raise HTTPException(422, detail="user path should end with .csv", headers=None)
    
    if not output_path.endswith(".json"):
        raise HTTPException(422, detail="output path should end with .json", headers=None)
    
    if not Path(tasks_path).exists():
        raise HTTPException(422, detail="invalid task path", headers=None)
    
    if not Path(users_path).exists():
        raise HTTPException(422, detail="invalid user path", headers=None)
    
    
    unsafe_path_tasks = ROOT_DIR / tasks_path
    
    try:
        safe_path = unsafe_path_tasks.resolve()
    except Exception:
        raise HTTPException(
            status_code=422, 
            detail="Invalid path structure."
        )
        
    
    if not safe_path.is_relative_to(ROOT_DIR):
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Path is outside the root directory."
        )
        
        
    
    unsafe_path_users = ROOT_DIR / users_path
        
    try:
        safe_path = unsafe_path_users.resolve()
    except Exception:
        raise HTTPException(
            status_code=422, 
            detail="Invalid path structure."
        )
        
    
    if not safe_path.is_relative_to(ROOT_DIR):
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Path is outside the root directory."
        )
        
    unsafe_path_output = ROOT_DIR / output_path
            
    try:
        safe_path = unsafe_path_users.resolve()
    except Exception:
        raise HTTPException(
            status_code=422, 
            detail="Invalid path structure."
        )
         
    Path(output_path).mkdir(parents=True, exist_ok=True)
    
    
    tasks = []
    tasks_header = []
    with open(tasks_path, mode='r', encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            cleaned_row = {}
            for key, value in row.items():
                if not isinstance(key, str):
                    continue
                if not isinstance(value, str):
                    continue
                
                cleaned_row[key.strip()] = value.strip()
            tasks.append(cleaned_row)
    print(tasks)

    users = []
    users_header = []
    with open(users_path, mode='r', encoding='utf-8-sig', newline='') as file:
        reader = csv.reader(file)
        for i, row in enumerate(reader):
            if i==0: users_header.append(r.strip() for r in row)
            else: users.append(row)
            
    print(tasks_header, users_header)
    
            
    return tasks


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


