"""35. FastAPI CRUD: Projects

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, StringConstraints
from kit import RealClock

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Priority = Annotated[int, Field(ge=1, le=5)]
Tags = Annotated[list[str], Field(max_length=10)]


class ProjectCreate(BaseModel):
    name: Name
    priority: Priority = 3
    tags: Tags = Field(default_factory=list)


class ProjectPatch(BaseModel):
    name: Optional[Name] = None
    priority: Optional[Priority] = None
    tags: Optional[Tags] = None


class Project(BaseModel):
    id: int
    name: str
    priority: int
    tags: list[str]
    created_at: str


class ProjectPage(BaseModel):
    items: list[Project]
    total: int


def create_app(clock=None) -> FastAPI:
    clock = clock or RealClock()
    app = FastAPI(title="Projects")
    projects: dict[int, Project] = {}  # per-app store, so every create_app() starts empty
    next_id = 1

    @app.post("/projects", status_code=201, response_model=Project)
    def create_project(body: ProjectCreate) -> Project:
        raise NotImplementedError

    @app.get("/projects", response_model=ProjectPage)
    def list_projects(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        tag: Optional[str] = None,
    ) -> ProjectPage:
        raise NotImplementedError

    @app.get("/projects/{project_id}", response_model=Project)
    def get_project(project_id: int) -> Project:
        raise NotImplementedError

    @app.patch("/projects/{project_id}", response_model=Project)
    def update_project(project_id: int, body: ProjectPatch) -> Project:
        raise NotImplementedError

    @app.delete("/projects/{project_id}", status_code=204)
    def delete_project(project_id: int) -> Response:
        raise NotImplementedError

    return app


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
    from fastapi.testclient import TestClient

    requests = [
        ("POST", "/projects", {"name": "  Street signs ", "tags": ["vision"]}),
        ("POST", "/projects", {"name": "STREET SIGNS"}),
        ("POST", "/projects", {"name": "", "priority": 9}),
        ("GET", "/projects/1", None),
        ("PATCH", "/projects/1", {"priority": 5}),
        ("GET", "/projects?limit=10", None),
        ("DELETE", "/projects/1", None),
        ("GET", "/projects/1", None),
    ]
    client = TestClient(create_app())
    for method, url, body in requests:
        resp = client.request(method, url, json=body)
        print(method, url, resp.status_code, resp.text[:120])
