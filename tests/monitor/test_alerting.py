"""Tests for alert manager."""

import pytest
from datetime import datetime, timedelta
from netopshub.monitor.alerting import AlertManager
from netopshub.models import Alert, AlertSeverity, AlertState, MetricType


class TestAlertManager:
    def test_add_alert(self, alert_manager, sample_alert):
        result = alert_manager.add_alert(sample_alert)
        assert result.id == sample_alert.id
        assert alert_manager.total_alerts == 1

    def test_acknowledge_alert(self, alert_manager, sample_alert):
        alert_manager.add_alert(sample_alert)
        result = alert_manager.acknowledge(sample_alert.id, "admin")
        assert result is not None
        assert result.state == AlertState.ACKNOWLEDGED
        assert result.acknowledged_by == "admin"

    def test_resolve_alert(self, alert_manager, sample_alert):
        alert_manager.add_alert(sample_alert)
        result = alert_manager.resolve(sample_alert.id)
        assert result is not None
        assert result.state == AlertState.RESOLVED

    def test_get_alerts_by_severity(self, alert_manager):
        a1 = Alert(device_id="d1", severity=AlertSeverity.WARNING, title="warn", description="")
        a2 = Alert(device_id="d2", severity=AlertSeverity.CRITICAL, title="crit", description="")
        alert_manager.add_alert(a1)
        alert_manager.add_alert(a2)
        warnings = alert_manager.get_alerts(severity=AlertSeverity.WARNING)
        assert len(warnings) == 1

    def test_suppression_rule(self, alert_manager, sample_alert):
        alert_manager.add_suppression_rule(
            device_id=sample_alert.device_id,
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow() + timedelta(hours=1),
            reason="Maintenance",
        )
        result = alert_manager.add_alert(sample_alert)
        assert result.state == AlertState.SUPPRESSED

    def test_summary(self, alert_manager, sample_alert):
        alert_manager.add_alert(sample_alert)
        summary = alert_manager.get_summary()
        assert summary["total"] == 1
        assert summary["active"] == 1
