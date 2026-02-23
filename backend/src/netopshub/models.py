"""Core data models for NetOpsHub.

All telemetry, device, and alert data is normalized to these Pydantic models,
providing a unified schema across SNMP, NetFlow, syslog, and REST collectors.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DeviceType(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    WIRELESS_CONTROLLER = "wireless_controller"
    ACCESS_POINT = "access_point"
    SERVER = "server"
    UNKNOWN = "unknown"


class DeviceVendor(str, Enum):
    CISCO = "cisco"
    JUNIPER = "juniper"
    ARISTA = "arista"
    PALO_ALTO = "palo_alto"
    FORTINET = "fortinet"
    MERAKI = "meraki"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    BANDWIDTH_IN = "bandwidth_in"
    BANDWIDTH_OUT = "bandwidth_out"
    ERROR_RATE = "error_rate"
    DISCARD_RATE = "discard_rate"
    LATENCY = "latency"
    JITTER = "jitter"
    PACKET_LOSS = "packet_loss"
    TEMPERATURE = "temperature"
    POWER = "power"
    FAN_SPEED = "fan_speed"
    UPTIME = "uptime"
    BGP_PREFIXES = "bgp_prefixes"
    OSPF_NEIGHBORS = "ospf_neighbors"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertState(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class CollectorType(str, Enum):
    SNMP = "snmp"
    NETFLOW = "netflow"
    SYSLOG = "syslog"
    REST_API = "rest_api"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"
    EXEMPTED = "exempted"


class InterfaceStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    ADMIN_DOWN = "admin_down"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Device Models
# ---------------------------------------------------------------------------

class Interface(BaseModel):
    """Network interface on a device."""
    name: str
    index: int = 0
    description: str = ""
    speed_mbps: int = 0
    admin_status: InterfaceStatus = InterfaceStatus.UNKNOWN
    oper_status: InterfaceStatus = InterfaceStatus.UNKNOWN
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    mac_address: Optional[str] = None
    vlan_id: Optional[int] = None
    mtu: int = 1500
    in_octets: int = 0
    out_octets: int = 0
    in_errors: int = 0
    out_errors: int = 0
    in_discards: int = 0
    out_discards: int = 0


class Device(BaseModel):
    """Network device in the inventory."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str
    ip_address: str
    device_type: DeviceType = DeviceType.UNKNOWN
    vendor: DeviceVendor = DeviceVendor.UNKNOWN
    model: str = ""
    os_version: str = ""
    serial_number: str = ""
    location: str = ""
    site: str = ""
    snmp_community: Optional[str] = None
    interfaces: list[Interface] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_managed: bool = True
    uptime_seconds: int = 0
    sys_description: str = ""


# ---------------------------------------------------------------------------
# Metric Models
# ---------------------------------------------------------------------------

class Metric(BaseModel):
    """Unified metric format for all telemetry sources."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    device_hostname: str = ""
    interface_name: Optional[str] = None
    metric_type: MetricType
    value: float
    unit: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: CollectorType = CollectorType.SNMP
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricThreshold(BaseModel):
    """Threshold definition for alerting."""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    emergency_threshold: Optional[float] = None
    comparison: str = "gt"  # gt, lt, eq
    duration_seconds: int = 60
    device_filter: Optional[str] = None
    interface_filter: Optional[str] = None


# ---------------------------------------------------------------------------
# Alert Models
# ---------------------------------------------------------------------------

class Alert(BaseModel):
    """Alert generated from threshold violations or anomaly detection."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    device_hostname: str = ""
    interface_name: Optional[str] = None
    severity: AlertSeverity
    state: AlertState = AlertState.ACTIVE
    title: str
    description: str
    metric_type: Optional[MetricType] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    source: str = "threshold"
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    tags: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Topology Models
# ---------------------------------------------------------------------------

