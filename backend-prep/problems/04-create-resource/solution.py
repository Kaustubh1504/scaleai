"""04. Create a project (POST + error mapping): reference solution."""

from __future__ import annotations

import httpx


class ProjectApiError(Exception):
    def __init__(self, status: int, message: str = ""):
        super().__init__(f"{status}: {message}")
        self.status = status


class AuthError(ProjectApiError):
    def __init__(self, message: str = "not authenticated"):
        super().__init__(401, message)


class ValidationFailed(ProjectApiError):
    def __init__(self, errors: list[dict]):
        super().__init__(422, str(errors))
        self.errors = errors


class AlreadyExists(ProjectApiError):
    def __init__(self, existing_id: str, message: str = ""):
        super().__init__(409, message)
        self.existing_id = existing_id


def create_project(client: httpx.Client, token: str, name: str, *,
                   description: str | None = None, tags: list[str] | None = None) -> dict:
    body = {"name": name, "description": description, "tags": tags}
    resp = client.post("/v1/projects", json={k: v for k, v in body.items() if v is not None},
                       headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 201:
        return resp.json()
    if resp.status_code == 401:
        raise AuthError(resp.text)
    if resp.status_code == 409:
        raise AlreadyExists(resp.json()["existing_id"])
    if resp.status_code == 422:
        errors = []
        for e in resp.json()["detail"]:
            loc = e["loc"][1:] if e["loc"][:1] == ["body"] else e["loc"]
            errors.append({"field": ".".join(map(str, loc)), "message": e["msg"]})
        raise ValidationFailed(errors)
    raise ProjectApiError(resp.status_code, resp.text)


if __name__ == "__main__":
    from problem_api import TOKEN, make_api

    client = make_api().client()
    print(create_project(client, TOKEN, "Retail shelf boxes", tags=["vision"]))
    try:
        create_project(client, TOKEN, "", tags=["ok", "this-tag-is-way-too-long"])
    except ValidationFailed as exc:
        print("ValidationFailed:", exc.errors)
    try:
        create_project(client, TOKEN, "support chat rlhf")
    except AlreadyExists as exc:
        print("AlreadyExists:", exc.existing_id)
