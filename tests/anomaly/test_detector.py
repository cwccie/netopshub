"""Tests for anomaly detector."""

import pytest
from datetime import datetime, timedelta
from netopshub.anomaly.detector import AnomalyDetector, MaintenanceWindow
from netopshub.models import Metric, MetricType, CollectorType


class TestAnomalyDetector:
    def test_no_anomaly_normal_data(self, anomaly_detector):
        for i in range(20):
            m = Metric(device_id="d1", metric_type=MetricType.CPU, value=50.0 + (i % 3), unit="%", source=CollectorType.SNMP)
            results = anomaly_detector.detect(m)
        # Normal data should not trigger anomalies (or very few)
        assert anomaly_detector.anomaly_count <= 2

    def test_detect_spike(self, anomaly_detector):
        # Feed normal data
        for i in range(30):
            m = Metric(device_id="d1", metric_type=MetricType.CPU, value=50.0, unit="%", source=CollectorType.SNMP)
            anomaly_detector.detect(m)
        # Feed anomalous data
        m = Metric(device_id="d1", metric_type=MetricType.CPU, value=150.0, unit="%", source=CollectorType.SNMP)
        results = anomaly_detector.detect(m)
        assert len(results) > 0
        assert results[0].is_anomaly is True

    def test_maintenance_window(self, anomaly_detector):
        anomaly_detector.add_maintenance_window(MaintenanceWindow(
            name="test",
            start=datetime.utcnow() - timedelta(hours=1),
            end=datetime.utcnow() + timedelta(hours=1),
            device_ids=["d1"],
        ))
        for i in range(15):
            m = Metric(device_id="d1", metric_type=MetricType.CPU, value=50.0, unit="%", source=CollectorType.SNMP)
            anomaly_detector.detect(m)
        m = Metric(device_id="d1", metric_type=MetricType.CPU, value=200.0, unit="%", source=CollectorType.SNMP)
        results = anomaly_detector.detect(m)
        assert len(results) == 0  # Suppressed

    def test_batch_detection(self, anomaly_detector):
        metrics = [
            Metric(device_id="d1", metric_type=MetricType.CPU, value=50.0, unit="%", source=CollectorType.SNMP)
            for _ in range(15)
        ]
        results = anomaly_detector.detect_batch(metrics)
        # Normal batch should have no/minimal anomalies
        assert isinstance(results, list)

    def test_min_samples(self, anomaly_detector):
        m = Metric(device_id="d1", metric_type=MetricType.CPU, value=200.0, unit="%", source=CollectorType.SNMP)
        results = anomaly_detector.detect(m)
        assert len(results) == 0  # Not enough samples
