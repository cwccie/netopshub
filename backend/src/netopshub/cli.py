"""NetOpsHub CLI — command-line interface.

Provides commands for device discovery, monitoring, compliance auditing,
and AI chat from the terminal.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Optional

import click


@click.group()
@click.version_option()
def cli():
    """NetOpsHub — AI-Native Network Operations Platform."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind address")
@click.option("--port", default=8000, help="Bind port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the NetOpsHub API server."""
    try:
        import uvicorn
        click.echo(f"Starting NetOpsHub API on {host}:{port}")
        uvicorn.run(
            "netopshub.api.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except ImportError:
        click.echo("Error: uvicorn is required. Install with: pip install uvicorn")
        sys.exit(1)


@cli.command()
@click.option("--subnet", default="10.0.0.0/24", help="Subnet to scan")
@click.option("--community", default="public", help="SNMP community string")
def discover(subnet: str, community: str):
    """Discover network devices on a subnet."""
    from netopshub.discover.scanner import NetworkScanner

    click.echo(f"Scanning {subnet}...")
    scanner = NetworkScanner(demo_mode=True)
    devices = asyncio.run(scanner.scan_subnet(subnet, community))

    click.echo(f"\nDiscovered {len(devices)} devices:\n")
    for d in devices:
        click.echo(
            f"  {d.hostname:25s} {d.ip_address:15s} "
            f"{d.vendor.value:10s} {d.model:20s} {d.os_version}"
        )


@cli.command()
@click.option("--device", default=None, help="Device hostname or IP")
def monitor(device: Optional[str]):
    """Show health metrics for devices."""
    from netopshub.collect.snmp import SNMPPoller, SNMPTarget
    from netopshub.monitor.health import HealthMonitor

    poller = SNMPPoller(demo_mode=True)
    target_ip = device or "10.0.0.1"
    poller.add_target(SNMPTarget(host=target_ip))

    metrics = asyncio.run(poller.poll_device(target_ip))
    monitor_engine = HealthMonitor()
    alerts = monitor_engine.process_metrics(metrics)

    click.echo(f"\nHealth metrics for {device or target_ip}:\n")
    for m in metrics:
        intf = f" ({m.interface_name})" if m.interface_name else ""
        click.echo(f"  {m.metric_type.value:20s}{intf:25s} {m.value:>8.1f} {m.unit}")

    if alerts:
        click.echo(f"\n{len(alerts)} alert(s):")
        for a in alerts:
            click.echo(f"  [{a.severity.value:8s}] {a.title}")


@cli.command()
@click.option("--framework", default=None, help="Framework (nist-800-53, cis, pci-dss)")
def compliance(framework: Optional[str]):
    """Run compliance audit against security frameworks."""
    from netopshub.agents.compliance_agent import ComplianceAgent
    from netopshub.models import AgentTask

    agent = ComplianceAgent(demo_mode=True)
    task = AgentTask(
        agent_name="compliance",
        task_type="audit_all",
        description="CLI compliance audit",
        input_data={"framework": framework},
    )
    result = asyncio.run(agent.process(task))

    summary = result.output_data.get("summary", {})
    click.echo(f"\nCompliance Audit Results")
    click.echo(f"{'=' * 50}")
    click.echo(f"Overall Score: {summary.get('overall_score', 0)}%")
    click.echo(f"Checks: {summary.get('total_checks', 0)} total, "
               f"{summary.get('compliant', 0)} passed, "
               f"{summary.get('non_compliant', 0)} failed\n")

    for device_id, data in result.output_data.get("devices", {}).items():
        click.echo(f"  {device_id}: {data['score']}%")
        for failure in data.get("failures", []):
            click.echo(f"    FAIL: {failure['rule']}")


@cli.command()
@click.argument("message")
def chat(message: str):
    """Chat with the AI assistant."""
    from netopshub.agents.coordinator import AgentCoordinator

    coordinator = AgentCoordinator(demo_mode=True)
    response = asyncio.run(coordinator.chat(message))
    click.echo(f"\n{response}")


def main():
    cli()


if __name__ == "__main__":
    main()
