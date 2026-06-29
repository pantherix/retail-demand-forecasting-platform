"use client";

import { useCallback, useEffect, useState } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { Search, Download, RefreshCw } from "lucide-react";
import { CardSkeleton } from "../ui/CardSkeleton";

const ACTION_COLORS: Record<string, string> = {
  import:        "bg-blue-900/50 border-blue-700/60 text-blue-300",
  delete_dataset:"bg-red-900/50 border-red-700/60 text-red-300",
  cleanup:       "bg-yellow-900/40 border-yellow-700/50 text-yellow-300",
  login:         "bg-green-900/40 border-green-700/50 text-green-300",
  logout:        "bg-zinc-800 border-zinc-700 text-zinc-400",
  retrain:       "bg-purple-900/40 border-purple-700/50 text-purple-300",
  approve:       "bg-emerald-900/40 border-emerald-700/50 text-emerald-300",
  reject:        "bg-rose-900/40 border-rose-700/50 text-rose-300",
};

function actionBadgeClass(action: string) {
  if (!action) return "bg-zinc-800 border-zinc-700 text-zinc-400";
  const key = action.toLowerCase();
  for (const [k, v] of Object.entries(ACTION_COLORS)) {
    if (key.includes(k)) return v;
  }
  return "bg-zinc-800 border-zinc-700 text-zinc-300";
}

export default function AuditLogsView() {
  const refreshTrigger = useStore((state) => state.refreshTrigger);
  const { addToast } = useToast();

  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedAction, setSelectedAction] = useState("");
  const [selectedUser, setSelectedUser] = useState("");

  const [uniqueActions, setUniqueActions] = useState<string[]>([]);
  const [uniqueUsers, setUniqueUsers] = useState<string[]>([]);

  // ── Fetch audit logs ──────────────────────────────────────────────────────
  const fetchLogs = useCallback(() => {
    setLoading(true);
    api
      .getAuditLogs({ action: selectedAction, user: selectedUser, search })
      .then((res) => {
        const data = Array.isArray(res) ? res : [];
        setLogs(data);
        if (!selectedAction && !selectedUser && !search) {
          const actions = Array.from(
            new Set(data.map((l: any) => l.action).filter(Boolean))
          ) as string[];
          const users = Array.from(
            new Set(data.map((l: any) => l.user).filter(Boolean))
          ) as string[];
          setUniqueActions(actions.sort());
          setUniqueUsers(users.sort());
        }
        setLoading(false);
      })
      .catch((err: any) => {
        addToast(err.message || "Failed to retrieve audit logs.", "error");
        setLoading(false);
      });
  }, [selectedAction, selectedUser, search, addToast]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs, refreshTrigger]);

  // ── Reset Prometheus telemetry counters ───────────────────────────────────
  const handleResetTelemetry = async () => {
    try {
      const baseUrl =
        typeof window !== "undefined"
          ? (window.location.host.includes("localhost:3000") || window.location.host.includes("127.0.0.1:3000")
              ? "http://127.0.0.1:8000"
              : "")
          : process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/api/reset_telemetry`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed: ${res.status}`);
      }
      addToast("Telemetry metrics have been reset to zero.", "success");
      fetchLogs();
    } catch (err: any) {
      addToast(err.message || "Failed to reset telemetry.", "error");
    }
  };

  // ── CSV Export ────────────────────────────────────────────────────────────
  const handleExportCSV = () => {
    if (logs.length === 0) {
      addToast("No logs available to export.", "error");
      return;
    }
    const headers = ["Timestamp", "Operator", "Action", "Resource Target", "Details", "IP Address"];
    const rows = logs.map((log) => [
      log.timestamp,
      log.user,
      log.action,
      log.resource,
      log.detail,
      log.ip_address,
    ]);
    const csvString = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((val) => `"${(val || "").toString().replace(/"/g, '""')}"`)
          .join(",")
      ),
    ].join("\n");
    const blob = new Blob(["\ufeff" + csvString], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `audit_trail_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    addToast("Audit log exported to CSV successfully.", "success");
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-6xl mx-auto space-y-6 py-2">

      {/* ── Title Header ── */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 border-b border-zinc-800 pb-5">
        <div>
          <h2 className="text-xl font-mono font-bold tracking-tight text-white uppercase flex items-center gap-2">
            System Audit Trail
          </h2>
          <p className="text-xs text-zinc-500 mt-1">
            Browse and download the immutable record of supply chain and configuration modifications.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleExportCSV}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-mono font-bold cursor-pointer transition-colors shadow-sm self-start sm:self-auto"
          >
            <Download className="h-3.5 w-3.5" />
            <span>EXPORT CSV</span>
          </button>
          <button
            type="button"
            onClick={handleResetTelemetry}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-mono font-bold cursor-pointer transition-colors shadow-sm self-start sm:self-auto"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>RESET TELEMETRY</span>
          </button>
        </div>
      </div>

      {/* ── Filter Control Bar ── */}
      <div className="bg-[#111114] border border-zinc-800 p-4 rounded-xl grid grid-cols-1 sm:grid-cols-4 gap-4">
        {/* Search */}
        <div className="relative sm:col-span-2">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search details, SKU, or user..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-xs placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-[#DC2626] font-mono text-zinc-200"
          />
        </div>
        {/* Action filter */}
        <select
          value={selectedAction}
          onChange={(e) => setSelectedAction(e.target.value)}
          className="px-3 py-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-[#DC2626] font-mono"
        >
          <option value="">All Actions</option>
          {uniqueActions.map((action) => (
            <option key={action} value={action}>
              {action}
            </option>
          ))}
        </select>
        {/* User filter */}
        <select
          value={selectedUser}
          onChange={(e) => setSelectedUser(e.target.value)}
          className="px-3 py-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-[#DC2626] font-mono"
        >
          <option value="">All Operators</option>
          {uniqueUsers.map((user) => (
            <option key={user} value={user}>
              {user}
            </option>
          ))}
        </select>
      </div>

      {/* ── Logs Table ── */}
      <div className="bg-[#0d0d10] border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
        {loading ? (
          <div className="p-8">
            <CardSkeleton />
          </div>
        ) : logs.length === 0 ? (
          <div className="py-20 text-center text-zinc-500 font-mono text-xs italic">
            No audit records match your search parameters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse hardware-table">
              <thead>
                <tr className="border-b border-zinc-800 bg-[#050507] text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-widest">
                  <th className="py-3.5 px-4">Timestamp</th>
                  <th className="py-3.5 px-4">Operator</th>
                  <th className="py-3.5 px-4">Action</th>
                  <th className="py-3.5 px-4">Resource</th>
                  <th className="py-3.5 px-4">Details</th>
                  <th className="py-3.5 px-4">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60 text-xs font-mono">
                {logs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-zinc-800/20 transition-colors"
                  >
                    <td className="py-3.5 px-4 text-[10px] text-zinc-500 shrink-0 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-zinc-100">
                      {log.user}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-mono font-semibold uppercase tracking-wider ${actionBadgeClass(log.action)}`}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-zinc-400">
                      {log.resource}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-zinc-300 leading-normal max-w-sm sm:max-w-md truncate md:whitespace-normal">
                      {log.detail}
                    </td>
                    <td className="py-3.5 px-4 text-zinc-500">
                      {log.ip_address}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
