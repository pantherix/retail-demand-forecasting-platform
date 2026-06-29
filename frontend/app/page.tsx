"use client";

import { useEffect, useState, ReactNode, useRef } from "react";
import { useStore } from "./store";
import { api } from "./api";
import { useTheme } from "../hooks/useTheme";
import {
  Boxes, LogOut, RefreshCw, X, Menu, Sun, Moon, Bell, Trash2,
  Flag, Gauge, Wrench, Cpu, Network, Zap, Fuel, Activity, TrendingUp, SlidersHorizontal, History, Users, BarChart3
} from "lucide-react";

import ToastContainer from "../components/ui/ToastContainer";

// View imports
import ExecutiveBriefingView from "../components/dashboard/ExecutiveBriefingView";
import ActionCenterView from "../components/dashboard/ActionCenterView";
import ScenarioLabView from "../components/dashboard/ScenarioLabView";
import ReorderEngineView from "../components/dashboard/ReorderEngineView";
import ProductIntelligenceView from "../components/dashboard/ProductIntelligenceView";
import CopilotView from "../components/dashboard/CopilotView";
import WarehouseView from "../components/dashboard/WarehouseView";
import PurchaseOrderView from "../components/dashboard/PurchaseOrderView";
import DatasetUploadView from "../components/dashboard/DatasetUploadView";
import UserManagementView from "../components/dashboard/UserManagementView";
import AuditLogsView from "../components/dashboard/AuditLogsView";
import ForecastAccuracyView from "../components/dashboard/ForecastAccuracyView";

// ── CommandCenterLayout ──────────────────────────────────────────────────────
interface CommandCenterLayoutProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  user: any;
  alertsCount: number;
  onSync: () => void;
  onSignOut: () => void;
  children: ReactNode;
}

