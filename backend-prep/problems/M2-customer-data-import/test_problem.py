import json
import os
from pathlib import Path

import pytest

from problem_api import API_KEY, SAMPLE_CSV, company, lookups, make_api

HEADER = "customer_id,name,email,company_domain,seats,updated_at"


def csv_bytes(*lines: str, bom: bool = False, eol: str = "\n") -> bytes:
    return (("﻿" if bom else "") + eol.join(lines) + eol).encode("utf-8")


def reasons(result):
    return [(e["line"], e["reason"]) for e in result.errors]


def ids(rows):
    return [r["customer_id"] for r in rows]


def write_csv(tmp_path, lines) -> Path:
    path = tmp_path / "upload.csv"
    path.write_bytes(csv_bytes(*lines))
    return path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ------------------------------------------------------------------ part 1


def test_part1_sample_file(sol):
    """The sample upload: BOM, ';' delimiter, aliased headers -> the exact good rows and errors"""
    result = sol.clean_customers(SAMPLE_CSV.read_bytes())
    assert ids(result.rows) == ["C002", "C003", "C001", "C007", "C009"], "rows are in order of the kept row's line"
    assert result.rows[2] == {"customer_id": "C001", "name": "Ada Lovelace", "email": "ada@acme.io",
                              "domain": "acme.io", "seats": 30, "updated_at": "2024-04-15"}
    assert reasons(result) == [(2, "duplicate"), (5, "invalid_seats"), (6, "missing_customer_id"),
                               (7, "invalid_email"), (10, "invalid_updated_at"), (12, "too_many_fields")]
    assert result.errors[2]["customer_id"] is None and result.errors[1]["customer_id"] == "C004"


def test_part1_delimiter_detection(sol):
    """Detects tab, pipe and comma (with quoted commas and CRLF line endings)"""
    for delim in ("\t", "|"):
        raw = csv_bytes(HEADER.replace(",", delim), delim.join(["C1", "Ann", "a@x.io", "", "2", "2024-01-01"]))
        assert ids(sol.clean_customers(raw).rows) == ["C1"], f"delimiter {delim!r} not detected"
    raw = csv_bytes(HEADER, 'C1,"Lovelace, Ada",a@x.io,,2,2024-01-01', 'C2,Bo,b@x.io,,,2024-01-02', eol="\r\n")
    rows = sol.clean_customers(raw).rows
    assert [r["name"] for r in rows] == ["Lovelace, Ada", "Bo"], "quoted fields may contain the delimiter"


def test_part1_header_normalisation_and_aliases(sol):
    """Headers are normalised and aliased; unknown columns ignored; first duplicate header wins; optional ones may be absent"""
    raw = csv_bytes("  Cust-ID ,Email Address,Mail,Last  Updated,Favourite Colour",
                    "C1, A@X.IO ,ignored@y.io,2024-01-01,blue")
    result = sol.clean_customers(raw)
    assert result.errors == []
    assert result.rows == [{"customer_id": "C1", "name": None, "email": "a@x.io", "domain": "x.io",
                            "seats": None, "updated_at": "2024-01-01"}]


def test_part1_missing_required_column(sol):
    """A file without a required column (here updated_at) raises SchemaError"""
    with pytest.raises(sol.SchemaError):
        sol.clean_customers(csv_bytes("customer_id,name,email", "C1,Ann,a@x.io"))
    assert issubclass(sol.SchemaError, ValueError)


def test_part1_ragged_rows(sol):
    """Short rows are padded; empty extra fields are fine; non-empty extras -> too_many_fields"""
    raw = csv_bytes(HEADER,
                    "C1,Ann,a@x.io,,1,2024-01-01,,,",
                    "C2,Bo,b@x.io,,2,2024-01-01,oops",
                    "C3,Cy,c@x.io")                     # short: updated_at missing
    result = sol.clean_customers(raw)
    assert ids(result.rows) == ["C1"]
    assert reasons(result) == [(3, "too_many_fields"), (4, "invalid_updated_at")]


def test_part1_validation_order_and_values(sol):
    """Each check yields its reason and only the first failing check is reported"""
    raw = csv_bytes(HEADER,
                    ",Ann,not-an-email,,x,2024-01-01",    # missing id beats invalid email/seats
                    "C2,Bo,bo@x,,1,2024-01-01",            # no dot in the domain part
                    "C3,Cy,c@x.io,,x,2024-02-30",          # date before seats
                    "C4,Di,d@x.io,,-1,2024-02-03",
                    "C5,Ed,e@x.io,,1.0,2024/02/03",
                    "C6,Fi,f@x.io,,12,2024-02-29")         # 2024 is a leap year: valid
    result = sol.clean_customers(raw)
    assert reasons(result) == [(2, "missing_customer_id"), (3, "invalid_email"), (4, "invalid_updated_at"),
                               (5, "invalid_seats"), (6, "invalid_updated_at")]
    assert result.rows[0]["seats"] == 12 and type(result.rows[0]["seats"]) is int


