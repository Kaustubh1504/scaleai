"""Mock Support API for problem 05. Explore it through GET /openapi.json, not by reading this file."""

from __future__ import annotations

import random

from kit import MockAPI, error_response, paginate_cursor, paginate_pages

API_KEY = "sk_test_51d2"
AUTH_HEADER = "X-Support-Key"
TICKET_STATUSES = ("open", "pending", "solved", "closed")
PLANS = ("free", "team", "enterprise")
NAMES = ["Acme Labs", "Zeta AI", "Northwind", "Globex", "Initech", "Umbrella Robotics", "Hooli", "Stark Vision",
         "Wayne Data", "Tyrell Bio", "Cyberdyne", "Soylent Foods", "Vandelay Imports", "Pied Piper", "Aperture",
         "Black Mesa", "Wonka Labs", "Gringotts", "Oscorp", "Monarch Air"]


def make_data(n_customers: int, seed: int, *, top_ids: tuple[int, ...] = (), no_open: bool = False):
    """
    Each customer gets 0..4 open tickets and 0..5 others; about 1 in 5 has no tickets at all.
    top_ids : these customers all get (max of the rest + 2) open tickets, forcing the winner (or a tie).
    no_open : no ticket is open.
    """
    rng = random.Random(seed)
    customers = []
    for cid in range(1, n_customers + 1):
        name = f"{NAMES[(cid - 1) % len(NAMES)]}" + (f" {(cid - 1) // len(NAMES) + 1}" if cid > len(NAMES) else "")
        customers.append({"id": cid, "name": name, "plan": rng.choice(PLANS),
                          "created_at": f"2023-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T00:00:00Z"})

    open_counts: dict[int, int] = {}
    other_counts: dict[int, int] = {}
    for c in customers:
        if rng.random() < 0.2:
            open_counts[c["id"]], other_counts[c["id"]] = 0, 0
        else:
            open_counts[c["id"]] = 0 if no_open else rng.randint(0, 4)
            other_counts[c["id"]] = rng.randint(0, 5)
    if top_ids:
        best = max((n for cid, n in open_counts.items() if cid not in top_ids), default=0) + 2
        for cid in top_ids:
            open_counts[cid] = best

    tickets = []
    for c in customers:
        statuses = ["open"] * open_counts[c["id"]] + [rng.choice(TICKET_STATUSES[1:]) for _ in range(other_counts[c["id"]])]
        for status in statuses:
            tickets.append({"customer_id": c["id"], "status": status,
                            "priority": rng.choice(["low", "normal", "high", "urgent"]),
                            "subject": rng.choice(["Export stuck", "Wrong labels", "Invoice question",
                                                   "Need more annotators", "API 500s", "Reset SSO"])})
    rng.shuffle(tickets)
    for i, t in enumerate(tickets, start=1):
        t["id"] = f"tkt_{i:05d}"
        t["created_at"] = f"2024-03-{1 + i % 28:02d}T{i % 24:02d}:00:00Z"
    tickets = [{"id": t["id"], **{k: v for k, v in t.items() if k != "id"}} for t in tickets]
    return customers, tickets


def _schema_ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def _int_param(name: str, where: str, desc: str, *, default=None, minimum=None, maximum=None, required=False) -> dict:
    schema: dict = {"type": "integer"}
    for key, val in (("default", default), ("minimum", minimum), ("maximum", maximum)):
        if val is not None:
            schema[key] = val
    return {"name": name, "in": where, "required": required, "description": desc, "schema": schema}


def _errors() -> dict:
    return {"401": {"description": "Missing or invalid API key", "content": {"application/json": {"schema": _schema_ref("Error")}}},
            "400": {"description": "Invalid parameters", "content": {"application/json": {"schema": _schema_ref("Error")}}}}


OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "Helpdesk Support API", "version": "2.4.0",
             "description": "Customers and their support tickets. All /v1 endpoints require an API key."},
    "servers": [{"url": "https://api.example.test"}],
    "security": [{"SupportKey": []}],
    "paths": {
        "/health": {"get": {"summary": "Liveness probe", "security": [], "operationId": "health",
                            "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {
                                "type": "object", "properties": {"status": {"type": "string", "example": "ok"}}}}}}}}},
        "/v1/customers": {"get": {
            "summary": "List customers", "operationId": "listCustomers", "tags": ["customers"],
            "description": "Page-number pagination, ordered by id.",
            "parameters": [_int_param("page", "query", "1-based page number", default=1, minimum=1),
                           _int_param("per_page", "query", "Page size", default=10, minimum=1, maximum=25)],
            "responses": {"200": {"description": "A page of customers",
                                  "content": {"application/json": {"schema": _schema_ref("CustomerPage")}}}, **_errors()}}},
        "/v1/customers/{customer_id}": {"get": {
            "summary": "Get one customer", "operationId": "getCustomer", "tags": ["customers"],
            "parameters": [_int_param("customer_id", "path", "Customer id", required=True)],
            "responses": {"200": {"description": "The customer", "content": {"application/json": {"schema": _schema_ref("Customer")}}},
                          "404": {"description": "No such customer", "content": {"application/json": {"schema": _schema_ref("Error")}}},
                          **_errors()}}},
        "/v1/tickets": {
            "get": {
                "summary": "List tickets", "operationId": "listTickets", "tags": ["tickets"],
                "description": "Cursor pagination. Pass the previous response's next_cursor to get the next page; "
                               "next_cursor is null on the last page. Cursors are opaque.",
                "parameters": [
                    {"name": "status", "in": "query", "required": False, "description": "Only tickets with this status",
                     "schema": {"type": "string", "enum": list(TICKET_STATUSES)}},
                    _int_param("customer_id", "query", "Only tickets of this customer"),
                    _int_param("limit", "query", "Page size", default=20, minimum=1, maximum=50),
                    {"name": "cursor", "in": "query", "required": False, "description": "Opaque cursor from next_cursor",
                     "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "A page of tickets",
                                      "content": {"application/json": {"schema": _schema_ref("TicketPage")}}}, **_errors()}},
            "post": {
                "summary": "Open a ticket", "operationId": "createTicket", "tags": ["tickets"],
                "requestBody": {"required": True, "content": {"application/json": {"schema": _schema_ref("TicketCreate")}}},
                "responses": {"201": {"description": "Created", "content": {"application/json": {"schema": _schema_ref("Ticket")}}},
                              "422": {"description": "Validation error"}, **_errors()}},
        },
        "/v1/tickets/{ticket_id}": {"get": {
            "summary": "Get one ticket", "operationId": "getTicket", "tags": ["tickets"],
            "parameters": [{"name": "ticket_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "responses": {"200": {"description": "The ticket", "content": {"application/json": {"schema": _schema_ref("Ticket")}}},
                          "404": {"description": "No such ticket"}, **_errors()}}},
        "/v1/agents": {"get": {
            "summary": "List support agents", "operationId": "listAgents", "tags": ["agents"],
            "responses": {"200": {"description": "All agents", "content": {"application/json": {"schema": {
                "type": "array", "items": _schema_ref("Agent")}}}}, **_errors()}}},
        "/v1/legacy/tickets": {"get": {
            "summary": "List tickets (v1 legacy)", "operationId": "listTicketsLegacy", "tags": ["tickets"], "deprecated": True,
            "description": "Removed. Use GET /v1/tickets.",
            "responses": {"410": {"description": "Gone"}}}},
    },
    "components": {
        "securitySchemes": {"SupportKey": {"type": "apiKey", "in": "header", "name": AUTH_HEADER,
                                           "description": "Your API key, e.g. sk_test_..."}},
        "schemas": {
            "Error": {"type": "object", "properties": {"error": {"type": "string"}}},
            "Customer": {"type": "object", "required": ["id", "name"], "properties": {
                "id": {"type": "integer"}, "name": {"type": "string"},
                "plan": {"type": "string", "enum": list(PLANS)}, "created_at": {"type": "string", "format": "date-time"}}},
            "CustomerPage": {"type": "object", "properties": {
                "data": {"type": "array", "items": _schema_ref("Customer")}, "page": {"type": "integer"},
                "per_page": {"type": "integer"}, "total": {"type": "integer"}, "total_pages": {"type": "integer"}}},
            "Ticket": {"type": "object", "required": ["id", "customer_id", "status"], "properties": {
                "id": {"type": "string", "example": "tkt_00042"}, "customer_id": {"type": "integer"},
                "status": {"type": "string", "enum": list(TICKET_STATUSES)},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                "subject": {"type": "string"}, "created_at": {"type": "string", "format": "date-time"}}},
            "TicketCreate": {"type": "object", "required": ["customer_id", "subject"], "properties": {
                "customer_id": {"type": "integer"}, "subject": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]}}},
            "TicketPage": {"type": "object", "properties": {
                "results": {"type": "array", "items": _schema_ref("Ticket")},
                "next_cursor": {"type": "string", "nullable": True}}},
            "Agent": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"},
                                                       "open_assignments": {"type": "integer"}}},
        },
    },
}


