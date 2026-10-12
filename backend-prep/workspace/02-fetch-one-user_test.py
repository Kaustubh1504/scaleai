import pytest
import httpx

from problem_api import USERS, make_api, recording_client

def setup():
    api = make_api()
    return api, recording_client(api)

def test_invalid_user_id(sol):
    asset sol.get_user("a/b") == ValueError()
    
    
    