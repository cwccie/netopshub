"""Tests for all agents."""

import pytest
from netopshub.agents.coordinator import AgentCoordinator
from netopshub.agents.discovery_agent import DiscoveryAgent
from netopshub.agents.knowledge_agent import KnowledgeAgent
from netopshub.agents.diagnosis_agent import DiagnosisAgent
from netopshub.agents.compliance_agent import ComplianceAgent
from netopshub.agents.forecast_agent import ForecastAgent
from netopshub.agents.remediation_agent import RemediationAgent
from netopshub.agents.verification_agent import VerificationAgent
from netopshub.models import AgentTask


class TestDiscoveryAgent:
    @pytest.mark.asyncio
    async def test_scan_subnet_task(self):
        agent = DiscoveryAgent(demo_mode=True)
        task = AgentTask(agent_name="discovery", task_type="scan_subnet", description="test", input_data={"subnet": "10.0.0.0/24"})
        result = await agent.process(task)
        assert result.status == "completed"
        assert result.output_data["devices_found"] > 0

    @pytest.mark.asyncio
    async def test_chat_discover(self):
        agent = DiscoveryAgent(demo_mode=True)
        response = await agent.chat("Discover devices on my network")
        assert "discovered" in response.lower()

    @pytest.mark.asyncio
    async def test_chat_topology(self):
        agent = DiscoveryAgent(demo_mode=True)
        response = await agent.chat("Show me the network topology")
        assert "topology" in response.lower() or "devices" in response.lower()


class TestKnowledgeAgent:
    @pytest.mark.asyncio
    async def test_query_bgp(self):
        agent = KnowledgeAgent(demo_mode=True)
        response = await agent.chat("Why is BGP flapping?")
        assert "bgp" in response.lower()

    @pytest.mark.asyncio
    async def test_query_ospf(self):
        agent = KnowledgeAgent(demo_mode=True)
        response = await agent.chat("OSPF adjacency failure causes")
        assert "ospf" in response.lower()

    @pytest.mark.asyncio
    async def test_ingest_document(self):
        agent = KnowledgeAgent(demo_mode=True)
        task = AgentTask(
            agent_name="knowledge", task_type="ingest", description="test",
            input_data={"text": "This is a test document about network troubleshooting " * 100, "source": "test"},
        )
        result = await agent.process(task)
        assert result.status == "completed"
        assert result.output_data["chunks_created"] > 0


class TestDiagnosisAgent:
    @pytest.mark.asyncio
    async def test_chat_bgp_flapping(self):
        agent = DiagnosisAgent(demo_mode=True)
        response = await agent.chat("Why is BGP flapping on router-core-1?")
        assert "root cause" in response.lower()

    @pytest.mark.asyncio
    async def test_chat_high_cpu(self):
        agent = DiagnosisAgent(demo_mode=True)
        response = await agent.chat("What's causing high CPU on router-core-1?")
        assert "cpu" in response.lower()

    @pytest.mark.asyncio
    async def test_analyze_anomaly(self):
        agent = DiagnosisAgent(demo_mode=True)
        task = AgentTask(
            agent_name="diagnosis", task_type="analyze_anomaly", description="test",
            input_data={"metrics": [
                {"value": 10}, {"value": 12}, {"value": 11},
                {"value": 100}, {"value": 9}, {"value": 10},
            ]},
        )
        result = await agent.process(task)
        assert result.status == "completed"
        assert result.output_data["anomaly_count"] > 0


class TestComplianceAgent:
    @pytest.mark.asyncio
    async def test_audit_all(self):
        agent = ComplianceAgent(demo_mode=True)
        task = AgentTask(agent_name="compliance", task_type="audit_all", description="test", input_data={})
        result = await agent.process(task)
        assert result.status == "completed"
        assert "summary" in result.output_data

    @pytest.mark.asyncio
    async def test_audit_specific_device(self):
        agent = ComplianceAgent(demo_mode=True)
        task = AgentTask(
            agent_name="compliance", task_type="audit", description="test",
            input_data={"device_id": "router-core-1"},
        )
        result = await agent.process(task)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_chat_audit(self):
        agent = ComplianceAgent(demo_mode=True)
        response = await agent.chat("Run a compliance audit")
        assert "compliance" in response.lower() or "score" in response.lower()


