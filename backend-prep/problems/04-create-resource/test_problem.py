import pytest

from problem_api import TOKEN, make_api


def test_creates_project(sol):
    """A valid project returns the 201 body (with its new id)"""
    api = make_api()
    got = sol.create_project(api.client(), TOKEN, "Retail shelf boxes", tags=["vision", "retail"])
    assert got["id"] == "prj_003", f"return the server's created object, got {got}"
    assert got["name"] == "Retail shelf boxes" and got["tags"] == ["vision", "retail"]
    assert api.projects[-1]["id"] == "prj_003"
    assert len(api.log) == 1 and api.log[0].method == "POST" and api.log[0].path == "/v1/projects"


def test_sends_json_with_bearer_token(sol):
    """Sends Content-Type application/json and Authorization: Bearer <token>"""
    api = make_api()
    sol.create_project(api.client(), TOKEN, "Bearer check")
    call = api.log[0]
    assert (call.header("content-type") or "").startswith("application/json"), \
        f"send the body with json=, not data= (content-type was {call.header('content-type')!r})"
    assert call.header("authorization") == f"Bearer {TOKEN}"


def test_omits_none_fields(sol):
    """description and tags are left out of the body when they are None"""
    api = make_api()
    sol.create_project(api.client(), TOKEN, "Only a name")
    assert api.log[0].json() == {"name": "Only a name"}, f"body was {api.log[0].json()}"


def test_includes_given_fields(sol):
    """description and tags are sent when given (even an empty tags list)"""
    api = make_api()
    got = sol.create_project(api.client(), TOKEN, "Full", description="Chat transcripts", tags=[])
    assert api.log[0].json() == {"name": "Full", "description": "Chat transcripts", "tags": []}
    assert got["description"] == "Chat transcripts"


def test_validation_error_single_field(sol):
    """A 422 on an empty name raises ValidationFailed([{field: "name", message: ...}])"""
    api = make_api()
    with pytest.raises(sol.ValidationFailed) as exc:
        sol.create_project(api.client(), TOKEN, "")
    assert exc.value.errors == [{"field": "name", "message": "String should have at least 1 character"}]
    assert isinstance(exc.value, sol.ProjectApiError) and exc.value.status == 422


def test_validation_errors_keep_order_and_nested_paths(sol):
    """Several 422 errors are kept in order; ["body", "tags", 1] becomes "tags.1\""""
    api = make_api()
    with pytest.raises(sol.ValidationFailed) as exc:
        sol.create_project(api.client(), TOKEN, "x" * 81, description="d" * 501,
                           tags=["ok", "this-tag-is-way-too-long", ""])
    assert exc.value.errors == [
        {"field": "name", "message": "String should have at most 80 characters"},
        {"field": "description", "message": "String should have at most 500 characters"},
        {"field": "tags.1", "message": "String should have at most 20 characters"},
        {"field": "tags.2", "message": "String should have at least 1 character"},
    ]


def test_validation_loc_edge_cases(sol):
    """A loc of just ["body"] maps to field "" and a non-body loc keeps every part"""
    api = make_api()
    detail = [
        {"loc": ["body"], "msg": "Input should be a valid dictionary", "type": "model_attributes_type"},
        {"loc": ["query", "dry_run"], "msg": "Input should be a valid boolean", "type": "bool_parsing"},
    ]
    api.script("POST /v1/projects", [lambda call: (422, {"detail": detail})])
    with pytest.raises(sol.ValidationFailed) as exc:
        sol.create_project(api.client(), TOKEN, "anything")
    assert exc.value.errors == [
        {"field": "", "message": "Input should be a valid dictionary"},
        {"field": "query.dry_run", "message": "Input should be a valid boolean"},
    ]


def test_duplicate_raises_already_exists(sol):
    """A 409 raises AlreadyExists with existing_id from the body"""
    api = make_api()
    with pytest.raises(sol.AlreadyExists) as exc:
        sol.create_project(api.client(), TOKEN, "support chat RLHF")
    assert exc.value.existing_id == "prj_002"
    assert exc.value.status == 409 and isinstance(exc.value, sol.ProjectApiError)


def test_bad_token_raises_auth_error(sol):
    """A 401 raises AuthError"""
    api = make_api()
    with pytest.raises(sol.AuthError) as exc:
        sol.create_project(api.client(), "tok_expired", "Anything")
    assert exc.value.status == 401


def test_other_statuses_raise_base_error(sol):
    """A 500 or 415 raises plain ProjectApiError with that status"""
    api = make_api()
    api.script("POST /v1/projects", [500, lambda call: (415, {"detail": "Unsupported Media Type"})])
    for status in (500, 415):
        with pytest.raises(sol.ProjectApiError) as exc:
            sol.create_project(api.client(), TOKEN, f"Project {status}")
        assert exc.value.status == status
        assert type(exc.value) is sol.ProjectApiError, \
            f"a {status} is not an auth/validation/conflict error; raise the base ProjectApiError"
