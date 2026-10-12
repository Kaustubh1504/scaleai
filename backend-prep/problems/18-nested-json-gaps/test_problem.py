import copy

import pytest

from problem_api import RECORDS

KEYS = {"id", "name", "email", "country", "city", "skills", "rating", "active"}


def test_get_path_dicts_and_lists(sol):
    """get_path follows dict keys and list indexes ("addresses.1.city")"""
    obj = {"user": {"addresses": [{"city": "Pune"}, {"city": "Austin"}], "n": 0}}
    assert sol.get_path(obj, "user.addresses.1.city") == "Austin"
    assert sol.get_path(obj, "user.addresses.0") == {"city": "Pune"}
    assert sol.get_path(obj, "user.n", "dflt") == 0, "a falsy value (0) is still a found value"


def test_get_path_never_raises(sol):
    """Missing keys, None in the middle, wrong types and bad indexes all return default"""
    obj = {"a": {"b": None, "s": "text", "n": 5, "lst": [1, 2]}}
    cases = ["x", "a.x", "a.b.c", "a.s.0", "a.n.x", "a.lst.2", "a.lst.-1", "a.lst.x", "a.lst.", "a..b"]
    for path in cases:
        assert sol.get_path(obj, path, "DEF") == "DEF", f"get_path(obj, {path!r}) should return default"
    assert sol.get_path(None, "a.b") is None
    assert sol.get_path([{"a": 1}], "0.a") == 1, "the root itself may be a list"


def test_get_path_edge_rules(sol):
    """Present-but-None returns None, "0" on a dict is a string key, "" returns obj"""
    assert sol.get_path({"a": None}, "a", "x") is None, "a key that exists with value None returns None"
    assert sol.get_path({"0": "zero"}, "0") == "zero", "on a dict, '0' is the string key '0'"
    obj = {"k": 1}
    assert sol.get_path(obj, "") is obj, "an empty path returns the object itself"


def test_v1_flat_record(sol):
    """A flat v1 record is cleaned: email lower-cased, country upper-cased, skills split"""
    assert sol.to_profile(RECORDS[0]) == {
        "id": "ann_001", "name": "Priya Raman", "email": "priya@example.com", "country": "IN",
        "city": "Pune", "skills": ["ner", "sentiment"], "rating": 4.8, "active": True,
    }


def test_v2_nested_record(sol):
    """A nested v2 record: int annotator_id, profile/contact/address/stats, status 'Active'"""
    assert sol.to_profile(RECORDS[1]) == {
        "id": "2", "name": "Diego Alvarez", "email": "diego@example.com", "country": "MX",
        "city": "Monterrey", "skills": ["audio", "ocr"], "rating": 4.1, "active": True,
    }


def test_blank_values_fall_through(sol):
    """"null", "", whitespace, None and unparseable values are skipped for the next source"""
    rec = {"id": "a1", "name": "  NULL ", "profile": {"full_name": "Ana Silva"},
           "email": "   ", "contact": {"email": "Ana@X.io"},
           "country": None, "address": {"country": ""}, "addresses": [{"country": " br ", "city": "Recife"}],
           "rating": "n/a", "stats": {"rating": "4"}}
    p = sol.to_profile(rec)
    assert p["name"] == "Ana Silva"
    assert p["email"] == "ana@x.io"
    assert p["country"] == "BR", "country should come from addresses.0.country, stripped and upper-cased"
    assert p["city"] == "Recife"
    assert p["rating"] == 4.0 and isinstance(p["rating"], float), "rating 'n/a' is blank, so stats.rating wins"


def test_split_name_and_v3(sol):
    """v3: name built from first_name + last_name; a null city stays None"""
    assert sol.to_profile(RECORDS[2]) == {
        "id": "ann_003", "name": "Mei Lin", "email": "mei@example.com", "country": "SG",
        "city": None, "skills": [], "rating": 3.0, "active": False,
    }
    only_last = {"id": "x", "profile": {"first_name": None, "last_name": "Okafor"}}
    assert sol.to_profile(only_last)["name"] == "Okafor", "join only the non-blank name parts"


def test_wrong_types_are_blank(sol):
    """Wrong-typed sources (number as name, bool rating, dict as skills) are skipped, not crashed on"""
    rec = {"id": "x", "name": 42, "profile": {"full_name": "Real Name", "skills": ["qa", 7, "  "]},
           "skills": {"a": 1}, "rating": True, "stats": {"rating": 2}, "email": ["a@b.c"]}
    p = sol.to_profile(rec)
    assert p["name"] == "Real Name"
    assert p["skills"] == ["qa"], "skills: keep string items only, drop blanks; a dict is blank"
    assert p["rating"] == 2.0, "True is not a rating"
    assert p["email"] is None


def test_skills_empty_falls_through(sol):
    """A skills value that leaves no items counts as blank (profile.skills is used)"""
    rec = {"id": "x", "skills": " , ,", "profile": {"skills": "rlhf,coding"}}
    assert sol.to_profile(rec)["skills"] == ["rlhf", "coding"]


def test_active_rules(sol):
    """active: bool or "true"/"false" string first, else status == "active", else False"""
    assert sol.to_profile({"id": "x", "active": "TRUE", "status": "suspended"})["active"] is True
    assert sol.to_profile({"id": "x", "active": False, "status": "active"})["active"] is False
    assert sol.to_profile({"id": "x", "active": "yes", "status": "ACTIVE"})["active"] is True, \
        "'yes' is not a valid active flag, so status decides"
    assert sol.to_profile({"id": "x", "status": "paused"})["active"] is False
    assert sol.to_profile({"id": "x"})["active"] is False


def test_sparse_record_and_shape(sol):
    """A nearly empty record gets None / [] / False defaults and exactly the 8 keys"""
    p = sol.to_profile(RECORDS[3])
    assert set(p) == KEYS, f"profile keys should be exactly {sorted(KEYS)}"
    assert p == {"id": "ann_004", "name": None, "email": None, "country": None, "city": None,
                 "skills": [], "rating": None, "active": False}


def test_missing_id_raises_and_no_mutation(sol):
    """No usable id raises ValueError; the input record is never mutated"""
    for rec in ({"name": "x"}, {"id": "null", "annotator_id": ""}, {"id": True}):
        with pytest.raises(ValueError):
            sol.to_profile(rec)
    before = copy.deepcopy(RECORDS)
    for rec in RECORDS:
        sol.to_profile(rec)
    assert RECORDS == before, "to_profile must not modify its input"
