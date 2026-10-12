"""Mock Org-chart API for problem 17. Tests and your __main__ block both use make_api().

The org data is messy on purpose: a child that points back at an ancestor (cycle),
a child listed twice, two parents sharing a child (diamond), and children that
were deleted (404).
"""

from __future__ import annotations

from kit import MockAPI, error_response


def org(org_id: str, parent: str | None, children: list[str], team_ids: list[str]) -> dict:
    return {"id": org_id, "name": org_id.removeprefix("org_").replace("_", " ").title(),
            "parent": parent, "children": children, "team_ids": team_ids}


ORGS: dict[str, dict] = {o["id"]: o for o in [
    org("org_holding", None, ["org_acme", "org_other"], ["t_board"]),
    org("org_other", "org_holding", [], ["t_other"]),
    org("org_acme", "org_holding", ["org_eng", "org_ops", "org_eng", "org_ghost"], ["t_exec"]),
    org("org_eng", "org_acme", ["org_ml", "org_platform"], ["t_backend", "t_frontend"]),
    org("org_ops", "org_acme", ["org_platform", "org_support"], ["t_ops"]),
    org("org_ml", "org_eng", ["org_research", "org_acme"], ["t_ml", "t_backend"]),
    org("org_platform", "org_eng", ["org_eng"], ["t_infra"]),
    org("org_support", "org_ops", ["org_vendor_gone"], ["t_support", "t_ops"]),
    org("org_research", "org_ml", [], ["t_research"]),
]}
# Not in ORGS (deleted, return 404): org_ghost, org_vendor_gone


def make_api(orgs: dict[str, dict] | None = None, clock=None) -> MockAPI:
    """GET /v1/orgs/{org_id} -> {"id", "name", "parent", "children", "team_ids"}, or 404.

    orgs: override the org graph (dict org_id -> org); defaults to ORGS.
    """
    api = MockAPI(clock=clock)
    data = ORGS if orgs is None else orgs
    api.orgs = data

    @api.route("GET", "/v1/orgs/{org_id}")
    def get_org(req, org_id):
        if org_id not in data:
            return error_response(404, f"org {org_id} not found")
        return data[org_id]

    return api
