import csv
import json
from decimal import Decimal

from .models import Credit, Plan, Request, Tenant, Tier
from .timeparse import parse_month, parse_ts


def norm_id(value):
    return (value or "").strip().lower()


def to_cents(value):
    return int((Decimal(str(value).strip()) * 100).to_integral_value())


def parse_discount(value):
    text = (value or "").strip().rstrip("%").strip()
    return Decimal(text) if text else Decimal(0)


def parse_units(value):
    try:
        return int(value.strip())
    except ValueError:
        return 0


def load_plans(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        name.strip().lower(): Plan(
            name=name.strip().lower(),
            limit=int(spec["limit"]),
            window_s=int(spec["window_s"]),
            billed=bool(spec["billed"]),
            monthly_fee_cents=int(spec["monthly_fee_cents"]),
            included_units=int(spec["included_units"]),
            tiers=tuple(Tier(t["up_to_blocks"], int(t["cents_per_block"])) for t in spec["tiers"]),
        )
        for name, spec in raw.items()
    }


def load_tenants(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {
            norm_id(row["tenant_id"]): Tenant(
                tenant_id=norm_id(row["tenant_id"]),
                plan=norm_id(row["plan"]),
                rate_override=(row["rate_override"] or "").strip(),
                discount_pct=parse_discount(row["discount_pct"]),
            )
            for row in csv.DictReader(fh)
        }


def load_requests(path, tenants):
    requests, skipped = [], {"malformed": [], "unknown_tenant": []}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            request_id = row["request_id"].strip()
            tenant_id = norm_id(row["tenant_id"])
            if tenant_id not in tenants:
                skipped["unknown_tenant"].append(request_id)
                continue
            try:
                units = parse_units(row["units"] or "")
                ts = parse_ts(row["ts"])
            except ValueError:
                skipped["malformed"].append(request_id)
                continue
            requests.append(Request(request_id, tenant_id, ts, units))
    return requests, {k: sorted(v) for k, v in skipped.items()}


def load_credits(path):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return [
        Credit(row["credit_id"].strip(), norm_id(row["tenant_id"]), parse_month(row["month"]), to_cents(row["amount"]))
        for row in rows
    ]
