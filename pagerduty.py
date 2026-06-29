#!/usr/bin/env python3
"""
pagerduty.py — PagerDuty on-call schedule integration for ir-bot
Author: Chad Hackerman
"""

import os
import requests

PAGERDUTY_API_KEY  = os.environ.get("PAGERDUTY_API_KEY", "")
PAGERDUTY_SCHEDULE = os.environ.get("PAGERDUTY_SCHEDULE_ID", "")
PAGERDUTY_BASE_URL = "https://api.pagerduty.com"
FALLBACK_USER      = os.environ.get("FALLBACK_ONCALL_USER", "")


def get_oncall_user() -> str:
    """
    Fetch the currently on-call user from PagerDuty.
    Returns the user's Slack user ID if mapped, otherwise their email.
    Falls back to FALLBACK_ONCALL_USER env var if PagerDuty is unreachable.
    """
    if not PAGERDUTY_API_KEY or not PAGERDUTY_SCHEDULE:
        return FALLBACK_USER

    headers = {
        "Authorization": f"Token token={PAGERDUTY_API_KEY}",
        "Accept": "application/vnd.pagerduty+json;version=2"
    }

    try:
        resp = requests.get(
            f"{PAGERDUTY_BASE_URL}/oncalls",
            headers=headers,
            params={"schedule_ids[]": PAGERDUTY_SCHEDULE, "limit": 1},
            timeout=5
        )
        resp.raise_for_status()
        oncalls = resp.json().get("oncalls", [])
        if oncalls:
            user = oncalls[0].get("user", {})
            # Return email — you can map to Slack user IDs in production
            return user.get("email", FALLBACK_USER)
    except requests.RequestException as e:
        print(f"[pagerduty] Failed to fetch on-call user: {e}")

    return FALLBACK_USER


def get_escalation_policy(policy_id: str) -> dict:
    """Fetch an escalation policy by ID."""
    if not PAGERDUTY_API_KEY:
        return {}

    headers = {
        "Authorization": f"Token token={PAGERDUTY_API_KEY}",
        "Accept": "application/vnd.pagerduty+json;version=2"
    }

    try:
        resp = requests.get(
            f"{PAGERDUTY_BASE_URL}/escalation_policies/{policy_id}",
            headers=headers,
            timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("escalation_policy", {})
    except requests.RequestException as e:
        print(f"[pagerduty] Failed to fetch escalation policy: {e}")
        return {}
