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

def _field(loc: list) -> str:
    parts = loc[1:] if loc and loc[0] == "body" else loc
    return ".".join(str(p) for p in parts)

def create_project(client: httpx.Client, token: str, name: str, *,
                   description: str | None = None, tags: list[str] | None = None) -> dict:
    
#     if (name is None) or (name and (len(name)<1 or len(name)>80)):
#         raise ValueError("Invalid Name")
     
#     if description and len(description)>500:
#         raise ValueError("description <= 500 chars")
       
#     if tags:
#         if len(tags)>10:
#             raise ValueError("tags <= 10")
#         for t in tags:
#             if t and (len(t)<1 or len(t)>20):
#                 raise ValueError("tag len should be between 1 and 20")
            
        req ={
            "name": name
        }
        
        if description is not None: req["description"] = description
        if tags is not None: req["tags"] = tags
        
        
        res = client.post(url="/v1/projects",json=req, headers={"Authorization": f"Bearer {token}"})
        
        if res.status_code == 201:
            return res.json()
        if res.status_code == 401:
            raise AuthError(res.text[:200])
        if res.status_code == 409:
            raise AlreadyExists(existing_id=res.json()['existing_id'])
        if res.status_code == 422:
            errors = [{"field": _field(e["loc"]), "message": e["msg"]} for e in res.json()["detail"]]
            raise ValidationFailed(errors)
        
        raise ProjectApiError(res.status_code, res.text[:200])


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
