import React, { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string;
}

const WELCOME = `I'm NetOpsHub's AI assistant. I can help with:

**Discovery** — "Discover devices on 10.0.0.0/24"
**Diagnosis** — "Why is BGP flapping on router-core-1?"
**Knowledge** — "What causes OSPF adjacency failures?"
**Compliance** — "Run a NIST 800-53 compliance audit"
**Forecasting** — "When will WAN bandwidth run out?"
**Remediation** — "Fix the compliance failures"
**Verification** — "Verify the last change was successful"

What would you like to investigate?`;

const DEMO_RESPONSES: Record<string, string> = {
  bgp: `*[Diagnosis Agent]*

**Root Cause Analysis: BGP Flapping on router-core-1**

**Findings:**
1. Interface GigabitEthernet0/4 showing CRC errors (47 in last hour)
2. BGP hold timer expiring due to lost keepalives
3. Correlated with optical power degradation on same interface

**Root Cause:** Physical layer issue on GigabitEthernet0/4 (likely degraded SFP optic) causing intermittent packet loss that exceeds the BGP hold timer threshold.

**Blast Radius:** 3 downstream devices affected
**Confidence:** 87%

**Recommended Actions:**
1. Check optical power levels
2. Replace SFP module if power is low
3. Replace fiber patch cable if errors persist`,

  compliance: `*[Compliance Agent]*

**Compliance Audit Results — All Frameworks**

Overall Score: **78.3%**
Total Checks: 30 | Passed: 23 | Failed: 7

**router-core-1**: 100% [PASS]
**switch-access-1**: 40% [FAIL]
  - FAIL: SNMP Community Not Default: FAIL
  - Fix: Remove: no snmp-server community public
  - FAIL: Password Encryption: FAIL
  - Fix: Configure: service password-encryption
**firewall-edge-1**: 100% [PASS]`,

  discover: `*[Discovery Agent]*

I discovered 8 devices on the network:

  - router-core-1 (10.0.0.1) — Cisco ISR4451-X
  - router-core-2 (10.0.0.2) — Cisco ISR4451-X
  - switch-dist-1 (10.0.1.1) — Arista DCS-7280R3
  - switch-dist-2 (10.0.1.2) — Arista DCS-7280R3
  - switch-access-1 (10.0.2.1) — Cisco C9300-48P
  - switch-access-2 (10.0.2.2) — Cisco C9300-48P
  - firewall-edge-1 (10.0.0.254) — Palo Alto PA-5260
  - router-branch-1 (10.0.3.1) — Juniper MX204

Topology graph built with 12 neighbor relationships.`,

  forecast: `*[Forecast Agent]*

**Network Forecast Summary**

| Resource | Status | Time to Critical |
|----------|--------|-----------------|
| WAN Bandwidth | Warning | 4.1 months |
| DC Fabric | OK | 19+ months |
| Router CPU | OK | No trend |
| Router Memory | Watch | 44 weeks |
| Switch TCAM | Warning | 6.2 months |

**Priority Actions:**
1. Plan WAN bandwidth upgrade (Q2 2026)
2. Optimize TCAM usage on distribution switches`,
};

function getResponse(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("bgp") || lower.includes("flap") || lower.includes("why"))
    return DEMO_RESPONSES.bgp;
  if (lower.includes("compliance") || lower.includes("audit") || lower.includes("nist"))
    return DEMO_RESPONSES.compliance;
  if (lower.includes("discover") || lower.includes("scan"))
    return DEMO_RESPONSES.discover;
  if (lower.includes("forecast") || lower.includes("predict") || lower.includes("bandwidth"))
    return DEMO_RESPONSES.forecast;
  return WELCOME;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: WELCOME },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // Simulate API call
    setTimeout(() => {
      const response = getResponse(input);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
      setLoading(false);
    }, 800);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-4">
        <h2 className="text-2xl font-bold">AI Chat</h2>
        <p className="text-noh-muted mt-1">
          Ask questions about your network — troubleshooting, compliance, forecasting
        </p>
      </div>

      <div className="flex-1 bg-noh-surface border border-noh-border rounded-xl overflow-y-auto p-6">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`mb-6 ${msg.role === "user" ? "flex justify-end" : ""}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-5 py-3 ${
                msg.role === "user"
                  ? "bg-noh-primary text-white"
                  : "bg-noh-bg border border-noh-border"
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                {msg.content}
              </pre>
            </div>
          </div>
        ))}
        {loading && (
          <div className="mb-6">
            <div className="bg-noh-bg border border-noh-border rounded-xl px-5 py-3 max-w-[80%]">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-noh-muted rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-noh-muted rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                <div className="w-2 h-2 bg-noh-muted rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="mt-4 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask about your network... (e.g., 'Why is BGP flapping on router-core-1?')"
          className="flex-1 bg-noh-surface border border-noh-border rounded-xl px-5 py-3 text-noh-text placeholder-noh-muted focus:outline-none focus:border-noh-primary"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="bg-noh-primary text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>

      <div className="mt-3 flex gap-2 flex-wrap">
        {[
          "Why is BGP flapping on router-core-1?",
          "Run a compliance audit",
          "Discover devices",
          "When will bandwidth run out?",
        ].map((q) => (
          <button
            key={q}
            onClick={() => { setInput(q); }}
            className="text-xs bg-noh-bg border border-noh-border rounded-full px-3 py-1 text-noh-muted hover:text-noh-text hover:border-noh-primary transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
