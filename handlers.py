#!/usr/bin/env python3
"""
handlers.py — Slash command handlers for ir-bot
Author: Chad Hackerman
"""

import json
import uuid
from datetime import datetime, timezone
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dynamodb import IncidentStore
from runbooks import get_runbook
from pagerduty import get_oncall_user

db = IncidentStore()

SEVERITY_EMOJI = {
    "SEV1": "🔴",
    "SEV2": "🟠",
    "SEV3": "🟡",
    "SEV4": "🟢"
}

ROLES = ["Incident Commander", "Communications Lead", "Technical Lead", "Scribe"]


def _ok(text: str, in_channel=False) -> dict:
    return {
        "statusCode": 200,
        "body": json.dumps({
            "response_type": "in_channel" if in_channel else "ephemeral",
            "text": text
        })
    }


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------

def handle_incident_new(client: WebClient, args: str, channel: str, user: str) -> dict:
    """
    /incident new <type> <severity>
    Creates a new incident channel, assigns roles, posts runbook.
    """
    parts = args.split()
    if len(parts) < 2:
        return _ok("Usage: `/incident new <type> <severity>`\nExample: `/incident new malware SEV1`")

    inc_type = parts[0].lower()
    severity = parts[1].upper()

    if severity not in SEVERITY_EMOJI:
        return _ok(f"Invalid severity `{severity}`. Use: SEV1, SEV2, SEV3, or SEV4.")

    incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
    channel_name = f"inc-{incident_id.lower()}-{inc_type}"

    # Create dedicated incident channel
    try:
        new_channel = client.conversations_create(name=channel_name, is_private=False)
        inc_channel_id = new_channel["channel"]["id"]
    except SlackApiError as e:
        return _ok(f"Failed to create channel: {e.response['error']}")

    # Assign roles via PagerDuty on-call or fallback to reporter
    assigned_roles = {}
    oncall = get_oncall_user()
    for i, role in enumerate(ROLES):
        assigned_roles[role] = oncall if i == 0 else user

    # Store incident in DynamoDB
    incident = {
        "incident_id": incident_id,
        "type": inc_type,
        "severity": severity,
        "status": "ACTIVE",
        "channel_id": inc_channel_id,
        "declared_by": user,
        "declared_at": _ts(),
        "roles": assigned_roles,
        "timeline": [{"ts": _ts(), "event": f"Incident declared by <@{user}>"}]
    }
    db.create_incident(incident)

    # Post incident header to new channel
    emoji = SEVERITY_EMOJI[severity]
    header = (
        f"{emoji} *Incident Declared: {incident_id}*\n"
        f"*Type:* {inc_type.replace('-', ' ').title()}\n"
        f"*Severity:* {severity}\n"
        f"*Declared by:* <@{user}> at {_ts()}\n\n"
        f"*Roles Assigned:*\n"
    )
    for role, uid in assigned_roles.items():
        header += f"• *{role}:* <@{uid}>\n"

    try:
        client.chat_postMessage(channel=inc_channel_id, text=header)
    except SlackApiError:
        pass

    # Post runbook
    runbook_text = get_runbook(inc_type)
    try:
        client.chat_postMessage(
            channel=inc_channel_id,
            text=f"📋 *Runbook: {inc_type.replace('-', ' ').title()}*\n{runbook_text}"
        )
    except SlackApiError:
        pass

    return _ok(
        f"{emoji} Incident `{incident_id}` declared!\n"
        f"Channel: <#{inc_channel_id}>\n"
        f"Severity: {severity} | Type: {inc_type}",
        in_channel=True
    )


def handle_incident_update(client: WebClient, args: str, channel: str, user: str) -> dict:
    """
    /incident update <id> <message>
    Posts a timestamped update to the incident timeline.
    """
    parts = args.split(" ", 1)
    if len(parts) < 2:
        return _ok("Usage: `/incident update <id> <message>`")

    incident_id, message = parts[0].upper(), parts[1]
    incident = db.get_incident(incident_id)
    if not incident:
        return _ok(f"Incident `{incident_id}` not found.")

    entry = {"ts": _ts(), "event": f"<@{user}>: {message}"}
    db.add_timeline_entry(incident_id, entry)

    try:
        client.chat_postMessage(
            channel=incident["channel_id"],
            text=f"🕐 *Timeline Update* [{_ts()}]\n<@{user}>: {message}"
        )
    except SlackApiError:
        pass

    return _ok(f"Update posted to `{incident_id}`.", in_channel=True)


