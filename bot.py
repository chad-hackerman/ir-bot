#!/usr/bin/env python3
"""
bot.py — AWS Lambda entry point and Slack event router for ir-bot
Author: Chad Hackerman
"""

import json
import os
import hmac
import hashlib
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from handlers import (
    handle_incident_new,
    handle_incident_update,
    handle_incident_resolve,
    handle_incident_report,
    handle_incident_list,
    handle_runbook
)

slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]


def verify_slack_signature(event: dict) -> bool:
    """Verify the request is genuinely from Slack."""
    headers = event.get("headers", {})
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    body = event.get("body", "")

    # Reject requests older than 5 minutes
    if abs(time.time() - int(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{body}"
    computed = "v0=" + hmac.new(
        SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


def parse_slash_command(body: str) -> dict:
    """Parse URL-encoded Slack slash command payload."""
    params = {}
    for pair in body.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            params[k] = v.replace("+", " ")
    return params


def lambda_handler(event, context):
    """Main AWS Lambda handler — routes all incoming Slack events."""

    # Slack URL verification challenge (one-time setup)
    if event.get("body"):
        try:
            body_json = json.loads(event["body"])
            if body_json.get("type") == "url_verification":
                return {
                    "statusCode": 200,
                    "body": json.dumps({"challenge": body_json["challenge"]})
                }
        except (json.JSONDecodeError, KeyError):
            pass

    # Verify request signature
    if not verify_slack_signature(event):
        return {"statusCode": 401, "body": "Unauthorized"}

    body = event.get("body", "")

    # Handle slash commands (URL-encoded)
    if "command=%2F" in body or "command=/" in body:
        params = parse_slash_command(body)
        command = params.get("command", "")
        text    = params.get("text", "").strip()
        channel = params.get("channel_id", "")
        user    = params.get("user_id", "")

        if command == "/incident":
            parts = text.split(" ", 1)
            subcommand = parts[0].lower() if parts else ""
            args = parts[1] if len(parts) > 1 else ""

            if subcommand == "new":
                return handle_incident_new(slack_client, args, channel, user)
            elif subcommand == "update":
                return handle_incident_update(slack_client, args, channel, user)
            elif subcommand == "resolve":
                return handle_incident_resolve(slack_client, args, channel, user)
            elif subcommand == "report":
                return handle_incident_report(slack_client, args, channel, user)
            elif subcommand == "list":
                return handle_incident_list(slack_client, channel)
            else:
                return _help_response()

        elif command == "/runbook":
            return handle_runbook(slack_client, text.strip(), channel)

    return {"statusCode": 200, "body": "OK"}


def _help_response():
    return {
        "statusCode": 200,
        "body": json.dumps({
            "response_type": "ephemeral",
            "text": (
                "*ir-bot commands:*\n"
                "`/incident new <type> <severity>` — Declare a new incident\n"
                "`/incident update <id> <message>` — Post a timeline update\n"
                "`/incident resolve <id>` — Mark incident as resolved\n"
                "`/incident report <id>` — Generate post-incident report\n"
                "`/incident list` — List all active incidents\n"
                "`/runbook <type>` — Pull up a runbook\n\n"
                "*Incident types:* malware · data-breach · ddos · phishing · ransomware · unauthorized-access · other\n"
                "*Severity levels:* SEV1 · SEV2 · SEV3 · SEV4"
            )
        })
    }


# Local development entry point
if __name__ == "__main__":
    from flask import Flask, request
    app = Flask(__name__)

    @app.route("/slack/events", methods=["POST"])
    def slack_events():
        event = {
            "headers": dict(request.headers),
            "body": request.get_data(as_text=True)
        }
        result = lambda_handler(event, None)
        return result.get("body", "OK"), result.get("statusCode", 200)

    app.run(port=3000, debug=True)
