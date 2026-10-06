from collections import defaultdict

from .models import SessionResult

TIER_RANK = {"gold": 3, "silver": 2, "standard": 1}


# VERIFIED
def priority_key(hold, members):
    rank = TIER_RANK.get(members[hold.member_id].tier, 1)
    return (-rank, hold.placed_at, hold.hold_id)


def allocate(sessions, live_holds, members):
    by_session = defaultdict(list)
    for hold in live_holds:
        by_session[hold.session_id].append(hold)

    results = {}
    for sid, session in sessions.items():
        result = SessionResult(sid)
        for hold in sorted(by_session[sid], key=lambda h: priority_key(h, members)):
            if result.seats_booked + hold.seats <= session.capacity:
                result.booked.append(hold)
                result.seats_booked += hold.seats
            else:
                result.waitlist.append(hold)
        results[sid] = result
    return results
