"""Shared test fixtures for NetOpsHub."""

import pytest
from netopshub.collect.snmp import SNMPPoller, SNMPTarget
from netopshub.collect.netflow import NetFlowReceiver
from netopshub.collect.syslog import SyslogListener
from netopshub.collect.rest_collector import RESTCollector, RESTEndpoint
from netopshub.collect.unified import UnifiedCollector
from netopshub.discover.scanner import NetworkScanner
from netopshub.discover.topology import TopologyDiscovery
from netopshub.monitor.health import HealthMonitor
from netopshub.monitor.alerting import AlertManager
from netopshub.monitor.sla import SLAMonitor
from netopshub.anomaly.detector import AnomalyDetector
from netopshub.config.manager import ConfigManager
from netopshub.agents.coordinator import AgentCoordinator
from netopshub.models import Device, DeviceType, DeviceVendor, Metric, MetricType, Alert, AlertSeverity, CollectorType


@pytest.fixture
def snmp_poller():
    return SNMPPoller(demo_mode=True)


@pytest.fixture
def netflow_receiver():
    return NetFlowReceiver(demo_mode=True)


@pytest.fixture
def syslog_listener():
    return SyslogListener(demo_mode=True)


@pytest.fixture
def rest_collector():
    return RESTCollector(demo_mode=True)


@pytest.fixture
def unified_collector():
    return UnifiedCollector(demo_mode=True)


@pytest.fixture
def scanner():
    return NetworkScanner(demo_mode=True)


@pytest.fixture
def topology():
    return TopologyDiscovery()


@pytest.fixture
def health_monitor():
    return HealthMonitor()


@pytest.fixture
def alert_manager():
    return AlertManager()


@pytest.fixture
def sla_monitor():
    return SLAMonitor()


@pytest.fixture
def anomaly_detector():
    return AnomalyDetector()


@pytest.fixture
def config_manager():
    return ConfigManager()


@pytest.fixture
def coordinator():
    return AgentCoordinator(demo_mode=True)


@pytest.fixture
def sample_device():
    return Device(
        hostname="test-router-1",
        ip_address="10.0.0.1",
        device_type=DeviceType.ROUTER,
        vendor=DeviceVendor.CISCO,
        model="ISR4451-X",
        os_version="IOS-XE 17.6.4",
    )


@pytest.fixture
def sample_metric():
    return Metric(
        device_id="test-device-1",
        device_hostname="test-router-1",
        metric_type=MetricType.CPU,
        value=45.5,
        unit="percent",
        source=CollectorType.SNMP,
    )


@pytest.fixture
def sample_alert():
    return Alert(
        device_id="test-device-1",
        device_hostname="test-router-1",
        severity=AlertSeverity.WARNING,
        title="CPU threshold exceeded",
        description="CPU at 85%",
        metric_type=MetricType.CPU,
        metric_value=85.0,
        threshold_value=70.0,
    )
