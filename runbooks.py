#!/usr/bin/env python3
"""
runbooks.py — Incident runbooks and checklists for ir-bot
Author: Chad Hackerman
"""

RUNBOOKS = {
    "malware": """
*🦠 Malware Incident Runbook*

*Immediate Actions (0–15 min):*
☐ Isolate affected host(s) from network
☐ Preserve system state — take memory dump if possible
☐ Identify malware family via AV/EDR alert
☐ Notify Incident Commander and Technical Lead

*Investigation (15–60 min):*
☐ Collect IOCs (file hashes, IPs, domains, registry keys)
☐ Search SIEM for lateral movement from affected host
☐ Check for persistence mechanisms (startup, scheduled tasks, services)
☐ Determine initial infection vector

*Containment:*
☐ Block malicious IPs/domains at firewall
☐ Add file hashes to AV/EDR blocklist
☐ Scan all hosts for same IOCs
☐ Reset credentials for affected accounts

*Eradication & Recovery:*
☐ Reimage or remediate affected host(s)
☐ Restore from clean backup if needed
☐ Re-enable host on network after verification
☐ Monitor for reinfection for 48 hours
""",

    "data-breach": """
*🔓 Data Breach Runbook*

*Immediate Actions (0–15 min):*
☐ Identify what data was accessed/exfiltrated
☐ Identify affected systems and accounts
☐ Revoke compromised credentials immediately
☐ Notify legal and compliance teams

*Investigation (15–60 min):*
☐ Determine breach timeline from logs
☐ Identify point of entry
☐ Scope affected data — PII, PCI, PHI, IP?
☐ Determine if breach is ongoing

*Containment:*
☐ Block attacker's access vectors
☐ Enable enhanced logging on affected systems
☐ Preserve all logs and forensic evidence

*Notification & Compliance:*
☐ Assess regulatory notification requirements (GDPR 72hr, HIPAA, etc.)
☐ Prepare breach notification communications
☐ Brief executive leadership
☐ Engage legal counsel
""",

    "ddos": """
*🌊 DDoS Attack Runbook*

*Immediate Actions (0–15 min):*
☐ Confirm attack type (volumetric, protocol, application layer)
☐ Identify targeted IPs/services
☐ Notify upstream ISP and/or CDN provider
☐ Enable DDoS mitigation (Cloudflare, AWS Shield, etc.)

*Mitigation (15–60 min):*
☐ Null-route or blackhole targeted IPs if needed
☐ Implement rate limiting at edge
☐ Block source IPs/ASNs if pattern is clear
☐ Scale infrastructure if application-layer attack

*Monitoring:*
☐ Track attack volume and traffic patterns
☐ Monitor legitimate user impact
☐ Coordinate with CDN/ISP on filtering
☐ Document attack characteristics for post-incident

*Recovery:*
☐ Verify services restored to normal
☐ Remove emergency blocks on legitimate traffic
☐ Review and tune DDoS protection rules
""",

    "phishing": """
*🎣 Phishing Incident Runbook*

*Immediate Actions (0–15 min):*
☐ Collect original phishing email (headers + body)
☐ Identify all recipients in the organization
☐ Determine if any users clicked links or submitted credentials
☐ Quarantine or delete phishing email from all mailboxes

*Investigation (15–60 min):*
☐ Analyze phishing URL and infrastructure
☐ Check for credential harvesting page
☐ Search SIEM for connections to phishing domain
☐ Identify any users who submitted credentials

*Containment:*
☐ Reset passwords for affected users
☐ Revoke active sessions for affected accounts
☐ Block phishing domain at email gateway and proxy
☐ Enable MFA if not already active for affected accounts

*User Communication:*
☐ Notify all recipients with guidance
☐ Send organization-wide awareness if widespread
☐ Report phishing domain to registrar and hosting provider
""",

    "ransomware": """
*💀 Ransomware Incident Runbook*

*Immediate Actions (0–15 min):*
☐ IMMEDIATELY isolate all affected hosts from network
☐ Disable file shares and network drives
☐ Do NOT reboot affected systems
☐ Notify executive leadership and legal

*Investigation (15–60 min):*
☐ Identify ransomware variant and family
☐ Determine encryption scope (what files/systems)
☐ Find patient zero and initial infection vector
☐ Check backup integrity — are backups affected?

*Containment:*
☐ Identify and block C2 infrastructure
☐ Scan all systems for ransomware IOCs
☐ Preserve forensic evidence before remediation
☐ Assess if decryptor is available (nomoreransom.org)

*Recovery:*
☐ Restore from clean, verified backups
☐ Rebuild affected systems from scratch if needed
☐ Prioritize restoration by business criticality
☐ Engage ransomware negotiation firm if needed (as last resort)

*Do NOT pay ransom without legal and executive approval.*
""",

    "unauthorized-access": """
*🚪 Unauthorized Access Runbook*

*Immediate Actions (0–15 min):*
☐ Revoke the compromised account's sessions and credentials
☐ Identify what systems and data were accessed
☐ Preserve authentication logs
☐ Determine if access is ongoing

*Investigation (15–60 min):*
☐ Trace how access was obtained (stolen creds, brute force, exploit?)
☐ Review access logs for data accessed or exfiltrated
☐ Check for persistence mechanisms (backdoors, new accounts, SSH keys)
☐ Determine full scope of unauthorized activity

*Containment:*
☐ Rotate credentials for affected accounts and any related accounts
☐ Enable MFA on affected accounts
☐ Block attacker's source IPs
☐ Review and tighten IAM policies

*Recovery:*
☐ Verify all attacker access paths are closed
☐ Enable enhanced monitoring on affected systems
☐ Review access controls to prevent recurrence
""",

    "other": """
*⚠️ General Incident Runbook*

*Immediate Actions:*
☐ Document initial scope and symptoms
☐ Assign Incident Commander
☐ Establish communication channel (this channel)
☐ Begin timeline documentation

*Investigation:*
☐ Collect relevant logs and evidence
☐ Identify affected systems and users
☐ Determine attack vector or root cause
☐ Assess business impact

*Containment:*
☐ Implement appropriate containment measures
☐ Prevent further spread or damage
☐ Preserve forensic evidence

*Recovery:*
☐ Restore affected services
☐ Verify environment is clean
☐ Monitor for recurrence
☐ Document lessons learned
"""
}


def get_runbook(incident_type: str) -> str:
    """Return the runbook for the given incident type, falling back to 'other'."""
    return RUNBOOKS.get(incident_type.lower(), RUNBOOKS["other"])
