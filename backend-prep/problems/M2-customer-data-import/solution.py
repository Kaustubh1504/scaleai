"""M2. Customer data import: reference solution."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import httpx

ALIASES = {
    "customer_id": ("customer_id", "id", "customer", "cust_id"),
    "name": ("name", "full_name", "customer_name"),
    "email": ("email", "e_mail", "email_address", "mail"),
    "company_domain": ("company_domain", "domain", "website", "company_website"),
    "seats": ("seats", "seat_count", "licenses"),
    "updated_at": ("updated_at", "last_updated", "updated", "modified"),
}
FIELD_FOR = {alias: name for name, aliases in ALIASES.items() for alias in aliases}
FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"}
NO_COMPANY = {"company_name": None, "industry": None, "employees": None}


class SchemaError(ValueError):
    pass


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


@dataclass
class CleanResult:
    rows: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


# ------------------------------------------------------------------ part 1


def is_date(s: str) -> bool:
    try:
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)) and bool(date.fromisoformat(s))
    except ValueError:
        return False


def clean_customers(raw: bytes) -> CleanResult:
    text = raw.decode("utf-8-sig")
    first = text.splitlines()[0] if text else ""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=max(",;\t|", key=first.count))
    header = next(reader, None)
    if header is None:
        raise SchemaError("empty file")
    cols: dict[str, int] = {}
    for i, h in enumerate(header):
        name = FIELD_FOR.get(re.sub(r"[^a-z0-9]+", "_", h.strip().lower()).strip("_"))
        if name:
            cols.setdefault(name, i)
    missing = [c for c in ("customer_id", "email", "updated_at") if c not in cols]
    if missing:
        raise SchemaError(f"missing required columns: {missing}")

    kept: dict[str, tuple[int, dict]] = {}
    errors = []
    while True:
        line = reader.line_num + 1
        fields = next(reader, None)
        if fields is None:
            break
        if not any(f.strip() for f in fields):
            continue
        padded = fields + [""] * (len(header) - len(fields))
        cid, name, email, domain, seats, updated = (
            padded[cols[c]].strip() if c in cols else "" for c in ALIASES)
        email = email.lower()
        if any(f.strip() for f in fields[len(header):]):
            reason = "too_many_fields"
        elif not cid:
            reason = "missing_customer_id"
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            reason = "invalid_email"
        elif not is_date(updated):
            reason = "invalid_updated_at"
        elif seats and not (seats.isascii() and seats.isdigit()):
            reason = "invalid_seats"
        else:
            reason = None
        if reason:
            errors.append({"line": line, "reason": reason, "customer_id": cid or None})
            continue
        domain = domain.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.")
        row = {
            "customer_id": cid,
            "name": " ".join(name.split()) or None,
            "email": email,
            "domain": domain.split("/")[0] or email.rsplit("@", 1)[1],
            "seats": int(seats) if seats else None,
            "updated_at": updated,
        }
        if cid in kept:
            prev_line, prev = kept[cid]
            if updated >= prev["updated_at"]:  # ISO dates compare as strings; ties go to the later row
                kept[cid] = (line, row)
                line = prev_line
            errors.append({"line": line, "reason": "duplicate", "customer_id": cid})
        else:
            kept[cid] = (line, row)

    rows = [row for _, row in sorted(kept.values(), key=lambda lr: lr[0])]
    return CleanResult(rows=rows, errors=sorted(errors, key=lambda e: e["line"]))


# ------------------------------------------------------------------ part 2


class CompanyCache:
    def __init__(self, clock: Any, ttl_s: float = 300.0, negative_ttl_s: float = 60.0):
        self.clock = clock
        self.ttl_s = ttl_s
        self.negative_ttl_s = negative_ttl_s
        self.entries: dict[str, tuple[float, dict | None]] = {}

    def get(self, domain: str) -> tuple[bool, dict | None]:
        if domain in self.entries:
            stored_at, company = self.entries[domain]
            ttl = self.ttl_s if company is not None else self.negative_ttl_s
            if self.clock.time() < stored_at + ttl:
                return True, company
        return False, None

    def put(self, domain: str, company: dict | None) -> None:
        self.entries[domain] = (self.clock.time(), company)


def lookup_company(http: httpx.Client, api_key: str, domain: str) -> dict | None:
    path = f"/v1/companies/{domain}"
    resp = http.get(path, headers={"X-API-Key": api_key})
    if resp.status_code == 404:
        return None
    if not resp.is_success:
        raise ApiError(resp.status_code, path, resp.text[:200])
    try:
        body = resp.json()
    except ValueError as exc:
        raise ApiError(resp.status_code, path, "body is not valid JSON") from exc
    return {"company_name": body.get("name"), "industry": body.get("industry"),
            "employees": body.get("employee_count")}


def enrich_rows(rows: list[dict], http: httpx.Client, api_key: str, cache: CompanyCache) -> list[dict]:
    out = []
    for row in rows:
        domain, company = row["domain"], None
        if domain in FREE_EMAIL_DOMAINS:
            status = "skipped"
        else:
            hit, company = cache.get(domain)
            if not hit:
                company = lookup_company(http, api_key, domain)
                cache.put(domain, company)
            status = "enriched" if company else "not_found"
        out.append({**row, **(company or NO_COMPANY), "enrichment": status})
    return out


# ------------------------------------------------------------------ part 3


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def run_import(csv_path: str | Path, out_dir: str | Path, http: httpx.Client, api_key: str, *,
               max_workers: int = 4) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cleaned = clean_customers(Path(csv_path).read_bytes())
    ckpt = out / "checkpoint.json"
    done = json.loads(ckpt.read_text()) if ckpt.exists() else {}
    todo = [d for d in dict.fromkeys(r["domain"] for r in cleaned.rows)
            if d not in FREE_EMAIL_DOMAINS and d not in done]
    lock = threading.Lock()

    def fetch(domain: str) -> None:
        try:
            company = lookup_company(http, api_key, domain)
        except (ApiError, httpx.TransportError):
            return  # not checkpointed: retried on the next run
        with lock:
            done[domain] = company
            atomic_write(ckpt, json.dumps(done, sort_keys=True))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(fetch, todo))

    rows = []
    for row in cleaned.rows:
        d = row["domain"]
        status = ("skipped" if d in FREE_EMAIL_DOMAINS else "failed" if d not in done
                  else "enriched" if done[d] else "not_found")
        rows.append({**row, **(done.get(d) or NO_COMPANY), "enrichment": status})
    for name, records in (("customers.jsonl", rows), ("errors.jsonl", cleaned.errors)):
        atomic_write(out / name, "".join(json.dumps(r) + "\n" for r in records))
    counts = {s: sum(r["enrichment"] == s for r in rows)
              for s in ("enriched", "not_found", "skipped", "failed")}
    return {"rows": len(rows), "errors": len(cleaned.errors), **counts}


if __name__ == "__main__":
    import tempfile

    from kit import FakeClock
    from problem_api import API_KEY, SAMPLE_CSV, make_api

    result = clean_customers(SAMPLE_CSV.read_bytes())
    print(result)
    print(enrich_rows(result.rows, make_api().client(), API_KEY, CompanyCache(FakeClock()))[0])
    with tempfile.TemporaryDirectory() as tmp:
        print(run_import(SAMPLE_CSV, tmp, make_api().client(), API_KEY), sorted(os.listdir(tmp)))
