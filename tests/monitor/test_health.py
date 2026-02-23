"""Tests for health monitor."""

import pytest
from netopshub.monitor.health import HealthMonitor
from netopshub.models import Metric, MetricType, MetricThreshold, CollectorType, AlertSeverity


class TestHealthMonitor:
    def test_process_normal_metric(self, health_monitor, sample_metric):
        alerts = health_monitor.process_metrics([sample_metric])
        assert len(alerts) == 0

    def test_process_warning_metric(self, health_monitor):
        metric = Metric(
            device_id="dev1", metric_type=MetricType.CPU,
            value=75.0, unit="percent", source=CollectorType.SNMP,
        )
        alerts = health_monitor.process_metrics([metric])
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_process_critical_metric(self, health_monitor):
        metric = Metric(
            device_id="dev1", metric_type=MetricType.CPU,
            value=90.0, unit="percent", source=CollectorType.SNMP,
        )
        alerts = health_monitor.process_metrics([metric])
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_process_emergency_metric(self, health_monitor):
        metric = Metric(
            device_id="dev1", metric_type=MetricType.CPU,
            value=97.0, unit="percent", source=CollectorType.SNMP,
        )
        alerts = health_monitor.process_metrics([metric])
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.EMERGENCY

    def test_get_device_health(self, health_monitor, sample_metric):
        health_monitor.process_metrics([sample_metric])
        health = health_monitor.get_device_health(sample_metric.device_id)
        assert health["status"] == "healthy"
        assert "cpu" in health["metrics"]

    def test_custom_threshold(self, health_monitor):
        health_monitor.set_threshold(MetricThreshold(
            metric_type=MetricType.CPU,
            warning_threshold=50.0,
            critical_threshold=60.0,
        ))
        metric = Metric(
            device_id="dev1", metric_type=MetricType.CPU,
            value=55.0, unit="percent", source=CollectorType.SNMP,
        )
        alerts = health_monitor.process_metrics([metric])
        assert len(alerts) == 1

    def test_alert_counts(self, health_monitor):
        metric = Metric(
            device_id="dev1", metric_type=MetricType.CPU,
            value=90.0, unit="percent", source=CollectorType.SNMP,
        )
        health_monitor.process_metrics([metric])
        assert health_monitor.alert_count == 1
        assert health_monitor.active_alert_count == 1
