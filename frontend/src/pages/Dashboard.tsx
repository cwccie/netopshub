import React, { useEffect, useState } from "react";

interface Device {
  id: string;
  hostname: string;
  ip_address: string;
  device_type: string;
  vendor: string;
  model: string;
  os_version: string;
  site: string;
}

const DEMO_DEVICES: Device[] = [
  { id: "1", hostname: "router-core-1", ip_address: "10.0.0.1", device_type: "router", vendor: "cisco", model: "ISR4451-X", os_version: "IOS-XE 17.6.4", site: "datacenter-1" },
  { id: "2", hostname: "router-core-2", ip_address: "10.0.0.2", device_type: "router", vendor: "cisco", model: "ISR4451-X", os_version: "IOS-XE 17.6.4", site: "datacenter-1" },
  { id: "3", hostname: "switch-dist-1", ip_address: "10.0.1.1", device_type: "switch", vendor: "arista", model: "DCS-7280R3", os_version: "EOS 4.31.1F", site: "datacenter-1" },
  { id: "4", hostname: "switch-dist-2", ip_address: "10.0.1.2", device_type: "switch", vendor: "arista", model: "DCS-7280R3", os_version: "EOS 4.31.1F", site: "datacenter-1" },
  { id: "5", hostname: "switch-access-1", ip_address: "10.0.2.1", device_type: "switch", vendor: "cisco", model: "C9300-48P", os_version: "IOS-XE 17.9.1", site: "main-office" },
  { id: "6", hostname: "firewall-edge-1", ip_address: "10.0.0.254", device_type: "firewall", vendor: "palo_alto", model: "PA-5260", os_version: "PAN-OS 11.1.0", site: "datacenter-1" },
  { id: "7", hostname: "router-branch-1", ip_address: "10.0.3.1", device_type: "router", vendor: "juniper", model: "MX204", os_version: "Junos 23.2R1", site: "branch-1" },
];

function StatCard({ title, value, subtitle, color }: { title: string; value: string; subtitle: string; color: string }) {
  return (
    <div className="bg-noh-surface border border-noh-border rounded-xl p-6">
      <p className="text-noh-muted text-sm">{title}</p>
      <p className={`text-3xl font-bold mt-2 ${color}`}>{value}</p>
      <p className="text-noh-muted text-xs mt-2">{subtitle}</p>
    </div>
  );
}

function DeviceRow({ device }: { device: Device }) {
  const typeColors: Record<string, string> = {
    router: "text-blue-400",
    switch: "text-green-400",
    firewall: "text-red-400",
  };

  const vendorBadge: Record<string, string> = {
    cisco: "bg-blue-900/30 text-blue-300",
    arista: "bg-green-900/30 text-green-300",
    juniper: "bg-purple-900/30 text-purple-300",
    palo_alto: "bg-red-900/30 text-red-300",
  };

  return (
    <tr className="border-b border-noh-border hover:bg-noh-bg/50 transition-colors">
      <td className="py-3 px-4">
        <span className="font-medium">{device.hostname}</span>
      </td>
      <td className="py-3 px-4 text-noh-muted">{device.ip_address}</td>
      <td className="py-3 px-4">
        <span className={typeColors[device.device_type] || "text-gray-400"}>
          {device.device_type}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className={`px-2 py-1 rounded-full text-xs ${vendorBadge[device.vendor] || "bg-gray-800 text-gray-300"}`}>
          {device.vendor}
        </span>
      </td>
      <td className="py-3 px-4 text-noh-muted">{device.model}</td>
      <td className="py-3 px-4 text-noh-muted text-sm">{device.os_version}</td>
      <td className="py-3 px-4">
        <span className="inline-block w-2 h-2 rounded-full bg-noh-success mr-2"></span>
        <span className="text-noh-success text-sm">Up</span>
      </td>
    </tr>
  );
}

export default function Dashboard() {
  const [devices] = useState<Device[]>(DEMO_DEVICES);

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <p className="text-noh-muted mt-1">Network overview and device inventory</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Total Devices" value="8" subtitle="7 up, 1 maintenance" color="text-noh-primary" />
        <StatCard title="Active Alerts" value="3" subtitle="1 critical, 2 warning" color="text-noh-warning" />
        <StatCard title="Compliance Score" value="87%" subtitle="NIST 800-53 baseline" color="text-noh-success" />
        <StatCard title="Avg CPU" value="32%" subtitle="Across all devices" color="text-noh-accent" />
      </div>

      <div className="bg-noh-surface border border-noh-border rounded-xl overflow-hidden">
        <div className="p-6 border-b border-noh-border flex justify-between items-center">
          <h3 className="text-lg font-semibold">Device Inventory</h3>
          <span className="text-sm text-noh-muted">{devices.length} devices</span>
        </div>
        <table className="w-full">
          <thead>
            <tr className="text-left text-noh-muted text-sm border-b border-noh-border">
              <th className="py-3 px-4 font-medium">Hostname</th>
              <th className="py-3 px-4 font-medium">IP Address</th>
              <th className="py-3 px-4 font-medium">Type</th>
              <th className="py-3 px-4 font-medium">Vendor</th>
              <th className="py-3 px-4 font-medium">Model</th>
              <th className="py-3 px-4 font-medium">OS Version</th>
              <th className="py-3 px-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <DeviceRow key={device.id} device={device} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
