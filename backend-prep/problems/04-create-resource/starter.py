"""04. Create a project (POST + error mapping)

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

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
        super().__init__(422, "; ".join(f"{e['field'] or '<body>'}: {e['message']}" for e in errors))
        self.errors = errors


class AlreadyExists(ProjectApiError):
    def __init__(self, existing_id: str, message: str = ""):
        super().__init__(409, message)
        self.existing_id = existing_id


def create_project(client: httpx.Client, token: str, name: str, *,
                   description: str | None = None, tags: list[str] | None = None) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import TOKEN, make_api

    api = make_api()
    client = api.client()
    print(create_project(client, TOKEN, "Retail shelf boxes", tags=["vision"]))
    for args, kwargs in [(("",), {"tags": ["ok", "this-tag-is-way-too-long"]}), (("support chat rlhf",), {})]:
        try:
            create_project(client, TOKEN, *args, **kwargs)
        except ValidationFailed as exc:
            print("ValidationFailed:", exc.errors)
        except AlreadyExists as exc:
            print("AlreadyExists:", exc.existing_id)
    try:
        create_project(client, "expired", "x")
    except AuthError as exc:
        print("AuthError:", exc)
