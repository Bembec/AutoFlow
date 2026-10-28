"""
Subscription plans.

Defaults come from plans.json next to this file (the roadmap's starting
proposals, to be tested with customers). Point LUPHINA_PLANS_FILE at
another JSON file to change prices or limits without a code change.
`null` means unlimited (or custom, for prices).
"""

import json
import os
from functools import lru_cache
from pathlib import Path


DEFAULT_PLANS_FILE = Path(__file__).with_name("plans.json")
DEFAULT_PLAN = "free"


@lru_cache(maxsize=1)
def all_plans():
    path = Path(os.getenv("LUPHINA_PLANS_FILE") or DEFAULT_PLANS_FILE)
    return json.loads(path.read_text(encoding="utf-8"))


def get_plan(name):
    plans = all_plans()
    return plans.get(name) or plans[DEFAULT_PLAN]


def stripe_price_id(plan_name):
    """Stripe price for a plan, e.g. STRIPE_PRICE_STARTER=price_123."""
    return os.getenv(f"STRIPE_PRICE_{plan_name.upper()}", "")


def plan_for_stripe_price(price_id):
    for name in all_plans():
        if price_id and stripe_price_id(name) == price_id:
            return name
    return None


def describe():
    return [{"name": name, **plan} for name, plan in all_plans().items()]
