"""40. Refactor a messy script. See the problem statement.

This script WORKS. It is also the kind of thing you inherit: one giant
function, prints for diagnostics, sys.exit deep inside, hard-coded URL / key /
timeouts, a bare except, pagination copy-pasted twice and magic numbers.

Refactor it into the public API the statement asks for (Config, load_config,
ApiError, ConfigError, ApiClient, Payout, compute_payouts, format_summary,
main). Keep the printed summary byte-for-byte identical.
"""

import sys

import httpx


def do_everything(client=None):
    if client is None:
        client = httpx.Client(base_url="https://api.example.test", timeout=10)
    key = "sk_live_payouts_42"

    # get annotators
    annotators = []
    page = 1
    while True:
        print("DEBUG fetching annotators page", page)
        r = client.get("/v1/annotators", params={"page": page, "per_page": 50},
                       headers={"Authorization": "Bearer " + key})
        if r.status_code != 200:
            print("ERROR: annotators request failed", r.status_code)
            sys.exit(1)
        try:
            body = r.json()
        except:
            print("ERROR: bad json")
            sys.exit(1)
        for a in body["data"]:
            annotators.append(a)
        if page >= body["total_pages"]:
            break
        page = page + 1

    # get submissions (same thing again)
    subs = []
    page = 1
    while True:
        print("DEBUG fetching submissions page", page)
        r = client.get("/v1/submissions", params={"page": page, "per_page": 50},
                       headers={"Authorization": "Bearer " + key})
        if r.status_code != 200:
            print("ERROR: submissions request failed", r.status_code)
            sys.exit(1)
        try:
            body = r.json()
        except:
            print("ERROR: bad json")
            sys.exit(1)
        for s in body["data"]:
            subs.append(s)
        if page >= body["total_pages"]:
            break
        page = page + 1

    # compute
    people = {}
    for a in annotators:
        if a["active"] == True:
            people[a["id"]] = a
    totals = {}
    for s in subs:
        if s["status"] != "accepted":
            continue
        if s["annotator_id"] not in people:
            continue
        if s["task_type"] == "bbox":
            c = 12
        elif s["task_type"] == "classify":
            c = 5
        elif s["task_type"] == "transcribe":
            c = 30
        else:
            print("WARNING unknown task type", s["task_type"], "on", s["id"])
            continue
        if s["annotator_id"] not in totals:
            totals[s["annotator_id"]] = [0, 0]
        totals[s["annotator_id"]][0] += 1
        totals[s["annotator_id"]][1] += c

    rows = []
    for aid in totals:
        n, cents = totals[aid]
        if people[aid]["level"] == "senior":
            cents = (cents * 125 + 50) // 100
        rows.append((aid, people[aid]["name"], n, cents))
    rows.sort(key=lambda x: (-x[3], x[0]))

    print("PAYOUT SUMMARY")
    grand = 0
    for aid, name, n, cents in rows:
        print("%s  %-20s %4d tasks  $%d.%02d" % (aid, name, n, cents // 100, cents % 100))
        grand += cents
    print("TOTAL $%d.%02d across %d annotators" % (grand // 100, grand % 100, len(rows)))


if __name__ == "__main__":
    # "Run" executes this block against the mock API. Note the DEBUG noise mixed into the output.
    from problem_api import make_api

    do_everything(make_api().client())