class Neighbor(BaseModel):
    """Neighbor relationship discovered via LLDP/CDP."""
    local_device_id: str
    local_interface: str
    remote_device_id: str
    remote_interface: str
    remote_hostname: str = ""
    remote_ip: Optional[str] = None
    protocol: str = "lldp"  # lldp, cdp, bgp, ospf
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class TopologyLink(BaseModel):
    """Link between two devices in the topology graph."""
    source_device_id: str
    source_interface: str
    target_device_id: str
    target_interface: str
    link_speed_mbps: int = 0
    link_type: str = "ethernet"
    protocol: str = "lldp"
    utilization_in: float = 0.0
    utilization_out: float = 0.0


class TopologyGraph(BaseModel):
    """Complete network topology."""
    devices: list[Device] = Field(default_factory=list)
    links: list[TopologyLink] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Configuration Models
# ---------------------------------------------------------------------------

class ConfigSnapshot(BaseModel):
    """Snapshot of a device's running configuration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    device_hostname: str = ""
    config_text: str
    config_hash: str = ""
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "manual"
    tags: dict[str, str] = Field(default_factory=dict)


class ConfigDiff(BaseModel):
    """Diff between two configuration snapshots."""
    device_id: str
    before_snapshot_id: str
    after_snapshot_id: str
    diff_text: str
    lines_added: int = 0
    lines_removed: int = 0
    lines_changed: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ComplianceRule(BaseModel):
    """Single compliance check rule."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    framework: str = "custom"
    control_id: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    check_type: str = "regex"  # regex, contains, not_contains, command
    pattern: str = ""
    expected_value: Optional[str] = None
    remediation: str = ""


class ComplianceResult(BaseModel):
    """Result of a compliance check on a device."""
    rule_id: str
    device_id: str
    device_hostname: str = ""
    status: ComplianceStatus
    framework: str = ""
    control_id: str = ""
    details: str = ""
    evidence: str = ""
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Flow Models
# ---------------------------------------------------------------------------

class NetFlowRecord(BaseModel):
    """Single NetFlow/IPFIX flow record."""
    src_addr: str
    dst_addr: str
    src_port: int = 0
    dst_port: int = 0
    protocol: int = 6  # TCP default
    bytes: int = 0
    packets: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime = Field(default_factory=datetime.utcnow)
    src_as: int = 0
    dst_as: int = 0
    input_interface: int = 0
    output_interface: int = 0
    tcp_flags: int = 0
    tos: int = 0
    exporter_ip: str = ""


class SyslogMessage(BaseModel):
    """Parsed syslog message."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: Optional[str] = None
    device_hostname: str = ""
    source_ip: str
    facility: int = 1
    severity: int = 6
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str
    program: str = ""
    pid: Optional[int] = None
    structured_data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent Models
# ---------------------------------------------------------------------------

class AgentMessage(BaseModel):
    """Message in an agent conversation."""
    role: str  # user, assistant, system, tool
    content: str
    agent_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """Task assigned to an agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    task_type: str
    description: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class RemediationProposal(BaseModel):
    """Proposed configuration change from the remediation agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str
    device_hostname: str = ""
    title: str
    description: str
    config_commands: list[str] = Field(default_factory=list)
    rollback_commands: list[str] = Field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    approved: bool = False
    approved_by: Optional[str] = None
    executed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# SLA Models
# ---------------------------------------------------------------------------

class SLATarget(BaseModel):
    """SLA target definition."""
    name: str
    description: str = ""
    metric_type: MetricType
    target_value: float
    comparison: str = "lt"  # lt = value must be less than target
    measurement_window: str = "24h"
    device_filter: Optional[str] = None


class SLAReport(BaseModel):
    """SLA compliance report."""
    target: SLATarget
    current_value: float
    is_met: bool
    compliance_percentage: float = 100.0
    measurement_period_start: datetime = Field(default_factory=datetime.utcnow)
    measurement_period_end: datetime = Field(default_factory=datetime.utcnow)
    violations: int = 0