def test_part1_duplicates(sol):
    """Duplicates: latest updated_at wins (whatever the order), a tie keeps the later line; losers are errors"""
    raw = csv_bytes(HEADER,
                    "A,new,a@x.io,,3,2024-03-01",
                    "B,first,b@x.io,,1,2024-01-01",
                    "A,old,a@x.io,,1,2024-01-01",
                    "B,second,b@x.io,,2,2024-01-01",
                    "C,only,c@x.io,,2,2024-01-01")
    result = sol.clean_customers(raw)
    assert [(r["customer_id"], r["name"]) for r in result.rows] == [("A", "new"), ("B", "second"), ("C", "only")]
    assert result.errors == [{"line": 3, "reason": "duplicate", "customer_id": "B"},
                             {"line": 4, "reason": "duplicate", "customer_id": "A"}]


def test_part1_value_normalisation(sol):
    """Emails lowercased, names collapsed, domains normalised or taken from the email; blank lines skipped but counted"""
    raw = csv_bytes(HEADER,
                    "C1,  Ada   King  ,ADA@Example.COM,https://www.Acme.io/about,,2024-01-01",
                    "",
                    "  ,  , , , , ",
                    "C2,Bo,bo@Sub.Example.org,  ,,2024-01-01",
                    "C3,Cy,cy@x.io,http://WWW.beta.dev,,2024-01-01",
                    "C4,Di,di@x.io,,,2024-13-01", bom=True)
    result = sol.clean_customers(raw)
    assert [(r["name"], r["email"], r["domain"]) for r in result.rows] == [
        ("Ada King", "ada@example.com", "acme.io"), ("Bo", "bo@sub.example.org", "sub.example.org"),
        ("Cy", "cy@x.io", "beta.dev")]
    assert reasons(result) == [(7, "invalid_updated_at")], "blank lines still count for line numbers"


# ------------------------------------------------------------------ part 2


def row(cid, domain, email=None):
    return {"customer_id": cid, "name": cid, "email": email or f"{cid.lower()}@{domain}", "domain": domain,
            "seats": None, "updated_at": "2024-01-01"}


def test_part2_enriches_rows(sol, clock):
    """Adds company_name/industry/employees and enrichment; 404 -> not_found; new dicts, same order"""
    api = make_api({"acme.io": company("Acme", "Manufacturing", 1200)})
    rows = [row("C1", "acme.io"), row("C2", "ghost.example")]
    before = [dict(r) for r in rows]
    out = sol.enrich_rows(rows, api.client(), API_KEY, sol.CompanyCache(clock))
    assert out == [{**rows[0], "company_name": "Acme", "industry": "Manufacturing", "employees": 1200,
                    "enrichment": "enriched"},
                   {**rows[1], "company_name": None, "industry": None, "employees": None,
                    "enrichment": "not_found"}]
    assert rows == before, "input rows must not be modified"
    assert all(c.header("x-api-key") == API_KEY for c in api.log)


def test_part2_free_mail_skipped(sol, clock):
    """Free-mail domains are skipped without any request"""
    api = make_api({})
    out = sol.enrich_rows([row("C1", "gmail.com"), row("C2", "icloud.com")], api.client(), API_KEY,
                          sol.CompanyCache(clock))
    assert [r["enrichment"] for r in out] == ["skipped", "skipped"]
    assert out[0]["company_name"] is None
    assert api.log == [], "no lookups for free-mail domains"


def test_part2_one_request_per_domain(sol, clock):
    """Rows sharing a domain (found or 404) cause one request each"""
    api = make_api({"acme.io": company("Acme")})
    rows = [row("C1", "acme.io"), row("C2", "ghost.example"), row("C3", "acme.io"), row("C4", "ghost.example")]
    out = sol.enrich_rows(rows, api.client(), API_KEY, sol.CompanyCache(clock))
    assert lookups(api) == ["acme.io", "ghost.example"]
    assert [r["enrichment"] for r in out] == ["enriched", "not_found", "enriched", "not_found"]


