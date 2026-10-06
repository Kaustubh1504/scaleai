MIN_SECONDS = 20
SPEEDING_RATIO = 0.5


def duration_seconds(sub):
    return (sub.submitted_at - sub.started_at).total_seconds()


# VERIFIED
def is_fast(sub):
    return duration_seconds(sub) < MIN_SECONDS


def flag_speeders(table):
    for row in table.values():
        if row.submissions and row.fast_ratio >= SPEEDING_RATIO:
            row.flags.add("speeding")
