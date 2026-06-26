"use client";

import { useEffect, useState } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { Search, Download, RefreshCw } from "lucide-react";
import { CardSkeleton } from "../ui/CardSkeleton";

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

  const fetchLogs = () => {
    setLoading(true);
    api.getAuditLogs({ action: selectedAction, user: selectedUser, search })
      .then((res) => {
        const data = Array.isArray(res) ? res : [];
        setLogs(data);
        
        // Extract unique actions and users on initial load for dropdown filters
        if (!selectedAction && !selectedUser && !search) {
          const actions = Array.from(new Set(data.map((l: any) => l.action).filter(Boolean))) as string[];
          const users = Array.from(new Set(data.map((l: any) => l.user).filter(Boolean))) as string[];
          setUniqueActions(actions.sort());
          setUniqueUsers(users.sort());
        }
        setLoading(false);
      })
      .catch((err: any) => {
        addToast(err.message || "Failed to retrieve audit logs.", "error");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchLogs();
  }, [selectedAction, selectedUser, search, refreshTrigger]);

  const handleExportCSV = () => {
    if (logs.length === 0) {
      addToast("No logs available to export.", "error");
      return;
    }

    const headers = ["Timestamp", "Operator", "Action", "Resource Target", "Details", "IP Address"];
    const rows = logs.map(log => [
      log.timestamp,
      log.user,
      log.action,
      log.resource,
      log.detail,
      log.ip_address
    ]);

    const csvString = [
      headers.join(","),
      ...rows.map(row => row.map(val => `"${(val || "").toString().replace(/"/g, '""')}"`).join(","))
    ].join("\n");

    const blob = new Blob(["\ufeff" + csvString], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `audit_trail_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast("Audit log exported to CSV successfully.", "success");
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 py-2">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 border-b border-zinc-200 dark:border-[#27272A] pb-5">
        <div>
          <h2 className="text-xl font-mono font-bold tracking-tight text-zinc-900 dark:text-white uppercase flex items-center gap-2">
            System Audit Trail
          </h2>
          <p className="text-xs text-zinc-500 mt-1">
            Browse and download the immutable record of supply chain and configuration modifications.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExportCSV}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded bg-zinc-950 hover:bg-zinc-800 dark:bg-[#DC2626] dark:hover:bg-[#B91C1C] text-white text-xs font-mono font-bold cursor-pointer transition-colors shadow-sm self-start sm:self-auto"
        >
          <Download className="h-3.5 w-3.5" />
          <span>EXPORT CSV</span>
        </button>
      </div>

      {/* Filter Control Bar */}
      <div className="bg-white dark:bg-[#18181B] border border-zinc-200 dark:border-[#27272A] p-4 rounded-lg shadow-sm grid grid-cols-1 sm:grid-cols-4 gap-4">
        {/* Search */}
        <div className="relative sm:col-span-2">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Search details, SKU, or user..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-950 font-sans text-zinc-900 dark:text-white"
          />
        </div>

        {/* Action filter */}
        <select
          value={selectedAction}
          onChange={(e) => setSelectedAction(e.target.value)}
          className="px-3 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-zinc-950 font-mono"
        >
          <option value="">All Actions</option>
          {uniqueActions.map(action => (
            <option key={action} value={action}>{action}</option>
          ))}
        </select>

        {/* User filter */}
        <select
          value={selectedUser}
          onChange={(e) => setSelectedUser(e.target.value)}
          className="px-3 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-zinc-950 font-mono"
        >
          <option value="">All Operators</option>
          {uniqueUsers.map(user => (
            <option key={user} value={user}>{user}</option>
          ))}
        </select>
      </div>

      {/* Logs Table */}
      <div className="bg-white dark:bg-[#18181B] border border-zinc-200 dark:border-[#27272A] rounded-lg shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8">
            <CardSkeleton />
          </div>
        ) : logs.length === 0 ? (
          <div className="py-20 text-center text-zinc-400 font-mono text-xs italic">
            No audit records match your search parameters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Timestamp</th>
                  <th className="py-3.5 px-4">Operator</th>
                  <th className="py-3.5 px-4">Action</th>
                  <th className="py-3.5 px-4">Resource</th>
                  <th className="py-3.5 px-4">Details</th>
                  <th className="py-3.5 px-4">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800 text-xs font-mono text-zinc-650 dark:text-zinc-350">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/20 transition-colors">
                    <td className="py-3.5 px-4 text-[10px] text-zinc-400 shrink-0">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-zinc-900 dark:text-white">
                      {log.user}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-zinc-400">
                      {log.resource}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-zinc-800 dark:text-zinc-200 leading-normal max-w-sm sm:max-w-md truncate md:whitespace-normal">
                      {log.detail}
                    </td>
                    <td className="py-3.5 px-4 text-zinc-450 dark:text-zinc-500">
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
