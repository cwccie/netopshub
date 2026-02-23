"""Alert management — severity classification, acknowledgment, suppression."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from netopshub.models import Alert, AlertSeverity, AlertState

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages the lifecycle of alerts.

    Handles alert creation, acknowledgment, resolution, suppression,
    and correlation of related alerts.
    """

    def __init__(self):
        self._alerts: dict[str, Alert] = {}
        self._suppression_rules: list[dict[str, Any]] = []
        self._notification_handlers: list[Any] = []

    def add_alert(self, alert: Alert) -> Alert:
        """Add a new alert, applying suppression rules."""
        if self._is_suppressed(alert):
            alert.state = AlertState.SUPPRESSED
            logger.debug(f"Alert suppressed: {alert.title}")

        # Check for duplicate active alerts
        for existing in self._alerts.values():
            if (
                existing.device_id == alert.device_id
                and existing.metric_type == alert.metric_type
                and existing.state == AlertState.ACTIVE
            ):
                # Update existing alert instead of creating duplicate
                existing.metric_value = alert.metric_value
                existing.description = alert.description
                existing.severity = max(existing.severity, alert.severity, key=lambda s: list(AlertSeverity).index(s))
                return existing

        self._alerts[alert.id] = alert
        logger.info(f"New alert: [{alert.severity.value}] {alert.title}")
        return alert

    def add_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """Add multiple alerts."""
        return [self.add_alert(a) for a in alerts]

    def acknowledge(self, alert_id: str, acknowledged_by: str) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if alert and alert.state == AlertState.ACTIVE:
            alert.state = AlertState.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            logger.info(f"Alert acknowledged: {alert.title} by {acknowledged_by}")
            return alert
        return None

    def resolve(self, alert_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if alert and alert.state in (AlertState.ACTIVE, AlertState.ACKNOWLEDGED):
            alert.state = AlertState.RESOLVED
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Alert resolved: {alert.title}")
            return alert
        return None

    def get_alerts(
        self,
        state: Optional[AlertState] = None,
        severity: Optional[AlertSeverity] = None,
        device_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Query alerts with filters."""
        alerts = list(self._alerts.values())
        if state:
            alerts = [a for a in alerts if a.state == state]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if device_id:
            alerts = [a for a in alerts if a.device_id == device_id]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID."""
        return self._alerts.get(alert_id)

    def get_summary(self) -> dict[str, Any]:
        """Get alert summary statistics."""
        by_severity: dict[str, int] = defaultdict(int)
        by_state: dict[str, int] = defaultdict(int)
        by_device: dict[str, int] = defaultdict(int)

        for alert in self._alerts.values():
            by_severity[alert.severity.value] += 1
            by_state[alert.state.value] += 1
            if alert.state == AlertState.ACTIVE:
                by_device[alert.device_hostname or alert.device_id] += 1

        return {
            "total": len(self._alerts),
            "active": by_state.get("active", 0),
            "acknowledged": by_state.get("acknowledged", 0),
            "resolved": by_state.get("resolved", 0),
            "suppressed": by_state.get("suppressed", 0),
            "by_severity": dict(by_severity),
            "by_device": dict(by_device),
        }

    def add_suppression_rule(
        self,
        device_id: Optional[str] = None,
        metric_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        reason: str = "",
    ) -> None:
        """Add a suppression rule (e.g., maintenance window)."""
        self._suppression_rules.append({
            "device_id": device_id,
            "metric_type": metric_type,
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason,
        })

    def _is_suppressed(self, alert: Alert) -> bool:
        """Check if an alert matches any suppression rules."""
        now = datetime.utcnow()
        for rule in self._suppression_rules:
            if rule.get("start_time") and now < rule["start_time"]:
                continue
            if rule.get("end_time") and now > rule["end_time"]:
                continue
            if rule.get("device_id") and rule["device_id"] != alert.device_id:
                continue
            if rule.get("metric_type") and alert.metric_type and rule["metric_type"] != alert.metric_type.value:
                continue
            return True
        return False

    @property
    def total_alerts(self) -> int:
        return len(self._alerts)
