import React from "react";

interface ComplianceDevice {
  name: string;
  score: number;
  passed: number;
  failed: number;
  failures: string[];
}

const DEVICES: ComplianceDevice[] = [
  { name: "router-core-1", score: 100, passed: 10, failed: 0, failures: [] },
  { name: "router-core-2", score: 100, passed: 10, failed: 0, failures: [] },
  { name: "switch-dist-1", score: 80, passed: 8, failed: 2, failures: ["Console Timeout", "VTY Access Control"] },
  { name: "switch-access-1", score: 40, passed: 4, failed: 6, failures: ["SNMP Community Not Default", "Password Encryption", "Banner Required", "Console Timeout", "VTY Access Control", "AAA Authentication"] },
  { name: "firewall-edge-1", score: 100, passed: 10, failed: 0, failures: [] },
  { name: "router-branch-1", score: 70, passed: 7, failed: 3, failures: ["Logging Configured", "VTY Access Control", "AAA Authentication"] },
];

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-noh-success" : score >= 60 ? "bg-noh-warning" : "bg-noh-danger";
  return (
    <div className="w-full bg-noh-bg rounded-full h-2.5">
      <div className={`${color} h-2.5 rounded-full`} style={{ width: `${score}%` }} />
    </div>
  );
}

export default function Compliance() {
  const overallScore = Math.round(
    DEVICES.reduce((sum, d) => sum + d.score, 0) / DEVICES.length
  );
  const totalPassed = DEVICES.reduce((sum, d) => sum + d.passed, 0);
  const totalFailed = DEVICES.reduce((sum, d) => sum + d.failed, 0);

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Compliance</h2>
        <p className="text-noh-muted mt-1">
          Configuration auditing against NIST 800-53, CIS Benchmarks, and PCI-DSS
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-noh-surface border border-noh-border rounded-xl p-6 text-center">
          <p className="text-noh-muted text-sm">Overall Score</p>
          <p className={`text-4xl font-bold mt-2 ${overallScore >= 80 ? "text-noh-success" : "text-noh-warning"}`}>
            {overallScore}%
          </p>
        </div>
        <div className="bg-noh-surface border border-noh-border rounded-xl p-6 text-center">
          <p className="text-noh-muted text-sm">Checks Passed</p>
          <p className="text-4xl font-bold mt-2 text-noh-success">{totalPassed}</p>
        </div>
        <div className="bg-noh-surface border border-noh-border rounded-xl p-6 text-center">
          <p className="text-noh-muted text-sm">Checks Failed</p>
          <p className="text-4xl font-bold mt-2 text-noh-danger">{totalFailed}</p>
        </div>
      </div>

      <div className="bg-noh-surface border border-noh-border rounded-xl overflow-hidden">
        <div className="p-6 border-b border-noh-border">
          <h3 className="text-lg font-semibold">Device Compliance Status</h3>
        </div>
        <div className="divide-y divide-noh-border">
          {DEVICES.map((device) => (
            <div key={device.name} className="p-6">
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium">{device.name}</span>
                <span
                  className={`text-sm font-bold ${
                    device.score >= 80
                      ? "text-noh-success"
                      : device.score >= 60
                      ? "text-noh-warning"
                      : "text-noh-danger"
                  }`}
                >
                  {device.score}%
                </span>
              </div>
              <ScoreBar score={device.score} />
              {device.failures.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {device.failures.map((f) => (
                    <span
                      key={f}
                      className="text-xs bg-red-900/20 text-red-300 px-2 py-1 rounded-full"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
