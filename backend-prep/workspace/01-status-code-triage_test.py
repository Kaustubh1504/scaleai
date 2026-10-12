import pytest

def test_get_503_is_retryable_server(sol):
    assert sol.triage("GET", 503) == sol.Triage("server", True, "retry")
    
@pytest.mark.parametrize("status,action",[
    (400, "fix_request"),
    (401, "reauthenticate"),
    (403, "forbidden"),
    (404, "not_found"),
    (409, "conflict"),
    (422, "fix_payload"),
])
def test_specific_client_errors(sol, status, action):
    assert sol.triage("GET", status) == sol.Triage("client", False, action)

def test_post_5xx(sol):
    assert sol.triage("POST", 503) == sol.Triage("server", False,"give_up")
    assert sol.triage("POST", 503, True) == sol.Triage("server", True,"retry")
    assert sol.triage("post", 429) == sol.Triage("client", True,"back_off")
    
@pytest.mark.parametrize("status", [302, 100, 99, 600])
def test_invalid_status_raises(sol, status):
    with pytest.raises(ValueError):
        sol.triage("GET", status)
        
def test_case_sensitive(sol):
    assert sol.
    