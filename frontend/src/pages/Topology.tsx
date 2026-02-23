import React from "react";

const nodes = [
  { id: "r1", label: "router-core-1", type: "router", x: 300, y: 50 },
  { id: "r2", label: "router-core-2", type: "router", x: 500, y: 50 },
  { id: "fw", label: "firewall-edge-1", type: "firewall", x: 100, y: 50 },
  { id: "s1", label: "switch-dist-1", type: "switch", x: 250, y: 200 },
  { id: "s2", label: "switch-dist-2", type: "switch", x: 550, y: 200 },
  { id: "a1", label: "switch-access-1", type: "switch", x: 300, y: 350 },
  { id: "a2", label: "switch-access-2", type: "switch", x: 500, y: 350 },
  { id: "br", label: "router-branch-1", type: "router", x: 700, y: 50 },
];

const links = [
  { from: "fw", to: "r1" }, { from: "fw", to: "r2" },
  { from: "r1", to: "r2" },
  { from: "r1", to: "s1" }, { from: "r1", to: "s2" },
  { from: "r2", to: "s1" }, { from: "r2", to: "s2" },
  { from: "s1", to: "a1" }, { from: "s1", to: "a2" },
  { from: "s2", to: "a1" }, { from: "s2", to: "a2" },
  { from: "r2", to: "br" },
];

const typeColors: Record<string, string> = {
  router: "#3b82f6",
  switch: "#22c55e",
  firewall: "#ef4444",
};

export default function Topology() {
  const nodeMap = Object.fromEntries(nodes.map((n) => [n.id, n]));

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Network Topology</h2>
        <p className="text-noh-muted mt-1">Auto-discovered via LLDP/CDP neighbor data</p>
      </div>

      <div className="bg-noh-surface border border-noh-border rounded-xl p-6">
        <svg viewBox="0 0 800 430" className="w-full" style={{ maxHeight: "500px" }}>
          {/* Links */}
          {links.map((link, i) => {
            const from = nodeMap[link.from];
            const to = nodeMap[link.to];
            return (
              <line
                key={i}
                x1={from.x + 40}
                y1={from.y + 20}
                x2={to.x + 40}
                y2={to.y + 20}
                stroke="#475569"
                strokeWidth="2"
                strokeDasharray={link.from === "r2" && link.to === "br" ? "6,4" : "none"}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => (
            <g key={node.id}>
              <rect
                x={node.x}
                y={node.y}
                width={80}
                height={40}
                rx={8}
                fill={typeColors[node.type]}
                opacity={0.2}
                stroke={typeColors[node.type]}
                strokeWidth={2}
              />
              <text
                x={node.x + 40}
                y={node.y + 24}
                textAnchor="middle"
                fill={typeColors[node.type]}
                fontSize="10"
                fontWeight="bold"
              >
                {node.label.replace("switch-", "sw-").replace("router-", "r-").replace("firewall-", "fw-")}
              </text>
            </g>
          ))}

          {/* Legend */}
          <g transform="translate(20, 400)">
            <rect x="0" y="0" width="12" height="12" rx="2" fill="#3b82f6" />
            <text x="18" y="10" fill="#94a3b8" fontSize="11">Router</text>
            <rect x="80" y="0" width="12" height="12" rx="2" fill="#22c55e" />
            <text x="98" y="10" fill="#94a3b8" fontSize="11">Switch</text>
            <rect x="160" y="0" width="12" height="12" rx="2" fill="#ef4444" />
            <text x="178" y="10" fill="#94a3b8" fontSize="11">Firewall</text>
            <line x1="260" y1="6" x2="290" y2="6" stroke="#94a3b8" strokeWidth="2" strokeDasharray="6,4" />
            <text x="298" y="10" fill="#94a3b8" fontSize="11">WAN Link</text>
          </g>
        </svg>
      </div>

      <div className="grid grid-cols-3 gap-6 mt-6">
        <div className="bg-noh-surface border border-noh-border rounded-xl p-4">
          <p className="text-noh-muted text-sm">Devices</p>
          <p className="text-2xl font-bold text-noh-primary mt-1">{nodes.length}</p>
        </div>
        <div className="bg-noh-surface border border-noh-border rounded-xl p-4">
          <p className="text-noh-muted text-sm">Links</p>
          <p className="text-2xl font-bold text-noh-accent mt-1">{links.length}</p>
        </div>
        <div className="bg-noh-surface border border-noh-border rounded-xl p-4">
          <p className="text-noh-muted text-sm">Discovery Protocol</p>
          <p className="text-2xl font-bold text-noh-success mt-1">LLDP</p>
        </div>
      </div>
    </div>
  );
}
