"use client";

import { useEffect, useState, ReactNode, useRef } from "react";
import { useStore } from "./store";
import { api } from "./api";
import { useTheme } from "../hooks/useTheme";
import {
  Boxes, LogOut, RefreshCw, X, Menu, Sun, Moon
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

  useEffect(() => {
    setMounted(true);
  }, []);

  const navItems: Array<{ id: string; name: string; icon: any; badge?: number }> = [
    { id: "executive", name: "Command Brief", icon: RefreshCw },
    { id: "action-center", name: "Decision Center", icon: Boxes },
    { id: "scenario-lab", name: "Scenario Lab", icon: RefreshCw },
    { id: "reorder", name: "Reorder Engine", icon: Boxes },
    { id: "copilot", name: "Decision Copilot", icon: Boxes },
    { id: "warehouses", name: "Warehouse Network", icon: Boxes },
    { id: "purchase-orders", name: "PO Automation", icon: Boxes },
  ];

  // Map the navigation items to their lucide icons properly for backward compatibility
  // (the icons are dynamically imported or matched)
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
      <div className="flex flex-col space-y-6">
        <div className="h-16 px-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
              <Boxes className="h-4 w-4 text-zinc-850 dark:text-zinc-200" />
            </div>
            <div>
              <span className="font-bold text-zinc-950 dark:text-zinc-50 text-sm tracking-tight block">RETAILGPT</span>
              <span className="text-[9px] text-zinc-400 dark:text-zinc-500 font-mono uppercase tracking-widest block">Command Center</span>
            </div>
          </div>
          {isMobile && (
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(false)}
              className="p-1.5 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-850"
              aria-label="Close navigation menu"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="p-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 rounded flex items-center gap-2.5">
          <div className="h-8 w-8 rounded bg-zinc-200 dark:bg-zinc-850 flex items-center justify-center font-mono font-bold text-zinc-750 dark:text-zinc-300 text-xs shrink-0">
            {user.username?.charAt(0).toUpperCase() || "A"}
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-bold text-zinc-955 dark:text-zinc-50 block truncate">{user.fullName}</span>
            <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono block truncate capitalize">{user.role}</span>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
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
                    ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-955 dark:text-zinc-50" 
                    : "text-zinc-500 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-850 hover:text-zinc-955 dark:hover:text-zinc-50"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Boxes className={`h-4 w-4 ${isActive ? "text-zinc-955 dark:text-zinc-50" : "text-zinc-400 dark:text-zinc-500"}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && item.badge > 0 ? (
                  <span className="px-1.5 py-0.5 rounded bg-red-50 dark:bg-red-955/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-900/50 text-[9px] font-mono font-bold">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800">
        <button
          type="button"
          onClick={onSignOut}
          className="w-full flex items-center justify-center gap-2 py-2 rounded bg-zinc-50 dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-850 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-zinc-955 dark:hover:text-zinc-50 text-xs font-mono font-bold transition-all cursor-pointer"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>SIGN OUT</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-955 dark:text-zinc-50 flex font-sans antialiased transition-colors duration-200">
      <aside className="hidden lg:flex w-64 bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-850 flex flex-col justify-between shrink-0 p-4 space-y-6 select-none transition-colors duration-200">
        {renderSidebarContent(false)}
      </aside>

      {mobileSidebarOpen && (
        <div 
          className="fixed inset-0 z-50 lg:hidden flex"
          role="dialog"
          aria-modal="true"
        >
          <div 
            className="fixed inset-0 bg-zinc-900/50 dark:bg-zinc-955/70 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div 
            ref={drawerRef}
            className="fixed inset-y-0 left-0 w-64 bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 p-4 flex flex-col justify-between space-y-6 shadow-xl z-50 animate-slideIn"
          >
            {renderSidebarContent(true)}
          </div>
        </div>
      )}

      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-20 px-4 sm:px-6 lg:px-10 border-b border-zinc-200/60 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between shrink-0 sticky top-0 z-20 transition-colors duration-200">
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded border border-zinc-200 dark:border-zinc-800 text-zinc-650 dark:text-zinc-400 hover:text-zinc-955 dark:hover:text-white"
              aria-label="Open navigation menu"
            >
              <Menu className="h-4 w-4" />
            </button>
            <h2 className="text-xs sm:text-sm font-mono font-bold text-zinc-950 dark:text-zinc-50 uppercase tracking-wider">{activeTab.replace("-", " ")}</h2>
            <span className="text-xs text-zinc-350 dark:text-zinc-700">|</span>
            <span className="text-[9px] text-zinc-400 dark:text-zinc-500 font-mono uppercase tracking-widest hidden sm:inline">Single Action Focus</span>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-650 dark:text-zinc-400 hover:text-zinc-955 dark:hover:text-white transition-all cursor-pointer focus:outline-none"
              title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
              aria-label="Toggle Theme"
            >
              {mounted && (theme === "light" ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />)}
            </button>

            <button
              type="button"
              onClick={onSync}
              className="p-2 rounded bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 text-zinc-600 dark:text-zinc-400 hover:text-zinc-955 dark:hover:text-white hover:border-zinc-305 dark:hover:border-zinc-700 transition-all cursor-pointer focus:outline-none"
              title="Sync Data Flow"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
            <div className="text-right">
              <span className="text-[9px] text-zinc-405 dark:text-zinc-500 block uppercase tracking-widest font-mono">Sync Status</span>
              <span className="text-[10px] text-green-600 dark:text-green-400 font-bold block flex items-center justify-end gap-1 font-mono uppercase">
                <span className="h-1.5 w-1.5 rounded-full bg-green-500 dark:bg-green-400 animate-pulse" /> Connected
              </span>
            </div>
          </div>
        </header>

        {/* Responsive view spacing container */}
        <div className="flex-1 p-4 sm:p-6 lg:p-10 bg-zinc-50/30 dark:bg-zinc-950/20">
          {children}
        </div>
      </main>
    </div>
  );
}

// ── Active View Router ────────────────────────────────────────────────────────
function RenderActiveView() {
  const { activeTab } = useStore();

  switch (activeTab) {
    case "executive":
      return <ExecutiveBriefingView />;
    case "action-center":
      return <ActionCenterView />;
    case "scenario-lab":
      return <ScenarioLabView />;
    case "reorder":
      return <ReorderEngineView />;
    case "product-intelligence":
      return <ProductIntelligenceView />;
    case "copilot":
      return <CopilotView />;
    case "warehouses":
      return <WarehouseView />;
    case "purchase-orders":
      return <PurchaseOrderView />;
    default:
      return <ExecutiveBriefingView />;
  }
}

// ── Main Dashboard Component ──────────────────────────────────────────────────
export default function Dashboard() {
  const { activeTab, setActiveTab, user, alertsCount, refreshTrigger, triggerRefresh, logout } = useStore();
  const [usernameInput, setUsernameInput] = useState("admin");
  const [passwordInput, setPasswordInput] = useState("admin123");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center text-zinc-500 dark:text-zinc-400 font-mono text-xs uppercase tracking-widest">
        Connecting to Command Center...
      </div>
    );
  }

  if (!user.token) {
    // Clean Minimal Login
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

    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 px-4">
        <div className="w-full max-w-sm bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-8 space-y-6 rounded-lg shadow-sm">
          <div className="space-y-1 text-center">
            <h1 className="text-2xl font-extrabold tracking-tight text-zinc-900 dark:text-zinc-50 font-sans">RETAILGPT</h1>
            <p className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono uppercase tracking-widest">Command Cockpit</p>
          </div>

          {authError && (
            <div className="p-3 rounded bg-red-50 dark:bg-red-955/20 border border-red-200 dark:border-red-900/40 text-red-700 dark:text-red-400 text-xs text-center font-mono">
              {authError}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1">
              <label className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-550 uppercase tracking-wider block animate-pulse-slow">Username</label>
              <input
                type="text"
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-zinc-850 border border-zinc-205 dark:border-zinc-750 rounded text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-450 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100 focus:ring-0 font-sans"
                placeholder="admin"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-550 uppercase tracking-wider block">Password</label>
              <input
                type="password"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-zinc-855 border border-zinc-205 dark:border-zinc-755 rounded text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-450 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-900 dark:focus:border-zinc-100 focus:ring-0 font-sans"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-950 text-white font-mono font-bold text-xs uppercase tracking-wider transition-colors cursor-pointer mt-2 disabled:opacity-50"
            >
              {loading ? "Authenticating..." : "Access Cockpit"}
            </button>
          </form>

          <div className="text-center pt-2">
            <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">Demo: admin / admin123</span>
          </div>
        </div>
      </div>
    );
  }

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
        <RenderActiveView />
      </CommandCenterLayout>
    </>
  );
}
