export interface Device {
  id: string;
  hostname: string;
  ip_address: string;
  device_type: string;
  vendor: string;
  model: string;
  os_version: string;
  location: string;
  site: string;
  uptime_seconds: number;
  is_managed: boolean;
}

export interface Alert {
  id: string;
  device_id: string;
  device_hostname: string;
  severity: "info" | "warning" | "critical" | "emergency";
  state: "active" | "acknowledged" | "resolved" | "suppressed";
  title: string;
  description: string;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  timestamp: string;
}

export interface ComplianceResult {
  device_id: string;
  status: string;
  framework: string;
  control_id: string;
  details: string;
}