function CommandCenterLayout({
  activeTab, setActiveTab, user, alertsCount, onSync, onSignOut, children
}: CommandCenterLayoutProps) {
  const { theme, toggleTheme } = useTheme();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [health, setHealth] = useState<"green" | "yellow" | "red">("green");

  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);

  // Live Pit Wall Telemetry Ticker
  const [telemetry, setTelemetry] = useState({
    lap: 42,
    rpm: 12100,
    ers: 85,
    temp: 102,
    gap: 1.284,
    drs: "AVAILABLE"
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setTelemetry(prev => {
        const nextRpm = 11000 + Math.floor(Math.random() * 1400);
        const nextErs = Math.max(5, Math.min(100, prev.ers + (Math.random() > 0.6 ? -1 : 1)));
        const nextTemp = Math.max(90, Math.min(115, prev.temp + (Math.random() > 0.5 ? -1 : 1)));
        const nextGap = Math.max(0.01, prev.gap + (Math.random() > 0.52 ? -0.005 : 0.004));
        const drsStates = ["AVAILABLE", "ACTIVE", "INACTIVE"];
        const nextDrs = Math.random() > 0.8 ? drsStates[Math.floor(Math.random() * 3)] : prev.drs;
        return {
          lap: prev.lap,
          rpm: nextRpm,
          ers: nextErs,
          temp: nextTemp,
          gap: Number(nextGap.toFixed(3)),
          drs: nextDrs
        };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const WS_ENABLED = true;
    if (!WS_ENABLED) return;

    let isMounted = true;
    let socket: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWS = () => {
      try {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api";
        const cleanBase = apiBase.endsWith("/") ? apiBase.slice(0, -1) : apiBase;
        let apiHost = cleanBase.replace("http://", "").replace("https://", "").replace("/api", "");
        if (!apiHost) {
          if (window.location.host.includes("localhost:3000") || window.location.host.includes("127.0.0.1:3000")) {
            apiHost = "localhost:8000";
          } else {
            apiHost = window.location.host;
          }
        }
        const wsUrl = `${wsProtocol}//${apiHost}/api/ws`;

        socket = new WebSocket(wsUrl);

        socket.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const msg = JSON.parse(event.data);
            console.log("Global Notification received:", msg);
            const newNotif = {
              id: Math.random().toString(36).substr(2, 9),
              message: msg.message || "System mutation event.",
              timestamp: new Date().toLocaleTimeString(),
              read: false,
              type: msg.type
            };
            setNotifications(prev => [newNotif, ...prev]);
            
            // Trigger store refresh globally to update UI
            const store = useStore.getState();
            if (store && typeof store.triggerRefresh === "function") {
              store.triggerRefresh();
            }
          } catch (e) {
            console.error("Failed to parse WebSocket message:", e);
          }
        };

        socket.onerror = (error) => {
          if (isMounted) {
            console.error("WebSocket error:", error);
          }
        };

        socket.onclose = () => {
          if (isMounted) {
            console.log("WebSocket closed. Reconnecting in 5s...");
            reconnectTimeout = setTimeout(connectWS, 5000);
          }
        };
      } catch (err) {
        if (isMounted) {
          console.error("WebSocket connection failed:", err);
        }
      }
    };

    connectWS();

    return () => {
      isMounted = false;
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
      }
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await api.getHealth();
        if (res && (res.status === "healthy" || res.status === "green")) {
          setHealth("green");
        } else if (res && res.status === "yellow") {
          setHealth("yellow");
        } else {
          setHealth("red");
        }
      } catch (err) {
        setHealth("red");
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const navItems: Array<{ id: string; name: string; icon: any; badge?: number }> = [
    { id: "executive", name: "Telemetry Brief", icon: Activity },
    { id: "datasets", name: "Fuel Intake (Upload)", icon: Fuel },
    { id: "accuracy", name: "Forecast Accuracy", icon: BarChart3 },
    { id: "action-center", name: "Cockpit Control", icon: SlidersHorizontal },
    { id: "scenario-lab", name: "Wind Tunnel Sim", icon: TrendingUp },
    { id: "reorder", name: "Pit Stop Planner", icon: Wrench },
    { id: "copilot", name: "Race Engineer AI", icon: Cpu },
    { id: "warehouses", name: "Supply Grid", icon: Network },
    { id: "purchase-orders", name: "Auto-Drift POs", icon: Zap },
    ...(user?.role === "admin" || user?.role === "manager" ? [{ id: "audit-logs", name: "Telemetry Audit", icon: History }] : []),
    ...(user?.role === "admin" ? [{ id: "users", name: "Crew Management", icon: Users }] : []),
  ];

  useEffect(() => {
    if (mobileSidebarOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileSidebarOpen]);

  useEffect(() => {
    if (!mobileSidebarOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileSidebarOpen]);

  const drawerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!mobileSidebarOpen) return;
    const drawer = drawerRef.current;
    if (!drawer) return;
    const focusable = drawer.querySelectorAll('button, [href], input, select, textarea, [tabindex="0"]');
    if (focusable.length === 0) return;
    const first = focusable[0] as HTMLElement;
    const last = focusable[focusable.length - 1] as HTMLElement;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          last.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === last) {
          first.focus();
          e.preventDefault();
        }
      }
    };
    window.addEventListener("keydown", handleTab);
    first.focus();
    return () => window.removeEventListener("keydown", handleTab);
  }, [mobileSidebarOpen]);

  const renderSidebarContent = (isMobile = false) => (
    <>
      <div className="flex flex-col space-y-6 relative z-10">
        <div className="h-16 px-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {/* 3D Die-cast Enamel Badge */}
            <div className="relative p-[1.5px] rounded-lg bg-gradient-to-b from-yellow-300 via-yellow-500 to-yellow-700 shadow-[0_4px_12px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.4)] shrink-0 w-9 h-9 flex items-center justify-center">
              <div className="w-full h-full rounded-[6px] bg-[#FFDC00] bg-gradient-to-br from-[#FFF59D] via-[#FFDC00] to-[#E5A900] flex items-center justify-center border border-black/30 shadow-[inset_0_2px_4px_rgba(255,255,255,0.6),inset_0_-2px_4px_rgba(0,0,0,0.4)]">
                <span className="font-mono font-black text-black text-sm tracking-tight drop-shadow-[1px_1.5px_0px_rgba(255,255,255,0.6)] select-none">
                  SF
                </span>
              </div>
            </div>
            <div>
              <span className="font-extrabold text-white text-sm tracking-widest block font-mono drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
                <span className="text-[#FF1B1B] font-black">SCUDERIA</span> RETAIL
              </span>
              <span className="text-[9px] text-[#FFDC00] font-mono uppercase tracking-widest block font-bold drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
                Pit Wall Telemetry
              </span>
            </div>
          </div>
          {isMobile && (
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(false)}
              className="p-1.5 rounded border border-white/10 text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
              aria-label="Close navigation menu"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* User profile card inside carbon container */}
        <div className="relative overflow-hidden p-3 bg-gradient-to-b from-[#1b1c20] to-[#0a0a0c] border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_4px_12px_rgba(0,0,0,0.5)] rounded-lg flex items-center gap-2.5 backdrop-blur-sm premium-border">
          {/* Glossy glare overlay */}
          <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />
          
          <div className="h-8 w-8 rounded bg-gradient-to-b from-[#3a3d45] to-[#151618] border border-white/20 flex items-center justify-center font-mono font-extrabold text-white text-xs shrink-0 shadow-[inset_0_1.5px_3px_rgba(255,255,255,0.15)] relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-white/10 to-transparent pointer-events-none" />
            {user?.username?.charAt(0).toUpperCase() || "A"}
          </div>
          <div className="min-w-0 flex-1 relative z-10">
            <span className="text-xs font-black text-white block truncate tracking-wide">{user?.fullName}</span>
            <span className="text-[9px] text-[#FFDC00] font-mono block truncate uppercase tracking-widest font-black opacity-80 mt-0.5">{user?.role}</span>
          </div>
        </div>

        {/* Tactile Mechanical / Paddle Shifter Navigation Buttons */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            const IconComponent = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setActiveTab(item.id);
                  if (isMobile) setMobileSidebarOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-mono font-bold transition-all cursor-pointer border border-transparent ${
                  isActive 
                    ? "bg-[radial-gradient(circle_at_center,_#ff2e2e_0%,_#c10000_50%,_#7a0000_100%)] border-[#ff3333]/40 text-white shadow-[inset_0_4px_12px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.15),0_0_12px_rgba(239,68,68,0.3)] pl-3 scale-[1.02] translate-x-1 hover:brightness-110 active:scale-[0.98] duration-150" 
                    : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent transition-all duration-200"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <IconComponent className={`h-4 w-4 transition-colors ${isActive ? "text-[#FF1B1B] drop-shadow-[0_0_6px_rgba(255,27,27,0.6)]" : "text-zinc-500 group-hover:text-zinc-300"}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && item.badge > 0 ? (
                  <span className="px-1.5 py-0.5 rounded bg-red-950/80 text-red-400 border border-red-500/30 text-[9px] font-mono font-black shadow-[0_0_8px_rgba(239,68,68,0.3)]">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Overhauled Live Telemetry Instrument Dial Widget */}
      <div className="p-3 bg-gradient-to-b from-[#141518] to-[#09090b] border border-white/10 rounded-lg space-y-3 select-none font-mono shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_6px_20px_rgba(0,0,0,0.6)] relative z-10">
        <div className="flex justify-between items-center border-b border-white/10 pb-1.5">
          <span className="text-[9px] text-[#FFDC00] font-black uppercase tracking-widest">PIT WALL TELEMETRY</span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full relative flex items-center justify-center">
              <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${
                health === "green" ? "bg-emerald-500" : health === "yellow" ? "bg-amber-400" : "bg-red-500"
              }`} />
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${
                health === "green" ? "bg-emerald-500" : health === "yellow" ? "bg-amber-400" : "bg-red-500"
              }`} />
            </span>
            <span className={`text-[8px] font-black tracking-wider ${
              health === "green" ? "text-emerald-400" : health === "yellow" ? "text-amber-400" : "text-red-400"
            }`}>
              {health === "green" ? "SYS.OK" : health === "yellow" ? "WARN" : "ERR"}
            </span>
          </span>
        </div>

        {/* Precise Instrument Panel Cluster */}
        <div className="grid grid-cols-2 gap-2">
          {/* RPM Card */}
          <div className="ferrari-panel premium-border">
            <div className="absolute top-1 right-1 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full led-glow-red animate-pulse" />
            </div>
            <span className="text-zinc-500 text-[7px] font-black uppercase tracking-wider">RPM</span>
            <span className="text-white text-xs font-black lcd-text leading-none mt-1" style={{ '--glow-color': 'rgba(239, 68, 68, 0.3)' } as any}>
              {telemetry.rpm}
            </span>
          </div>

          {/* Tyre Temp Card */}
          <div className="ferrari-panel premium-border">
            <div className="absolute top-1 right-1 flex items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${
                telemetry.temp > 105 ? "led-glow-red" : "led-glow-green"
              }`} />
            </div>
            <span className="text-zinc-500 text-[7px] font-black uppercase tracking-wider">TYRE TEMP</span>
            <span className="text-white text-xs font-black lcd-text leading-none mt-1" style={{ '--glow-color': telemetry.temp > 105 ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)' } as any}>
              {telemetry.temp}°C
            </span>
          </div>

          {/* ERS Charge Card */}
          <div className="ferrari-panel premium-border">
            <div className="absolute top-1 right-1 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full led-glow-green animate-pulse" />
            </div>
            <span className="text-zinc-500 text-[7px] font-black uppercase tracking-wider">ERS CHARGE</span>
            <span className="text-emerald-400 text-xs font-black lcd-text leading-none mt-1" style={{ '--glow-color': 'rgba(16, 185, 129, 0.3)' } as any}>
              {telemetry.ers}%
            </span>
          </div>

          {/* DRS Status Card */}
          <div className="ferrari-panel premium-border">
            <div className="absolute top-1 right-1 flex items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full animate-pulse ${
                telemetry.drs === "ACTIVE" ? "led-glow-green" : telemetry.drs === "AVAILABLE" ? "led-glow-green" : "bg-zinc-700 shadow-none"
              }`} />
            </div>
            <span className="text-zinc-500 text-[7px] font-black uppercase tracking-wider">DRS STATUS</span>
            <span className={`text-xs font-black lcd-text leading-none mt-1 ${
              telemetry.drs === "ACTIVE" ? "text-emerald-400" : telemetry.drs === "AVAILABLE" ? "text-[#FFDC00]" : "text-zinc-500"
            }`} style={{ '--glow-color': telemetry.drs === "ACTIVE" ? 'rgba(16, 185, 129, 0.3)' : telemetry.drs === "AVAILABLE" ? 'rgba(251, 191, 36, 0.3)' : 'rgba(113, 113, 122, 0.1)' } as any}>
              {telemetry.drs}
            </span>
          </div>
        </div>

        <div className="bg-white/[0.02] p-1.5 rounded border border-white/5 flex justify-between items-center text-[9px] font-mono leading-none">
          <div>
            <span className="text-zinc-500 uppercase text-[7px] font-bold">LAP</span>
            <span className="text-white font-bold ml-1">{telemetry.lap}/57</span>
          </div>
          <div className="border-l border-white/10 pl-2">
            <span className="text-zinc-500 uppercase text-[7px] font-bold">GAP</span>
            <span className="text-[#FFDC00] font-bold ml-1">+{telemetry.gap}s</span>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-white/10 relative z-10">
        <button
          type="button"
          onClick={onSignOut}
          className="w-full flex items-center justify-center gap-2 py-2 rounded bg-red-950/20 hover:bg-red-950/40 border border-red-550/20 hover:border-red-550/40 text-red-400 hover:text-red-300 text-xs font-mono font-black transition-all duration-200 cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.4)]"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>SIGN OUT</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[#050507] text-white flex font-sans antialiased transition-colors duration-200">
      <aside className="hidden lg:flex w-64 carbon-texture border-r border-white/5 shadow-[5px_0_25px_rgba(0,0,0,0.6)] flex flex-col justify-between shrink-0 p-4 space-y-6 select-none transition-colors duration-200 premium-border">
        {renderSidebarContent(false)}
      </aside>

      {mobileSidebarOpen && (
        <div 
          className="fixed inset-0 z-50 lg:hidden flex"
          role="dialog"
          aria-modal="true"
        >
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div 
            ref={drawerRef}
            className="fixed inset-y-0 left-0 w-64 carbon-texture border-r border-white/5 p-4 flex flex-col justify-between space-y-6 shadow-2xl z-50 animate-slideIn"
          >
            {renderSidebarContent(true)}
          </div>
        </div>
      )}

      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-20 px-4 sm:px-6 lg:px-10 border-b border-white/5 bg-[#09090b]/85 backdrop-blur-xl flex items-center justify-between shrink-0 sticky top-0 z-20 shadow-[0_6px_30px_rgba(0,0,0,0.5)] relative overflow-hidden">
          {/* Glossy top line */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          {/* Active indicator line */}
          <div className="absolute bottom-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-[#FF1B1B]/70 to-transparent" />
          
          <div className="flex items-center gap-2 sm:gap-3 z-10">
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded border border-white/10 text-zinc-400 hover:text-white hover:bg-white/5 transition-all"
              aria-label="Open navigation menu"
            >
              <Menu className="h-4 w-4" />
            </button>
            <h2 className="text-xs sm:text-sm font-mono font-black text-white uppercase tracking-widest bg-[#121215] border border-white/10 px-3.5 py-2 rounded-md shadow-[inset_0_1.5px_3px_rgba(0,0,0,0.6)]">
              <span className="text-[#FF1B1B] mr-2">{"//"}</span>
              {activeTab.replace("-", " ")}
            </h2>
            <span className="text-xs text-zinc-800 font-mono">|</span>
            <div className="flex items-center gap-1.5 text-[9px] text-[#FFDC00] font-mono uppercase tracking-widest hidden sm:flex font-black bg-[#121215] border border-white/5 px-2.5 py-1.5 rounded shadow-[inset_0_1px_2px_rgba(0,0,0,0.5)]">
              <span className="h-2 w-2 rounded-full led-glow-green" />
              <span>CONSOLE MODE: ACTIVE</span>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4 z-10">
            {/* Notification Hub Bell with Aviation aesthetic */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 rounded border border-white/10 bg-black/40 text-zinc-400 hover:text-white hover:border-white/20 transition-all cursor-pointer relative shadow-[inset_0_1px_2px_rgba(255,255,255,0.05)]"
                title="Notifications"
                aria-label="Notification Hub"
              >
                <Bell className="h-3.5 w-3.5" />
                {notifications.some(n => !n.read) && (
                  <span className="absolute top-1 right-1 h-1.5 w-1.5 bg-[#FF1B1B] rounded-full animate-ping" />
                )}
                {notifications.some(n => !n.read) && (
                  <span className="absolute top-1 right-1 h-1.5 w-1.5 bg-[#FF1B1B] rounded-full" />
                )}
              </button>

              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-zinc-955/95 border border-white/15 rounded-lg shadow-2xl p-4 z-50 space-y-3 font-mono">
                  <div className="flex justify-between items-center border-b border-white/10 pb-2">
                    <span className="text-[10px] font-black text-[#FFDC00] uppercase tracking-widest">
                      MSG QUEUE ({notifications.filter(n => !n.read).length})
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
                      }}
                      className="text-[9px] text-[#FF1B1B] font-mono hover:underline font-bold uppercase tracking-wider"
                    >
                      Clear All
                    </button>
                  </div>

                  <div className="max-h-60 overflow-y-auto space-y-2.5 pr-1">
                    {notifications.length === 0 ? (
                      <div className="py-6 text-center text-zinc-550 text-xs font-mono italic">
                        No recent notifications.
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`p-2.5 rounded border text-xs leading-normal transition-all ${
                            n.read
                              ? "bg-white/[0.02] border-white/5 text-zinc-400"
                              : "bg-[#FF1B1B]/10 border-[#FF1B1B]/25 text-white font-medium"
                          }`}
                        >
                          <div className="flex justify-between items-start gap-2 mb-1">
                            <span className="text-[8px] font-mono font-bold text-[#FFDC00] uppercase tracking-wide">
                              {n.type || "ALERT"}
                            </span>
                            <span className="text-[8px] font-mono text-zinc-500">
                              {n.timestamp}
                            </span>
                          </div>
                          <p>{n.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded border border-white/10 bg-black/40 text-zinc-400 hover:text-white hover:border-white/20 transition-all cursor-pointer focus:outline-none shadow-[inset_0_1px_2px_rgba(255,255,255,0.05)]"
              title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
              aria-label="Toggle Theme"
            >
              {mounted && (theme === "light" ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />)}
            </button>

            <button
              type="button"
              onClick={onSync}
              className="p-2 rounded bg-black/40 border border-white/10 text-zinc-400 hover:text-white hover:border-white/20 transition-all cursor-pointer focus:outline-none shadow-[inset_0_1px_2px_rgba(255,255,255,0.05)]"
              title="Sync Data Flow"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>

            {/* Glowing aviation connect LEDs */}
            <div className="text-right bg-black/40 border border-white/5 px-3 py-1.5 rounded shadow-[inset_0_1px_2px_rgba(255,255,255,0.05)] flex flex-col justify-center">
              <span className="text-[8px] text-zinc-500 block uppercase tracking-widest font-black">Sync Status</span>
              <span className={`text-[9px] ${
                health === "green" 
                  ? "text-emerald-400" 
                  : health === "yellow" 
                  ? "text-amber-400" 
                  : "text-red-500"
              } font-black block flex items-center justify-end gap-1.5 font-mono uppercase tracking-wider`}>
                <span className={`h-1.5 w-1.5 rounded-full ${
                  health === "green" 
                    ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" 
                    : health === "yellow" 
                    ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" 
                    : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"
                } animate-pulse`} /> 
                {health === "green" ? "CONNECTED" : health === "yellow" ? "DEGRADED" : "DOWN"}
              </span>
            </div>
          </div>
        </header>

        <div className="flex-1 p-4 sm:p-6 lg:p-10 bg-[#070709] relative overflow-y-auto bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900/50 via-[#070709] to-[#070709]">
          {children}
        </div>
      </main>
    </div>
  );
}

// ── Main Dashboard Component ──────────────────────────────────────────────────
export default function Dashboard() {
  const { activeTab, setActiveTab, user, alertsCount, triggerRefresh, logout, addToast, hydrateStore, isHydrated } = useStore();
  const [usernameInput, setUsernameInput] = useState("admin");
  const [passwordInput, setPasswordInput] = useState("admin123");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [fullNameInput, setFullNameInput] = useState("");
  const [roleInput, setRoleInput] = useState("analyst");
  const [sessionStatus, setSessionStatus] = useState<"pending" | "valid" | "anonymous">("pending");

  useEffect(() => {
    setMounted(true);
    hydrateStore();
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("register") === "true") {
        setIsRegistering(true);
      }
    }
  }, [hydrateStore]);

  // Validate the cached session before protected dashboard views can issue requests.
  useEffect(() => {
    if (!mounted || !isHydrated) return;

    if (!user?.token) {
      setSessionStatus("anonymous");
      return;
    }

    setSessionStatus("pending");
    api.getCurrentUser()
      .then((data) => {
        localStorage.setItem("full_name", data.full_name || "");
        useStore.getState().setUser({
          fullName: data.full_name,
          role: data.role,
          username: data.username
        });
        setSessionStatus("valid");
      })
      .catch(() => {
        setSessionStatus("anonymous");
      });
  }, [mounted, isHydrated, user?.token]);

  if (!mounted || !isHydrated || sessionStatus === "pending") {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center text-zinc-500 dark:text-zinc-400 font-mono text-xs uppercase tracking-widest">
        Connecting to Command Center...
      </div>
    );
  }

  if (sessionStatus === "anonymous" || !user || !user.token) {
    const handleLogin = async (e: React.FormEvent) => {
      e.preventDefault();
      setLoading(true);
      setAuthError("");
      try {
        const formData = new FormData();
        formData.append("username", usernameInput);
        formData.append("password", passwordInput);
        await api.login(formData);
        
        useStore.setState({
          user: {
            token: localStorage.getItem("token"),
            username: localStorage.getItem("username"),
            role: localStorage.getItem("role"),
            fullName: localStorage.getItem("full_name"),
          }
        });
      } catch (err: any) {
        setAuthError(err.message || "Invalid credentials");
      } finally {
        setLoading(false);
      }
    };

    const handleRegister = async (e: React.FormEvent) => {
      e.preventDefault();
      setLoading(true);
      setAuthError("");
      try {
        if (!emailInput.includes("@")) {
          throw new Error("Please enter a valid email address.");
        }
        if (usernameInput.length < 3) {
          throw new Error("Username must be at least 3 characters.");
        }
        if (fullNameInput.length < 2) {
          throw new Error("Full name must be at least 2 characters.");
        }
        if (passwordInput.length < 6) {
          throw new Error("Password must be at least 6 characters.");
        }
        await api.register({
          email: emailInput,
          username: usernameInput.toLowerCase().trim(),
          full_name: fullNameInput.trim(),
          password: passwordInput,
          role: roleInput
        });
        addToast(`User ${usernameInput} registered successfully. Please login.`, "success");
        setIsRegistering(false);
        setEmailInput("");
        setRoleInput("analyst");
      } catch (err: any) {
        addToast(err.message || "Registration failed.", "error");
        setAuthError(err.message || "Registration failed.");
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="min-h-screen flex items-center justify-center bg-[#050507] px-4 text-zinc-100 font-sans relative overflow-hidden">
        {/* Animated grid background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f1f23_1px,transparent_1px),linear-gradient(to_bottom,#1f1f23_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-10 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#050507] via-transparent to-transparent pointer-events-none" />

        {/* Outer glowing border ring */}
        <div className="w-full max-w-sm bg-[#0c0c0f]/80 border-2 border-zinc-800 hover:border-[#E10600]/80 p-8 space-y-6 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.8)] hover:shadow-[0_0_30px_rgba(225,6,0,0.15)] transition-all duration-500 backdrop-blur-lg relative">
          
          {/* Scuderia Red/Yellow Accent top line */}
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-red-600 via-yellow-500 to-red-600 rounded-t-2xl" />

          {/* Scuderia Ferrari Shield Icon */}
          <div className="flex justify-center">
            <div className="p-2.5 rounded bg-[#FFDC00] border border-black shadow-md flex items-center justify-center shrink-0 w-12 h-12 font-mono font-extrabold text-black text-lg select-none tracking-tight">
              SF
            </div>
          </div>

          <div className="space-y-1 text-center">
            <h1 className="text-xl font-mono font-black tracking-widest text-white"><span className="text-[#E10600]">SCUDERIA</span> RETAIL</h1>
            <p className="text-[9px] text-zinc-400 font-mono uppercase tracking-widest block font-bold">
              {isRegistering ? "Crew Provision Portal" : "PIT WALL AUTHORIZATION"}
            </p>
          </div>

          {authError && (
            <div className="p-3 rounded bg-red-955/30 border border-[#E10600]/30 text-red-400 text-xs text-center font-mono leading-relaxed">
              <span className="font-bold text-red-500 mr-1">!]</span> {authError}
            </div>
          )}

          {isRegistering ? (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-zinc-455 uppercase tracking-wider block">Email Address</label>
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                  placeholder="crew@scuderia-retail.com"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-zinc-455 uppercase tracking-wider block">Username</label>
                <input
                  type="text"
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                  placeholder="username"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-zinc-455 uppercase tracking-wider block">Full Name</label>
                <input
                  type="text"
                  value={fullNameInput}
                  onChange={(e) => setFullNameInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                  placeholder="Full Name"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-zinc-455 uppercase tracking-wider block">Password</label>
                <input
                  type="password"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                  placeholder="••••••••"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-zinc-455 uppercase tracking-wider block">Role / Clearance</label>
                <select
                  value={roleInput}
                  onChange={(e) => setRoleInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-200 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                >
                  <option value="analyst">Crew Analyst</option>
                  <option value="manager">Race Manager</option>
                  <option value="director">Technical Director</option>
                  <option value="admin">Pit Administrator</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-lg bg-gradient-to-r from-red-700 via-red-600 to-red-700 hover:from-red-600 hover:to-red-500 disabled:from-zinc-800 disabled:to-zinc-850 disabled:opacity-50 text-white font-mono font-bold text-xs uppercase tracking-widest transition-all duration-300 cursor-pointer shadow-[0_0_15px_rgba(225,6,0,0.2)]"
              >
                {loading ? "PROVISIONING..." : "CREATE ACCOUNT"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-[#E10600] uppercase tracking-wider block">Crew Identifier</label>
                <input
                  type="text"
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                  placeholder="username"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[9px] font-mono font-bold text-[#E10600] uppercase tracking-wider block">Passkey</label>
                <input
                  type="password"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#121216] border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-650 focus:outline-none focus:border-[#E10600] font-sans transition-all"
                  placeholder="••••••••"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-lg bg-gradient-to-r from-red-700 via-red-600 to-red-700 hover:from-red-600 hover:to-red-500 disabled:from-zinc-800 disabled:to-zinc-850 disabled:opacity-50 text-white font-mono font-bold text-xs uppercase tracking-widest transition-all duration-300 cursor-pointer shadow-[0_0_15px_rgba(225,6,0,0.2)]"
              >
                {loading ? "AUTHENTICATING..." : "ACCESS PIT WALL"}
              </button>
            </form>
          )}

          <div className="text-center pt-3 border-t border-zinc-900">
            <button
              onClick={() => {
                setIsRegistering(!isRegistering);
                setAuthError("");
              }}
              className="text-[9px] text-[#E10600] hover:underline font-mono font-bold uppercase tracking-wider cursor-pointer"
            >
              {isRegistering ? "← Return to Login" : "Provision New Account →"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Purely inline client route dispatcher to ensure zero hydration lag
  const renderCurrentView = () => {
    switch (activeTab) {
      case "executive": return <ExecutiveBriefingView />;
      case "accuracy": return <ForecastAccuracyView />;
      case "action-center": return <ActionCenterView />;
      case "scenario-lab": return <ScenarioLabView />;
      case "reorder": return <ReorderEngineView />;
      case "product-intelligence": return <ProductIntelligenceView />;
      case "copilot": return <CopilotView />;
      case "warehouses": return <WarehouseView />;
      case "purchase-orders": return <PurchaseOrderView />;
      case "datasets": return <DatasetUploadView />;
      case "users": return <UserManagementView />;
      case "audit-logs": return <AuditLogsView />;
      default: return <ExecutiveBriefingView />;
    }
  };

  return (
    <>
      <ToastContainer />
      <CommandCenterLayout
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        alertsCount={alertsCount}
        onSync={triggerRefresh}
        onSignOut={logout}
      >
        {renderCurrentView()}
      </CommandCenterLayout>
    </>
  );
}