def test_part2_positive_ttl(sol, clock):
    """A found company is cached for ttl_s: no request at 299 s, a new request at exactly 300 s"""
    api = make_api({"acme.io": company("Acme")})
    cache = sol.CompanyCache(clock, ttl_s=300, negative_ttl_s=60)
    sol.enrich_rows([row("C1", "acme.io")], api.client(), API_KEY, cache)
    clock.advance(299)
    sol.enrich_rows([row("C1", "acme.io")], api.client(), API_KEY, cache)
    assert len(lookups(api)) == 1, "still fresh at 299 s"
    clock.advance(1)
    sol.enrich_rows([row("C1", "acme.io")], api.client(), API_KEY, cache)
    assert len(lookups(api)) == 2, "expired at exactly ttl_s"


def test_part2_negative_ttl(sol, clock):
    """A 404 is cached for negative_ttl_s only, while found companies stay cached"""
    api = make_api({"acme.io": company("Acme")})
    cache = sol.CompanyCache(clock, ttl_s=300, negative_ttl_s=60)
    rows = [row("C1", "acme.io"), row("C2", "ghost.example")]
    sol.enrich_rows(rows, api.client(), API_KEY, cache)
    clock.advance(59)
    sol.enrich_rows(rows, api.client(), API_KEY, cache)
    assert lookups(api) == ["acme.io", "ghost.example"]
    clock.advance(1)
    sol.enrich_rows(rows, api.client(), API_KEY, cache)
    assert lookups(api) == ["acme.io", "ghost.example", "ghost.example"]


def test_part2_cache_contract(sol, clock):
    """CompanyCache.get returns (hit, company); None is a cacheable 'not found' value"""
    cache = sol.CompanyCache(clock, ttl_s=10, negative_ttl_s=5)
    assert cache.get("a.io") == (False, None)
    cache.put("a.io", {"company_name": "A"})
    cache.put("b.io", None)
    assert cache.get("a.io") == (True, {"company_name": "A"})
    assert cache.get("b.io") == (True, None)
    clock.advance(5)
    assert cache.get("b.io") == (False, None) and cache.get("a.io")[0] is True


def test_part2_errors_raise_api_error(sol, clock):
    """A 500 raises ApiError(500, path); a bad key raises ApiError(401)"""
    api = make_api({"acme.io": company("Acme")})
    api.script("GET /v1/companies/acme.io", [500])
    with pytest.raises(sol.ApiError) as exc:
        sol.enrich_rows([row("C1", "acme.io")], api.client(), API_KEY, sol.CompanyCache(clock))
    assert (exc.value.status, exc.value.path) == (500, "/v1/companies/acme.io")
    with pytest.raises(sol.ApiError) as exc:
        sol.enrich_rows([row("C1", "acme.io")], api.client(), "bad-key", sol.CompanyCache(clock))
    assert exc.value.status == 401


# ------------------------------------------------------------------ part 3


def many(n=16, dup_every=4):
    lines = [HEADER]
    for i in range(n):
        lines.append(f"C{i:03d},N{i},u{i}@d{i:02d}.example,,1,2024-01-01")
        if i % dup_every == 0:
            lines.append(f"X{i:03d},M{i},v{i}@d{i:02d}.example,,1,2024-01-01")   # same domain again
    companies = {f"d{i:02d}.example": company(f"Co {i}", employees=i) for i in range(n)}
    return lines, companies


def test_part3_writes_outputs(sol, tmp_path):
    """Writes customers.jsonl, errors.jsonl and checkpoint.json (and nothing else) and returns the counts"""
    out = tmp_path / "out"
    summary = sol.run_import(SAMPLE_CSV, out, make_api().client(), API_KEY)
    assert summary == {"rows": 5, "errors": 6, "enriched": 3, "not_found": 1, "skipped": 1, "failed": 0}
    assert sorted(os.listdir(out)) == ["checkpoint.json", "customers.jsonl", "errors.jsonl"]
    rows = read_jsonl(out / "customers.jsonl")
    assert [(r["customer_id"], r["enrichment"]) for r in rows] == [
        ("C002", "enriched"), ("C003", "skipped"), ("C001", "enriched"), ("C007", "enriched"), ("C009", "not_found")]
    assert rows[2]["company_name"] == "Acme Corp" and rows[2]["seats"] == 30
    assert [e["reason"] for e in read_jsonl(out / "errors.jsonl")][:2] == ["duplicate", "invalid_seats"]
    ckpt = json.loads((out / "checkpoint.json").read_text())
    assert ckpt["unknown-co.example"] is None
    assert ckpt["acme.io"] == {"company_name": "Acme Corp", "industry": "Manufacturing", "employees": 1200}


