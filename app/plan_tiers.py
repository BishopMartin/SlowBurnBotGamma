"""Subscription tier definitions and helpers."""

PLAN_TIERS = {
    "crawl": {"max_accounts": 3,  "max_clients": 1,  "price": 19},
    "walk":  {"max_accounts": 10, "max_clients": 5,  "price": 39},
    "run":   {"max_accounts": 25, "max_clients": 10, "price": 59},
}


def get_max_accounts(tier: str) -> int:
    return PLAN_TIERS.get(tier, {}).get("max_accounts", 0)


def get_max_clients(tier: str) -> int:
    return PLAN_TIERS.get(tier, {}).get("max_clients", 0)


def is_valid_tier(tier: str) -> bool:
    return tier in PLAN_TIERS