def handle_incident_resolve(client: WebClient, args: str, channel: str, user: str) -> dict:
    """
    /incident resolve <id>
    Marks an incident as resolved and notifies the channel.
    """
    incident_id = args.strip().upper()
    if not incident_id:
        return _ok("Usage: `/incident resolve <id>`")

    incident = db.get_incident(incident_id)
    if not incident:
        return _ok(f"Incident `{incident_id}` not found.")

    db.update_status(incident_id, "RESOLVED")
    db.add_timeline_entry(incident_id, {"ts": _ts(), "event": f"Incident resolved by <@{user}>"})

    try:
        client.chat_postMessage(
            channel=incident["channel_id"],
            text=(
                f"✅ *Incident {incident_id} Resolved*\n"
                f"Resolved by <@{user}> at {_ts()}\n"
                f"Run `/incident report {incident_id}` to generate the post-incident report."
            )
        )
    except SlackApiError:
        pass

    return _ok(f"Incident `{incident_id}` marked as resolved.", in_channel=True)


def handle_incident_report(client: WebClient, args: str, channel: str, user: str) -> dict:
    """
    /incident report <id>
    Generates and posts a post-incident report.
    """
    incident_id = args.strip().upper()
    if not incident_id:
        return _ok("Usage: `/incident report <id>`")

    incident = db.get_incident(incident_id)
    if not incident:
        return _ok(f"Incident `{incident_id}` not found.")

    timeline_text = "\n".join(
        f"• [{e['ts']}] {e['event']}" for e in incident.get("timeline", [])
    )
    roles_text = "\n".join(
        f"• *{role}:* <@{uid}>" for role, uid in incident.get("roles", {}).items()
    )

    report = (
        f"📄 *Post-Incident Report — {incident_id}*\n\n"
        f"*Type:* {incident['type'].replace('-', ' ').title()}\n"
        f"*Severity:* {incident['severity']}\n"
        f"*Status:* {incident['status']}\n"
        f"*Declared:* {incident['declared_at']}\n\n"
        f"*Roles:*\n{roles_text}\n\n"
        f"*Timeline:*\n{timeline_text}\n\n"
        f"_Report generated by ir-bot at {_ts()}_"
    )

    try:
        client.chat_postMessage(channel=incident["channel_id"], text=report)
    except SlackApiError:
        pass

    return _ok(f"Post-incident report generated for `{incident_id}`.", in_channel=True)


def handle_incident_list(client: WebClient, channel: str) -> dict:
    """
    /incident list
    Lists all active incidents.
    """
    incidents = db.list_active_incidents()
    if not incidents:
        return _ok("No active incidents. 🎉")

    lines = ["*Active Incidents:*"]
    for inc in incidents:
        emoji = SEVERITY_EMOJI.get(inc["severity"], "⚪")
        lines.append(
            f"{emoji} `{inc['incident_id']}` — {inc['type']} ({inc['severity']}) "
            f"| <#{inc['channel_id']}> | Since {inc['declared_at']}"
        )

    return _ok("\n".join(lines))


def handle_runbook(client: WebClient, inc_type: str, channel: str) -> dict:
    """
    /runbook <type>
    Posts the runbook for the given incident type.
    """
    if not inc_type:
        return _ok("Usage: `/runbook <type>`\nTypes: malware · data-breach · ddos · phishing · ransomware · unauthorized-access · other")

    runbook_text = get_runbook(inc_type.lower())
    try:
        client.chat_postMessage(
            channel=channel,
            text=f"📋 *Runbook: {inc_type.replace('-', ' ').title()}*\n{runbook_text}"
        )
    except SlackApiError as e:
        return _ok(f"Failed to post runbook: {e.response['error']}")

    return _ok(f"Runbook for `{inc_type}` posted.")
