"""FastAPI application factory and route definitions.

Provides REST endpoints for:
- Device CRUD and inventory
- Metric querying and time-series data
- Agent chat interface
- Alert management
- Compliance audit
- Topology visualization
- Configuration management
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from netopshub import __version__
from netopshub.agents.coordinator import AgentCoordinator
from netopshub.anomaly.detector import AnomalyDetector
from netopshub.collect.unified import UnifiedCollector
from netopshub.config.manager import ConfigManager
from netopshub.discover.scanner import NetworkScanner
from netopshub.discover.topology import TopologyDiscovery
from netopshub.monitor.alerting import AlertManager
from netopshub.monitor.health import HealthMonitor
from netopshub.monitor.sla import SLAMonitor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    agent: str | None = None


class DeviceResponse(BaseModel):
    id: str
    hostname: str
    ip_address: str
    device_type: str
    vendor: str
    model: str
    os_version: str


class AlertAckRequest(BaseModel):
    acknowledged_by: str


class ScanRequest(BaseModel):
    subnet: str = "10.0.0.0/24"
    community: str = "public"


class ComplianceAuditRequest(BaseModel):
    framework: str | None = None
    device_id: str | None = None


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

class AppState:
    """Shared application state."""

    def __init__(self):
        self.collector = UnifiedCollector(demo_mode=True)
        self.scanner = NetworkScanner(demo_mode=True)
        self.topology = TopologyDiscovery()
        self.health_monitor = HealthMonitor()
        self.alert_manager = AlertManager()
        self.sla_monitor = SLAMonitor()
        self.anomaly_detector = AnomalyDetector()
        self.config_manager = ConfigManager()
        self.coordinator = AgentCoordinator(demo_mode=True)


_state: AppState | None = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = get_state()
        await state.collector.start()
        logger.info("NetOpsHub API started")
        yield
        await state.collector.stop()
        logger.info("NetOpsHub API stopped")

    app = FastAPI(
        title="NetOpsHub API",
        description="AI-Native Network Operations Platform",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Health & Info
    # -----------------------------------------------------------------------

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/v1/status")
    async def status():
        state = get_state()
        return {
            "version": __version__,
            "collector": {
                "running": state.collector.is_running,
                "total_metrics": state.collector.total_metrics,
            },
            "devices": state.scanner.discovered_count,
            "alerts": state.alert_manager.get_summary(),
            "agents": state.coordinator.get_agent_status(),
        }

    # -----------------------------------------------------------------------
    # Devices
    # -----------------------------------------------------------------------

    @app.get("/api/v1/devices")
    async def list_devices():
        state = get_state()
        devices = state.scanner.get_discovered_devices()
        if not devices:
            # Auto-discover for demo
            devices = await state.scanner.scan_subnet("10.0.0.0/24")
            state.topology.add_devices(devices)
        return {
            "devices": [
                {
                    "id": d.id,
                    "hostname": d.hostname,
                    "ip_address": d.ip_address,
                    "device_type": d.device_type.value,
                    "vendor": d.vendor.value,
                    "model": d.model,
                    "os_version": d.os_version,
                    "location": d.location,
                    "site": d.site,
                    "uptime_seconds": d.uptime_seconds,
                    "is_managed": d.is_managed,
                }
                for d in devices
            ],
            "total": len(devices),
        }

    @app.post("/api/v1/devices/scan")
    async def scan_devices(req: ScanRequest):
        state = get_state()
        devices = await state.scanner.scan_subnet(req.subnet, req.community)
        state.topology.add_devices(devices)
        return {"devices_found": len(devices)}

    # -----------------------------------------------------------------------
    # Metrics
    # -----------------------------------------------------------------------

    @app.get("/api/v1/metrics")
    async def get_metrics(
        device_id: str | None = None,
        metric_type: str | None = None,
        limit: int = Query(default=100, le=1000),
    ):
        state = get_state()
        # Collect fresh metrics for demo
        if state.collector.total_metrics == 0:
            from netopshub.collect.snmp import SNMPTarget
            for host in ["10.0.0.1", "10.0.0.2", "10.0.1.1"]:
                state.collector.snmp.add_target(SNMPTarget(host=host))
            await state.collector.collect_all()

        metrics = state.collector.get_metrics(device_id, metric_type, limit=limit)
        return {
            "metrics": [m.model_dump() for m in metrics],
            "total": len(metrics),
        }

    @app.post("/api/v1/metrics/collect")
    async def trigger_collection():
        state = get_state()
        metrics = await state.collector.collect_all()
        alerts = state.health_monitor.process_metrics(metrics)
        state.alert_manager.add_alerts(alerts)
        state.sla_monitor.process_metrics(metrics)
        anomalies = state.anomaly_detector.detect_batch(metrics)
        return {
            "metrics_collected": len(metrics),
            "alerts_generated": len(alerts),
            "anomalies_detected": len(anomalies),
        }

    # -----------------------------------------------------------------------
    # Alerts
    # -----------------------------------------------------------------------

    @app.get("/api/v1/alerts")
    async def list_alerts(
        state_filter: str | None = None,
        severity: str | None = None,
        device_id: str | None = None,
        limit: int = Query(default=100, le=1000),
    ):
        state_obj = get_state()
        from netopshub.models import AlertSeverity, AlertState
        s = AlertState(state_filter) if state_filter else None
        sev = AlertSeverity(severity) if severity else None
        alerts = state_obj.alert_manager.get_alerts(state=s, severity=sev, device_id=device_id, limit=limit)
        return {
            "alerts": [a.model_dump() for a in alerts],
            "total": len(alerts),
            "summary": state_obj.alert_manager.get_summary(),
        }

    @app.post("/api/v1/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(alert_id: str, req: AlertAckRequest):
        state = get_state()
        alert = state.alert_manager.acknowledge(alert_id, req.acknowledged_by)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert.model_dump()

    @app.post("/api/v1/alerts/{alert_id}/resolve")
    async def resolve_alert(alert_id: str):
        state = get_state()
        alert = state.alert_manager.resolve(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert.model_dump()

    # -----------------------------------------------------------------------
    # Topology
    # -----------------------------------------------------------------------

    @app.get("/api/v1/topology")
    async def get_topology():
        state = get_state()
        if state.topology.device_count == 0:
            state.topology.build_demo_topology()
        return state.topology.to_dict()

    # -----------------------------------------------------------------------
    # Chat (Agent Interface)
    # -----------------------------------------------------------------------

    @app.post("/api/v1/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        state = get_state()
        response = await state.coordinator.chat(req.message, req.context)
        return ChatResponse(response=response)

    @app.get("/api/v1/chat/history")
    async def chat_history(limit: int = Query(default=50, le=200)):
        state = get_state()
        return {"messages": state.coordinator.get_conversation(limit)}

    # -----------------------------------------------------------------------
    # Compliance
    # -----------------------------------------------------------------------

    @app.post("/api/v1/compliance/audit")
    async def run_compliance_audit(req: ComplianceAuditRequest):
        state = get_state()
        from netopshub.models import AgentTask
        task = AgentTask(
            agent_name="compliance",
            task_type="audit_all" if not req.device_id else "audit",
            description="Compliance audit",
            input_data={
                "framework": req.framework,
                "device_id": req.device_id or "",
            },
        )
        result = await state.coordinator.agents["compliance"].process(task)
        return result.output_data

    @app.get("/api/v1/compliance/status")
    async def compliance_status():
        state = get_state()
        from netopshub.models import AgentTask
        task = AgentTask(
            agent_name="compliance",
            task_type="audit_all",
            description="Get compliance status",
            input_data={},
        )
        result = await state.coordinator.agents["compliance"].process(task)
        return result.output_data

    # -----------------------------------------------------------------------
    # SLA
    # -----------------------------------------------------------------------

    @app.get("/api/v1/sla")
    async def sla_status():
        state = get_state()
        return state.sla_monitor.get_compliance_summary()

    # -----------------------------------------------------------------------
    # Agents
    # -----------------------------------------------------------------------

    @app.get("/api/v1/agents")
    async def agent_status():
        state = get_state()
        return state.coordinator.get_agent_status()

    return app


# For running directly with uvicorn
app = create_app()
