import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Topology from "./pages/Topology";
import Chat from "./pages/Chat";
import Alerts from "./pages/Alerts";
import Compliance from "./pages/Compliance";

const navItems = [
  { path: "/", label: "Dashboard", icon: "grid" },
  { path: "/topology", label: "Topology", icon: "share-2" },
  { path: "/chat", label: "AI Chat", icon: "message-circle" },
  { path: "/alerts", label: "Alerts", icon: "bell" },
  { path: "/compliance", label: "Compliance", icon: "shield" },
];

function NavIcon({ icon }: { icon: string }) {
  const icons: Record<string, string> = {
    grid: "⊞",
    "share-2": "⬡",
    "message-circle": "💬",
    bell: "🔔",
    shield: "🛡",
  };
  return <span className="text-lg mr-3">{icons[icon] || "•"}</span>;
}

function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 bg-noh-surface border-r border-noh-border flex flex-col h-screen fixed">
      <div className="p-6 border-b border-noh-border">
        <h1 className="text-xl font-bold text-noh-primary">NetOpsHub</h1>
        <p className="text-xs text-noh-muted mt-1">AI-Native Network Operations</p>
      </div>
      <nav className="flex-1 p-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-4 py-3 rounded-lg mb-1 transition-colors ${
                isActive
                  ? "bg-noh-primary/20 text-noh-primary"
                  : "text-noh-muted hover:bg-noh-bg hover:text-noh-text"
              }`}
            >
              <NavIcon icon={item.icon} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-noh-border">
        <p className="text-xs text-noh-muted">v0.1.0 — Community Edition</p>
      </div>
    </aside>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-noh-bg">
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/topology" element={<Topology />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/compliance" element={<Compliance />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
