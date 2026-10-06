"""Part 2: messy wire values, unknown rewards, inactive annotators on hold."""

from conftest import (EVERYTHING, add_scenario, add_unknown_reward_scenario, assert_part1, assert_part2, build_api,
                      row_for, run)


def test_messy_report_matches_oracle(clock):
    api = build_api(clock, messy=True)
    assert_part2(api, run(api, clock))


def test_every_wire_variant_is_understood(clock):
    api = build_api(clock, messy=True)
    subs = api.rendered("submissions")
    stamps = [s["submitted_at"] for s in subs] + [r["created_at"] for r in api.rendered("reviews")]
    assert any(isinstance(v, int) and v > 10**11 for v in stamps)  # epoch ms
    assert any(isinstance(v, int) and v < 10**11 for v in stamps)  # epoch s
    assert any(isinstance(v, str) and v.endswith("+00:00") for v in stamps)
    assert any(isinstance(v, str) and v.endswith("Z") for v in stamps)
    assert any(isinstance(v, str) and v[-1].isdigit() and "+" not in v for v in stamps)  # naive
    rewards = [t.get("reward_cents", "absent") for t in api.rendered("tasks")]
    assert "absent" in rewards and None in rewards
    assert any(isinstance(r, str) and r.isdigit() for r in rewards)
    assert {type(a["is_active"]) for a in api.rendered("annotators")} == {bool, int, str}
    assert any(r["verdict"] != r["verdict"].strip().lower() for r in api.rendered("reviews"))
    report = run(api, clock, EVERYTHING)
    assert_part2(api, report, EVERYTHING)


def test_latest_review_rule_survives_mixed_timestamp_formats(clock):
    api = build_api(clock, messy=True)
    add_scenario(api)
    row = row_for(run(api, clock), "ann_900")
    assert (row["approved"], row["rejected"], row["pending"], row["earnings_cents"]) == (3, 1, 1, 63)


def test_unknown_rewards_are_excluded_and_listed(clock):
    api = build_api(clock, messy=True)
    add_unknown_reward_scenario(api)
    report = run(api, clock)
    row = row_for(report, "ann_903")
    assert (row["approved"], row["rejected"], row["pending"], row["earnings_cents"]) == (3, 0, 2, 20)
    unknown = report["unknown_reward_task_ids"]
    assert {"tsk_9005", "tsk_9006"} <= set(unknown) and "tsk_9007" not in unknown
    assert unknown == sorted(unknown)
    assert_part2(api, report)


def test_inactive_annotators_are_on_hold_and_not_payable(clock):
    api = build_api(clock, messy=True)
    add_unknown_reward_scenario(api)
    report = run(api, clock)
    assert row_for(report, "ann_903")["on_hold"] is True
    held = [r for r in report["annotators"] if r["on_hold"]]
    assert len(held) >= 2 and any(r["earnings_cents"] > 0 for r in held)
    totals = report["totals"]
    assert totals["earnings_cents"] == sum(r["earnings_cents"] for r in report["annotators"])
    assert totals["payable_cents"] == sum(r["earnings_cents"] for r in report["annotators"] if not r["on_hold"])
    assert totals["payable_cents"] < totals["earnings_cents"]


def test_clean_data_still_works(clock):
    api = build_api(clock, messy=False)
    report = run(api, clock)
    assert_part1(api, report)
    assert_part2(api, report)
