"""Mock Users API and sample orders for problem 16. Tests and your __main__ block both use these."""

from __future__ import annotations

import random

from kit import MockAPI, error_response

N_USERS = 40
DANGLING_USER_IDS = ("usr_404", "usr_gone")  # referenced by orders, but deleted from the Users API


def make_users(n: int = N_USERS) -> dict[str, dict]:
    tiers = ("free", "pro", "enterprise")
    return {f"usr_{i:03d}": {"id": f"usr_{i:03d}", "name": f"Customer {i}", "email": f"c{i}@example.com",
                             "tier": tiers[i % 3]}
            for i in range(1, n + 1)}


def make_orders(n: int = 500, n_users: int = N_USERS, seed: int = 16) -> list[dict]:
    """``n`` orders spread over ``n_users`` users, plus a few pointing at deleted users."""
    rng = random.Random(seed)
    user_ids = [f"usr_{i:03d}" for i in range(1, n_users + 1)]
    orders = []
    for i in range(1, n + 1):
        user_id = DANGLING_USER_IDS[(i // 50) % 2] if i % 50 == 0 else rng.choice(user_ids)
        orders.append({"id": f"ord_{i:04d}", "user_id": user_id, "total_cents": rng.randint(100, 50_000)})
    return orders


def make_api(n_users: int = N_USERS, clock=None) -> MockAPI:
    """GET /v1/users/{user_id} -> the user, or 404."""
    api = MockAPI(clock=clock)
    users = make_users(n_users)
    api.users = users

    @api.route("GET", "/v1/users/{user_id}")
    def get_user(req, user_id):
        if user_id not in users:
            return error_response(404, f"user {user_id} not found")
        return users[user_id]

    return api
