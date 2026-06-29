#!/usr/bin/env python3
"""
dynamodb.py — DynamoDB incident state management for ir-bot
Author: Chad Hackerman
"""

import os
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime, timezone

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "ir-bot-incidents")
AWS_REGION  = os.environ.get("AWS_REGION", "us-east-1")


class IncidentStore:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.table = self.dynamodb.Table(TABLE_NAME)

    def create_incident(self, incident: dict) -> dict:
        """Store a new incident record."""
        self.table.put_item(Item=incident)
        return incident

    def get_incident(self, incident_id: str) -> dict | None:
        """Retrieve an incident by ID."""
        response = self.table.get_item(Key={"incident_id": incident_id})
        return response.get("Item")

    def update_status(self, incident_id: str, status: str):
        """Update the status of an incident."""
        self.table.update_item(
            Key={"incident_id": incident_id},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status}
        )

    def add_timeline_entry(self, incident_id: str, entry: dict):
        """Append a timeline entry to an incident."""
        self.table.update_item(
            Key={"incident_id": incident_id},
            UpdateExpression="SET timeline = list_append(if_not_exists(timeline, :empty), :entry)",
            ExpressionAttributeValues={
                ":entry": [entry],
                ":empty": []
            }
        )

    def list_active_incidents(self) -> list:
        """Return all incidents with status ACTIVE."""
        response = self.table.scan(
            FilterExpression=Attr("status").eq("ACTIVE")
        )
        items = response.get("Items", [])
        # Sort by declared_at descending
        items.sort(key=lambda x: x.get("declared_at", ""), reverse=True)
        return items

    def list_all_incidents(self, limit=50) -> list:
        """Return all incidents, newest first."""
        response = self.table.scan()
        items = response.get("Items", [])
        items.sort(key=lambda x: x.get("declared_at", ""), reverse=True)
        return items[:limit]