def test_part3_concurrent_and_bounded(sol, tmp_path):
    """Lookups run concurrently, never more than max_workers at once, once per domain, output order kept"""
    lines, companies = many()
    api = make_api(companies, real_latency_s=0.02)
    sol.run_import(write_csv(tmp_path, lines), tmp_path / "out", api.client(), API_KEY, max_workers=4)
    assert 2 <= api.max_in_flight <= 4, f"max in flight was {api.max_in_flight}; expected concurrency capped at 4"
    assert sorted(lookups(api)) == sorted(companies), "each distinct domain exactly once"
    rows = read_jsonl(tmp_path / "out" / "customers.jsonl")
    assert ids(rows) == [line.split(",")[0] for line in lines[1:]], "output keeps the cleaned order"
    assert all(r["company_name"] == companies[r["domain"]]["name"] for r in rows)


def test_part3_partial_failures_are_reported(sol, tmp_path):
    """503, timeout and a malformed body mark those rows failed; the rest of the import completes"""
    lines, companies = many(n=8)
    api = make_api(companies)
    api.script("GET /v1/companies/d01.example", [503])
    api.script("GET /v1/companies/d02.example", ["timeout"])
    api.script("GET /v1/companies/d04.example", ["malformed"])   # d04 has two rows
    summary = sol.run_import(write_csv(tmp_path, lines), tmp_path / "out", api.client(), API_KEY, max_workers=3)
    assert summary["failed"] == 4 and summary["enriched"] == summary["rows"] - 4
    rows = read_jsonl(tmp_path / "out" / "customers.jsonl")
    failed = sorted({r["domain"] for r in rows if r["enrichment"] == "failed"})
    assert failed == ["d01.example", "d02.example", "d04.example"]
    assert all(r["company_name"] is None for r in rows if r["enrichment"] == "failed")


def test_part3_resume_only_retries_failures(sol, tmp_path):
    """A re-run requests only the domains that failed (or were never fetched) last time"""
    lines, companies = many(n=8)
    path = write_csv(tmp_path, lines)
    api = make_api(companies)
    del api.companies["d07.example"]                    # will 404 -> checkpointed as null
    api.script("GET /v1/companies/d03.example", [502])
    sol.run_import(path, tmp_path / "out", api.client(), API_KEY)
    api2 = make_api(companies)
    summary = sol.run_import(path, tmp_path / "out", api2.client(), API_KEY)
    assert lookups(api2) == ["d03.example"], "checkpointed domains (found or 404) must not be refetched"
    assert summary["failed"] == 0 and summary["not_found"] == 1


def test_part3_crash_then_resume(sol, tmp_path):
    """After a crash mid-run the checkpoint is valid JSON and the re-run skips everything checkpointed"""
    class Crash(BaseException):
        pass

    def crash(call):
        raise Crash("killed")

    lines, companies = many(n=10)
    path = write_csv(tmp_path, lines)
    api = make_api(companies)
    api.script("*", ["pass"] * 5 + [crash])
    with pytest.raises(Crash):
        sol.run_import(path, tmp_path / "out", api.client(), API_KEY, max_workers=1)
    ckpt = json.loads((tmp_path / "out" / "checkpoint.json").read_text())
    assert len(ckpt) >= 5, "the five lookups that finished before the crash must be checkpointed"
    api2 = make_api(companies)
    summary = sol.run_import(path, tmp_path / "out", api2.client(), API_KEY, max_workers=1)
    assert sorted(lookups(api2)) == sorted(set(companies) - set(ckpt))
    assert summary["enriched"] == summary["rows"]


def test_part3_writes_are_atomic(sol, tmp_path, monkeypatch):
    """Outputs go through os.replace; if the final replace fails, the previous file is left intact"""
    out = tmp_path / "out"
    out.mkdir()
    (out / "customers.jsonl").write_text("OLD\n")
    real_replace = os.replace
    replaced = []

    def recording(src, dst, *a, **kw):
        replaced.append(Path(dst).name)
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", recording)
    sol.run_import(SAMPLE_CSV, tmp_path / "ok", make_api().client(), API_KEY)
    assert {"customers.jsonl", "errors.jsonl", "checkpoint.json"} <= set(replaced), \
        "write a temp file in out_dir and os.replace it onto each final name"

    def failing(src, dst, *a, **kw):
        if Path(dst).name == "customers.jsonl":
            raise OSError("disk full")
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", failing)
    with pytest.raises(OSError):
        sol.run_import(SAMPLE_CSV, out, make_api().client(), API_KEY)
    assert (out / "customers.jsonl").read_text() == "OLD\n", "a failed write must not clobber the old output"
