"""35. FastAPI CRUD: Projects: reference solution."""

from datetime import datetime, timezone
from itertools import count
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints

from kit import RealClock

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Priority = Annotated[int, Field(ge=1, le=5)]
Tags = Annotated[list[str], Field(max_length=10)]


class ProjectCreate(BaseModel):
    name: Name
    priority: Priority = 3
    tags: Tags = []


class ProjectPatch(BaseModel):
    name: Name | None = None
    priority: Priority | None = None
    tags: Tags | None = None


def create_app(clock=None) -> FastAPI:
    clock = clock or RealClock()
    app = FastAPI()
    projects: dict[int, dict] = {}
    ids = count(1)

    def get_or_404(project_id: int) -> dict:
        if project_id not in projects:
            raise HTTPException(404, f"project {project_id} not found")
        return projects[project_id]

    def check_name(name: str, project_id: int | None = None) -> None:
        for p in projects.values():
            if p["id"] != project_id and p["name"].casefold() == name.casefold():
                raise HTTPException(409, f"a project named {p['name']!r} already exists")

    @app.post("/projects", status_code=201)
    def create_project(body: ProjectCreate) -> dict:
        check_name(body.name)
        pid = next(ids)
        created_at = datetime.fromtimestamp(clock.time(), timezone.utc).isoformat()
        projects[pid] = {"id": pid, **body.model_dump(), "created_at": created_at}
        return projects[pid]

    @app.get("/projects")
    def list_projects(
        limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), tag: str | None = None
    ) -> dict:
        matching = [p for p in projects.values() if tag is None or tag in p["tags"]]
        return {"items": matching[offset:offset + limit], "total": len(matching)}

    @app.get("/projects/{project_id}")
    def get_project(project_id: int) -> dict:
        return get_or_404(project_id)

    @app.patch("/projects/{project_id}")
    def update_project(project_id: int, body: ProjectPatch) -> dict:
        project = get_or_404(project_id)
        changes = body.model_dump(exclude_none=True)
        if "name" in changes:
            check_name(changes["name"], project_id)
        project.update(changes)
        return project

    @app.delete("/projects/{project_id}", status_code=204)
    def delete_project(project_id: int) -> None:
        get_or_404(project_id)
        del projects[project_id]

    return app


if __name__ == "__main__":
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    for method, url, body in [
        ("POST", "/projects", {"name": "  Street signs ", "tags": ["vision"]}),
        ("POST", "/projects", {"name": "STREET SIGNS"}),
        ("PATCH", "/projects/1", {"priority": 5}),
        ("GET", "/projects?limit=10", None),
        ("DELETE", "/projects/1", None),
        ("GET", "/projects/1", None),
    ]:
        resp = client.request(method, url, json=body)
        print(method, url, resp.status_code, resp.text[:120])