def _int_arg(req, name: str, default: int, lo: int, hi: int | None):
    raw = req.params.get(name)
    if raw is None:
        return default, None
    try:
        value = int(raw)
    except ValueError:
        return None, error_response(400, f"{name} must be an integer, got {raw!r}")
    if value < lo or (hi is not None and value > hi):
        return None, error_response(400, f"{name} must be between {lo} and {hi}" if hi else f"{name} must be >= {lo}")
    return value, None


def make_api(seed: int = 0, n_customers: int = 23, *, top_ids: tuple[int, ...] = (), no_open: bool = False,
             clock=None) -> MockAPI:
    api = MockAPI(clock=clock)
    customers, tickets = make_data(n_customers, seed, top_ids=top_ids, no_open=no_open)
    api.customers, api.tickets = customers, tickets
    by_id = {c["id"]: c for c in customers}

    def authed(req) -> bool:
        return req.header(AUTH_HEADER) == API_KEY

    def unauthorized():
        return error_response(401, f"missing or invalid {AUTH_HEADER} header")

    @api.route("GET", "/openapi.json")
    def openapi(req):
        return OPENAPI

    @api.route("GET", "/health")
    def health(req):
        return {"status": "ok"}

    @api.route("GET", "/v1/customers")
    def list_customers(req):
        if not authed(req):
            return unauthorized()
        page, err = _int_arg(req, "page", 1, 1, None)
        if err:
            return err
        per_page, err = _int_arg(req, "per_page", 10, 1, 25)
        if err:
            return err
        return paginate_pages(customers, page, per_page)

    @api.route("GET", "/v1/customers/{customer_id}")
    def get_customer(req, customer_id):
        if not authed(req):
            return unauthorized()
        c = by_id.get(int(customer_id)) if customer_id.isdigit() else None
        return c if c is not None else error_response(404, f"customer {customer_id} not found")

    @api.route("GET", "/v1/tickets")
    def list_tickets(req):
        if not authed(req):
            return unauthorized()
        limit, err = _int_arg(req, "limit", 20, 1, 50)
        if err:
            return err
        rows = tickets
        status = req.params.get("status")
        if status is not None:
            if status not in TICKET_STATUSES:
                return error_response(400, f"status must be one of {list(TICKET_STATUSES)}")
            rows = [t for t in rows if t["status"] == status]
        if "customer_id" in req.params:
            cid, err = _int_arg(req, "customer_id", 0, 1, None)
            if err:
                return err
            rows = [t for t in rows if t["customer_id"] == cid]
        try:
            return paginate_cursor(rows, req.params.get("cursor") or None, limit)
        except ValueError:
            return error_response(400, "invalid cursor")

    @api.route("POST", "/v1/tickets")
    def create_ticket(req):
        if not authed(req):
            return unauthorized()
        return error_response(403, "this API key is read-only")

    @api.route("GET", "/v1/tickets/{ticket_id}")
    def get_ticket(req, ticket_id):
        if not authed(req):
            return unauthorized()
        t = next((t for t in tickets if t["id"] == ticket_id), None)
        return t if t is not None else error_response(404, f"ticket {ticket_id} not found")

    @api.route("GET", "/v1/agents")
    def agents(req):
        if not authed(req):
            return unauthorized()
        return [{"id": "agt_1", "name": "Sam", "open_assignments": 14}, {"id": "agt_2", "name": "Priya", "open_assignments": 9}]

    @api.route("GET", "/v1/legacy/tickets")
    def legacy(req):
        return error_response(410, "gone: use GET /v1/tickets")

    return api
