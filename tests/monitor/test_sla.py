"""Tests for SLA monitor."""

import pytest
from netopshub.monitor.sla import SLAMonitor
from netopshub.models import Metric, MetricType, CollectorType


class TestSLAMonitor:
    def test_init(self, sla_monitor):
        assert sla_monitor.target_count > 0

    def test_process_metrics(self, sla_monitor):
        metrics = [
            Metric(device_id="d1", metric_type=MetricType.LATENCY, value=5.0, unit="ms", source=CollectorType.SNMP),
            Metric(device_id="d1", metric_type=MetricType.PACKET_LOSS, value=0.01, unit="%", source=CollectorType.SNMP),
        ]
        sla_monitor.process_metrics(metrics)
        reports = sla_monitor.evaluate(device_id="d1")
        assert len(reports) > 0

    def test_compliance_summary(self, sla_monitor):
        summary = sla_monitor.get_compliance_summary()
        assert "total_targets" in summary
        assert "overall_compliance" in summary
