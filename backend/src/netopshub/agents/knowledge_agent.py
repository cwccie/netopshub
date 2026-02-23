"""Knowledge Agent — RAG over vendor documentation.

Ingests vendor documentation (Cisco, Juniper, Arista, Palo Alto),
chunks and embeds into a vector store, and answers knowledge queries
with source attribution.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Optional

from netopshub.agents.base import BaseAgent
from netopshub.models import AgentTask

logger = logging.getLogger(__name__)


# Simulated knowledge base for demo mode
VENDOR_KNOWLEDGE = {
    "bgp_flapping": {
        "title": "BGP Session Flapping — Root Causes and Resolution",
        "content": (
            "BGP session flapping is typically caused by: (1) Physical link instability — "
            "check interface error counters and optic levels. (2) MTU mismatch — BGP uses "
            "TCP, and path MTU issues cause session resets. (3) Hold timer expiry — if the "
            "peer doesn't send keepalives within the hold time (default 180s), the session "
            "drops. (4) Route policy changes — aggressive filtering can cause rapid "
            "withdraw/announce cycles. (5) Memory exhaustion — full tables on low-memory "
            "platforms cause BGP process restarts."
        ),
        "vendor": "multi-vendor",
        "tags": ["bgp", "flapping", "troubleshooting"],
    },
    "ospf_adjacency": {
        "title": "OSPF Adjacency Formation Failures",
        "content": (
            "OSPF adjacency failures are commonly caused by: (1) Area ID mismatch — both "
            "sides must be in the same area. (2) Hello/Dead timer mismatch — default 10s/40s "
            "on broadcast, 30s/120s on NBMA. (3) Authentication mismatch — type and key must "
            "match. (4) MTU mismatch — OSPF checks MTU in DBD packets (disable with "
            "'ip ospf mtu-ignore' on Cisco). (5) Network type mismatch — point-to-point vs "
            "broadcast affects DR/BDR election. (6) Stub area flag mismatch."
        ),
        "vendor": "multi-vendor",
        "tags": ["ospf", "adjacency", "troubleshooting"],
    },
    "high_cpu_cisco": {
        "title": "High CPU Utilization on Cisco IOS/IOS-XE",
        "content": (
            "Common causes of high CPU on Cisco platforms: (1) IP Input process — typically "
            "caused by process-switched traffic (ACL logging, TTL-exceeded, ARP). Use "
            "'show processes cpu sorted' and 'show ip cef'. (2) BGP Scanner — normal during "
            "convergence, but sustained high CPU indicates table churn. (3) SNMP Engine — "
            "excessive polling or large MIB walks. (4) Memory pressure causing garbage "
            "collection. (5) Software bug — check Cisco Bug Search for the specific version."
        ),
        "vendor": "cisco",
        "tags": ["cpu", "cisco", "troubleshooting"],
    },
    "stp_topology_change": {
        "title": "Spanning Tree Topology Changes and Their Impact",
        "content": (
            "STP topology changes (TC) cause MAC address table flushing, leading to "
            "temporary flooding. Frequent TCs indicate: (1) Unstable links — error counters, "
            "duplex mismatch. (2) Incorrectly placed portfast — server ports without portfast "
            "cause TC on every link bounce. (3) Unidirectional link — use UDLD. "
            "(4) Bridge priority misconfiguration — unplanned root bridge changes. "
            "Mitigation: Enable BPDU Guard on access ports, use Root Guard on distribution "
            "uplinks, enable portfast on all host-facing ports."
        ),
        "vendor": "multi-vendor",
        "tags": ["stp", "spanning-tree", "topology-change"],
    },
    "interface_errors": {
        "title": "Interface Error Counter Analysis",
        "content": (
            "Interface error types and their meaning: "
            "CRC errors — usually physical layer: bad cable, optic, or far-end issue. "
            "Input errors — broad category including CRC, frame, overrun. "
            "Output drops — QoS queue full, often during micro-bursts. "
            "Runts — frames smaller than 64 bytes, often collision-related. "
            "Giants — frames exceeding MTU, check jumbo frame configuration. "
            "Late collisions — cable too long or duplex mismatch (half vs full). "
            "Resets — interface flapping, often physical. "
            "Ignored — input buffer full, may need buffer tuning."
        ),
        "vendor": "multi-vendor",
        "tags": ["interface", "errors", "troubleshooting"],
    },
    "palo_alto_ha": {
        "title": "Palo Alto HA Failover Troubleshooting",
        "content": (
            "Palo Alto HA failover causes: (1) Link monitoring — monitored interface goes "
            "down. (2) Path monitoring — monitored IP becomes unreachable. (3) HA heartbeat "
            "loss — HA1 and HA1-backup both fail. (4) Preemption — higher priority peer "
            "comes back online. Check: 'show high-availability all', verify HA link status, "
            "check session sync status. Common issue: asymmetric routing post-failover when "
            "using ECMP — ensure session table is fully synced."
        ),
        "vendor": "palo_alto",
        "tags": ["palo-alto", "ha", "failover"],
    },
}


class DocumentChunk:
    """A chunk of vendor documentation for RAG."""

    def __init__(self, text: str, source: str, metadata: dict[str, Any] | None = None):
        self.text = text
        self.source = source
        self.metadata = metadata or {}
        self.chunk_id = hashlib.md5(text.encode()).hexdigest()[:12]
        self.embedding: list[float] = []  # Would be populated by embedding model


class KnowledgeAgent(BaseAgent):
    """RAG-based knowledge agent for vendor documentation.

    In production, uses Qdrant for vector storage and an embedding model
    for semantic search. In demo mode, uses keyword matching against a
    curated knowledge base.
    """

    def __init__(self, demo_mode: bool = True):
        super().__init__(
            name="knowledge",
            description="RAG over vendor documentation and network knowledge",
        )
        self.demo_mode = demo_mode
        self._knowledge_base = VENDOR_KNOWLEDGE
        self._chunks: list[DocumentChunk] = []
        self._index_built = False

    async def process(self, task: AgentTask) -> AgentTask:
        """Process a knowledge query task."""
        task.status = "running"

        try:
            if task.task_type == "query":
                query = task.input_data.get("query", "")
                results = self._search(query)
                return self._complete_task(task, {
                    "query": query,
                    "results": results,
                    "sources": len(results),
                })

            elif task.task_type == "ingest":
                doc_text = task.input_data.get("text", "")
                source = task.input_data.get("source", "manual")
                chunks = self._chunk_document(doc_text, source)
                self._chunks.extend(chunks)
                return self._complete_task(task, {
                    "chunks_created": len(chunks),
                    "total_chunks": len(self._chunks),
                })

            else:
                return self._fail_task(task, f"Unknown task type: {task.task_type}")

        except Exception as e:
            return self._fail_task(task, str(e))

    async def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Answer knowledge questions using RAG."""
        self.log_message("user", message)

        results = self._search(message)
        if results:
            top = results[0]
            response = (
                f"**{top['title']}**\n\n"
                f"{top['content']}\n\n"
                f"_Source: {top['vendor']} documentation | "
                f"Tags: {', '.join(top.get('tags', []))} | "
                f"Relevance: {top['score']:.0%}_"
            )
            if len(results) > 1:
                related = ", ".join(r["title"] for r in results[1:3])
                response += f"\n\nRelated topics: {related}"
        else:
            response = (
                "I don't have specific documentation on that topic in my knowledge base. "
                "I can help with: BGP, OSPF, STP, interface errors, Cisco CPU troubleshooting, "
                "and Palo Alto HA. Try rephrasing your question."
            )

        self.log_message("assistant", response)
        return response

    def _search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search the knowledge base (keyword-based in demo mode)."""
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))

        scored: list[tuple[float, str, dict]] = []
        for key, doc in self._knowledge_base.items():
            # Score based on keyword overlap
            doc_words = set(re.findall(r'\w+', doc["content"].lower()))
            doc_words.update(doc.get("tags", []))
            doc_words.update(re.findall(r'\w+', doc["title"].lower()))

            overlap = query_words & doc_words
            if overlap:
                score = len(overlap) / len(query_words) if query_words else 0
                scored.append((score, key, doc))

        scored.sort(key=lambda x: -x[0])
        return [
            {**doc, "score": score, "key": key}
            for score, key, doc in scored[:top_k]
            if score > 0.1
        ]

    def _chunk_document(
        self,
        text: str,
        source: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[DocumentChunk]:
        """Split a document into overlapping chunks for embedding."""
        chunks: list[DocumentChunk] = []
        words = text.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            if len(chunk_words) < 20:  # Skip tiny trailing chunks
                continue
            chunk_text = " ".join(chunk_words)
            chunks.append(DocumentChunk(
                text=chunk_text,
                source=source,
                metadata={"position": i, "total_words": len(words)},
            ))

        return chunks

    @property
    def knowledge_count(self) -> int:
        return len(self._knowledge_base)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)