class TestForecastAgent:
    @pytest.mark.asyncio
    async def test_predict_threshold_breach(self):
        agent = ForecastAgent(demo_mode=True)
        values = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        task = AgentTask(
            agent_name="forecast", task_type="predict_capacity", description="test",
            input_data={"metric_history": values, "threshold": 50},
        )
        result = await agent.process(task)
        assert result.status == "completed"
        assert result.output_data["prediction"] == "breach_predicted"

    @pytest.mark.asyncio
    async def test_trend_analysis(self):
        agent = ForecastAgent(demo_mode=True)
        task = AgentTask(
            agent_name="forecast", task_type="trend_analysis", description="test",
            input_data={"metric_history": [10, 12, 14, 16, 18, 20]},
        )
        result = await agent.process(task)
        assert result.output_data["trend"] == "increasing"

    @pytest.mark.asyncio
    async def test_chat_bandwidth(self):
        agent = ForecastAgent(demo_mode=True)
        response = await agent.chat("When will bandwidth run out?")
        assert "bandwidth" in response.lower()


class TestRemediationAgent:
    @pytest.mark.asyncio
    async def test_propose_fix(self):
        agent = RemediationAgent(demo_mode=True)
        task = AgentTask(
            agent_name="remediation", task_type="propose_fix", description="test",
            input_data={"issue": "bgp_flapping", "device_id": "router-core-1"},
        )
        result = await agent.process(task)
        assert result.status == "completed"
        assert "proposal" in result.output_data

    @pytest.mark.asyncio
    async def test_chat_fix(self):
        agent = RemediationAgent(demo_mode=True)
        response = await agent.chat("Fix BGP flapping")
        assert "proposal" in response.lower() or "remediation" in response.lower()

    @pytest.mark.asyncio
    async def test_proposal_has_rollback(self):
        agent = RemediationAgent(demo_mode=True)
        task = AgentTask(
            agent_name="remediation", task_type="propose_fix", description="test",
            input_data={"issue": "bgp_flapping", "device_id": "router-core-1"},
        )
        result = await agent.process(task)
        proposal = result.output_data["proposal"]
        assert len(proposal["rollback_commands"]) > 0


class TestVerificationAgent:
    @pytest.mark.asyncio
    async def test_verify_change(self):
        agent = VerificationAgent(demo_mode=True)
        task = AgentTask(
            agent_name="verification", task_type="verify_change", description="test",
            input_data={"device_id": "router-core-1", "change_type": "bgp_fix"},
        )
        result = await agent.process(task)
        assert result.status == "completed"
        assert result.output_data["overall_status"] == "pass"

    @pytest.mark.asyncio
    async def test_health_check(self):
        agent = VerificationAgent(demo_mode=True)
        task = AgentTask(
            agent_name="verification", task_type="health_check", description="test",
            input_data={"device_id": "router-core-1"},
        )
        result = await agent.process(task)
        assert result.output_data["overall"] == "healthy"


class TestCoordinator:
    @pytest.mark.asyncio
    async def test_route_to_discovery(self, coordinator):
        response = await coordinator.chat("Discover devices on my network")
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_route_to_diagnosis(self, coordinator):
        response = await coordinator.chat("Why is BGP flapping on router-core-1?")
        assert "bgp" in response.lower() or "diagnosis" in response.lower()

    @pytest.mark.asyncio
    async def test_route_to_compliance(self, coordinator):
        response = await coordinator.chat("Run a compliance audit")
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_default_response(self, coordinator):
        response = await coordinator.chat("hello")
        assert "netopshub" in response.lower() or "help" in response.lower() or "assistant" in response.lower()

    @pytest.mark.asyncio
    async def test_workflow_diagnose_and_fix(self, coordinator):
        result = await coordinator.run_workflow(
            "diagnose_and_fix",
            {"device_id": "router-core-1", "issue": "bgp_flapping"},
        )
        assert result["status"] == "completed"
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_agent_status(self, coordinator):
        status = coordinator.get_agent_status()
        assert "discovery" in status
        assert "diagnosis" in status
        assert "compliance" in status

    @pytest.mark.asyncio
    async def test_conversation_history(self, coordinator):
        await coordinator.chat("test message")
        history = coordinator.get_conversation()
        assert len(history) >= 2  # user + assistant
