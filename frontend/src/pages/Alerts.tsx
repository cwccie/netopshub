import React, { useState } from "react";

interface AlertItem {
  id: string;
  severity: "emergency" | "critical" | "warning" | "info";
  title: string;
  device: string;
  metric: string;
  value: string;
  time: string;
  state: "active" | "acknowledged" | "resolved";
}

const DEMO_ALERTS: AlertItem[] = [
  { id: "1", severity: "critical", title: "CPU threshold exceeded", device: "router-core-1", metric: "CPU", value: "92%", time: "2 min ago", state: "active" },
  { id: "2", severity: "warning", title: "Memory utilization high", device: "switch-dist-1", metric: "Memory", value: "78%", time: "15 min ago", state: "active" },
  { id: "3", severity: "warning", title: "Interface errors increasing", device: "switch-access-1", metric: "CRC Errors", value: "47/hr", time: "23 min ago", state: "active" },
  { id: "4", severity: "info", title: "BGP session established", device: "router-branch-1", metric: "BGP", value: "Established", time: "1 hr ago", state: "resolved" },
  { id: "5", severity: "critical", title: "Interface down", device: "switch-dist-2", metric: "Gi0/3", value: "Down", time: "2 hr ago", state: "acknowledged" },
  { id: "6", severity: "warning", title: "SLA violation - latency", device: "router-core-2", metric: "Latency", value: "62ms", time: "3 hr ago", state: "resolved" },
  { id: "7", severity: "emergency", title: "Temperature critical", device: "switch-access-2", metric: "Temp", value: "87°C", time: "4 hr ago", state: "resolved" },
  { id: "8", severity: "info", title: "Config change detected", device: "firewall-edge-1", metric: "Config", value: "Modified", time: "5 hr ago", state: "resolved" },
];

const severityStyles: Record<string, { bg: string; text: string; dot: string }> = {
  emergency: { bg: "bg-red-900/20", text: "text-red-400", dot: "bg-red-500" },
  critical: { bg: "bg-orange-900/20", text: "text-orange-400", dot: "bg-orange-500" },
  warning: { bg: "bg-yellow-900/20", text: "text-yellow-400", dot: "bg-yellow-500" },
  info: { bg: "bg-blue-900/20", text: "text-blue-400", dot: "bg-blue-500" },
};

const stateStyles: Record<string, string> = {
  active: "bg-red-500/20 text-red-300",
  acknowledged: "bg-yellow-500/20 text-yellow-300",
  resolved: "bg-green-500/20 text-green-300",
};

export default function Alerts() {
  const [filter, setFilter] = useState<string>("all");
  const filtered = filter === "all" ? DEMO_ALERTS : DEMO_ALERTS.filter((a) => a.state === filter);
  const active = DEMO_ALERTS.filter((a) => a.state === "active").length;
  const critical = DEMO_ALERTS.filter((a) => a.severity === "critical" || a.severity === "emergency").length;

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Alerts</h2>
        <p className="text-noh-muted mt-1">
          {active} active alert{active !== 1 ? "s" : ""}, {critical} critical
        </p>
      </div>

      <div className="flex gap-3 mb-6">
        {["all", "active", "acknowledged", "resolved"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f
                ? "bg-noh-primary text-white"
                : "bg-noh-surface border border-noh-border text-noh-muted hover:text-noh-text"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== "all" && (
              <span className="ml-2 text-xs opacity-70">
                ({DEMO_ALERTS.filter((a) => a.state === f).length})
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.map((alert) => {
          const sev = severityStyles[alert.severity];
          return (
            <div
              key={alert.id}
              className={`${sev.bg} border border-noh-border rounded-xl p-4 flex items-center justify-between`}
            >
              <div className="flex items-center gap-4">
                <div className={`w-3 h-3 rounded-full ${sev.dot} ${alert.state === "active" ? "animate-pulse" : ""}`} />
                <div>
                  <p className={`font-medium ${sev.text}`}>{alert.title}</p>
                  <p className="text-noh-muted text-sm mt-1">
                    {alert.device} &middot; {alert.metric}: {alert.value} &middot; {alert.time}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${stateStyles[alert.state]}`}>
                  {alert.state}
                </span>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${sev.bg} ${sev.text}`}>
                  {alert.severity}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
