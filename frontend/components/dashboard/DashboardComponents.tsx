"use client";

import { ReactNode, FormEvent } from "react";
import { UserCheck } from "lucide-react";

// ── ApprovalButton ───────────────────────────────────────────────────────────
interface ApprovalButtonProps {
  onClick: (e: any) => void;
  disabled?: boolean;
  children: ReactNode;
  variant?: "primary" | "secondary";
}

export function ApprovalButton({ onClick, disabled = false, children, variant = "primary" }: ApprovalButtonProps) {
  const baseClass = "font-mono text-xs uppercase font-bold rounded transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none shadow-sm hover:shadow active:translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-zinc-950 dark:focus:ring-zinc-300";
  const variantClass = variant === "primary"
    ? "px-5 py-3 bg-zinc-950 hover:bg-zinc-800 text-white dark:bg-[#DC2626] dark:hover:bg-[#B91C1C]"
    : "px-3 py-1.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-900 border border-zinc-200 dark:bg-[#18181B] dark:border-[#27272A] dark:hover:bg-zinc-800 dark:text-zinc-100";

  return (
    <button 
      type="button"
      onClick={onClick} 
      disabled={disabled} 
      className={`${baseClass} ${variantClass}`}
    >
      {children}
    </button>
  );
}

// ── RevenueImpactCard ─────────────────────────────────────────────────────────
interface RevenueImpactCardProps {
  title: string;
  value: number;
  variant?: "protected" | "risk" | "neutral" | "warning";
}

export function RevenueImpactCard({ title, value, variant = "neutral" }: RevenueImpactCardProps) {
  const bgClass =
    variant === "protected" ? "bg-emerald-950/20" :
    variant === "risk" ? "bg-red-950/20" :
    variant === "warning" ? "bg-amber-950/20" :
    "bg-[#111114]";

  const borderClass =
    variant === "protected" ? "border-emerald-900/40" :
    variant === "risk" ? "border-red-900/40" :
    variant === "warning" ? "border-amber-900/40" :
    "border-zinc-800";

  const textClass =
    variant === "protected" ? "text-green-400" :
    variant === "risk" ? "text-red-400" :
    variant === "warning" ? "text-amber-400" :
    "text-zinc-50";

  return (
    <div className={`${bgClass} border ${borderClass} p-6 rounded-lg shadow-sm space-y-1`}>
      <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-widest block">{title}</span>
      <h1 className={`${textClass} min-w-0 flex-1 whitespace-nowrap overflow-visible text-2xl md:text-3xl font-black tracking-tight font-sans`}>
        ₹{Number(value).toLocaleString('en-IN')}
      </h1>
    </div>
  );
}

// ── HeroActionCard ────────────────────────────────────────────────────────────
interface HeroActionCardProps {
  title: string;
  sku?: string;
  description: string;
  actionLabel: string;
  buttonText: string;
  colorClass: string;
  onExecute: () => void;
  onSkuClick?: () => void;
  disabled?: boolean;
}

export function HeroActionCard({
  title, sku, description, actionLabel, buttonText, colorClass, onExecute, onSkuClick, disabled = false
}: HeroActionCardProps) {
  return (
    <div className={`bg-[#0f0f13] border-l-4 ${colorClass} border-t border-r border-b border-zinc-800 p-8 rounded-lg shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6`}>
      <div className="space-y-3 max-w-xl">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[9px] font-bold uppercase text-zinc-600 dark:text-zinc-400">
            {actionLabel}
          </span>
          {sku && onSkuClick && (
            <button
              type="button"
              onClick={onSkuClick}
              className="text-xs font-mono font-bold text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200 underline cursor-pointer focus:outline-none"
            >
              {sku}
            </button>
          )}
        </div>
        <h2 className="text-2xl sm:text-3xl tracking-tight font-extrabold text-zinc-900 dark:text-zinc-50 leading-tight">{title}</h2>
        <p className="text-sm text-zinc-650 dark:text-zinc-350 leading-relaxed font-sans font-medium">{description}</p>
      </div>
      <div className="shrink-0">
        <ApprovalButton onClick={onExecute} disabled={disabled}>
          {buttonText}
        </ApprovalButton>
      </div>
    </div>
  );
}

// ── DecisionCard ──────────────────────────────────────────────────────────────
interface DecisionCardProps {
  sku: string;
  productName: string;
  issue: string;
  impact: number;
  type: string;
  owner: string;
  status: string;
  assignTargetSku: string | null;
  assignUser: string;
  noteTargetSku: string | null;
  noteText: string;
  onStatusChange: (s: string) => void;
  onAssignClick: () => void;
  onAssignSave: () => void;
  onAssignUserChange: (u: string) => void;
  onNoteClick: () => void;
  onNoteSave: () => void;
  onNoteCancel: () => void;
  onNoteTextChange: (t: string) => void;
  onExecute: () => void;
  onSkuClick: () => void;
  submitting?: boolean;
}

export function DecisionCard({
  sku, productName, issue, impact, status, owner,
  assignTargetSku, assignUser, noteTargetSku, noteText,
  onStatusChange, onAssignClick, onAssignSave, onAssignUserChange,
  onNoteClick, onNoteSave, onNoteCancel, onNoteTextChange, onExecute, onSkuClick,
  submitting = false
}: DecisionCardProps) {
  return (
    <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg flex flex-col justify-between gap-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors shadow-sm">
      <div className="space-y-3">
        <div className="flex justify-between items-start">
          <button 
            type="button"
            onClick={onSkuClick} 
            className="font-mono text-xs font-bold text-zinc-600 hover:text-zinc-950 dark:text-zinc-400 dark:hover:text-zinc-100 underline cursor-pointer focus:outline-none"
          >
            {sku}
          </button>
          <span className="text-sm font-mono font-bold text-zinc-950 dark:text-zinc-50">₹{impact.toLocaleString()}</span>
        </div>
        <div>
          <h3 className="text-base font-bold text-zinc-950 dark:text-zinc-50 leading-snug">{productName}</h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 leading-normal">{issue}</p>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-zinc-800 font-mono text-[10px] text-zinc-600 dark:text-zinc-400">
          <div>
            <span className="block uppercase text-[8px] text-zinc-400 dark:text-zinc-500">Owner</span>
            {assignTargetSku === sku ? (
              <div className="flex gap-1 items-center mt-1">
                <select
                  value={assignUser}
                  onChange={(e) => onAssignUserChange(e.target.value)}
                  className="bg-zinc-800 border border-zinc-700 text-[10px] rounded p-0.5 focus:outline-none text-zinc-100"
                >
                  <option value="admin">Admin</option>
                  <option value="manager">Manager</option>
                  <option value="analyst">Analyst</option>
                </select>
                <button 
                  type="button"
                  onClick={onAssignSave} 
                  className="text-[10px] bg-zinc-900 hover:bg-zinc-800 dark:bg-[#DC2626] dark:hover:bg-[#B91C1C] px-1 py-0.5 rounded text-white font-bold cursor-pointer"
                >
                  OK
                </button>
              </div>
            ) : (
              <button 
                type="button"
                onClick={onAssignClick} 
                className="hover:underline text-zinc-600 dark:text-zinc-300 font-bold text-left block mt-1 focus:outline-none"
              >
                {owner}
              </button>
            )}
          </div>
          <div>
            <span className="block uppercase text-[8px] text-zinc-400 dark:text-zinc-500">Status</span>
            <select
              value={status}
              onChange={(e) => onStatusChange(e.target.value)}
              className={`bg-zinc-800 border border-zinc-700 text-[10px] rounded px-1 mt-1 font-bold focus:outline-none ${
                status === "Resolved" ? "text-green-400" :
                status === "In Progress" ? "text-amber-400" :
                "text-zinc-400"
              }`}
            >
              <option value="Open">Open</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>
        </div>

        {/* Notes audit trail */}
        <div className="pt-2 border-t border-zinc-800">
          {noteTargetSku === sku ? (
            <div className="space-y-1.5">
              <textarea
                value={noteText}
                onChange={(e) => onNoteTextChange(e.target.value)}
                placeholder="Add comment..."
                className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-[10px] text-zinc-100 focus:outline-none"
              />
              <div className="flex gap-2">
                <button 
                  type="button"
                  onClick={onNoteSave} 
                  className="text-[9px] bg-zinc-950 dark:bg-[#DC2626] dark:hover:bg-[#B91C1C] px-2 py-1 rounded text-white font-mono font-bold cursor-pointer"
                >
                  Save Note
                </button>
                <button 
                  type="button"
                  onClick={onNoteCancel} 
                  className="text-[9px] bg-zinc-200 dark:bg-zinc-800 px-2 py-1 rounded text-zinc-600 dark:text-zinc-300 font-mono font-bold cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={onNoteClick}
              className="text-[10px] text-zinc-400 hover:text-zinc-950 dark:text-zinc-500 dark:hover:text-zinc-200 font-mono font-bold cursor-pointer underline focus:outline-none"
            >
              + Add note to audit log
            </button>
          )}
        </div>
      </div>

      {status !== "Resolved" && (
        <button
          type="button"
          onClick={onExecute}
          disabled={submitting}
          className="w-full py-2.5 mt-2 bg-[#DC2626] hover:bg-[#B91C1C] text-white font-mono text-xs uppercase font-bold tracking-wider rounded cursor-pointer transition-colors shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? "Executing..." : "Execute Action"}
        </button>
      )}
    </div>
  );
}

// ── ActionFeed ────────────────────────────────────────────────────────────────
interface AuditItem {
  title: string;
  message: string;
}

interface ActionFeedProps {
  audits: AuditItem[];
  title: string;
}

export function ActionFeed({ audits, title }: ActionFeedProps) {
  return (
    <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg space-y-4 shadow-sm">
      <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">{title}</span>
      <ul className="space-y-3.5 divide-y divide-zinc-200 dark:divide-zinc-800">
        {audits.map((audit, idx) => (
          <li key={`audit-${idx}`} className={`text-xs flex gap-3 ${idx === 0 ? "" : "pt-3.5"}`}>
            <UserCheck className="h-4.5 w-4.5 shrink-0 mt-0.5 text-zinc-400 dark:text-zinc-500" />
            <div className="space-y-0.5">
              <span className="font-bold text-zinc-955 dark:text-zinc-50 font-mono">{audit.title}</span>
              <p className="text-zinc-600 dark:text-zinc-400 leading-snug">{audit.message}</p>
            </div>
          </li>
        ))}
        {audits.length === 0 && (
          <li className="text-zinc-400 dark:text-zinc-500 italic font-mono text-center py-4">No logged outcomes today.</li>
        )}
      </ul>
    </div>
  );
}

// ── ScenarioPanel ─────────────────────────────────────────────────────────────
interface ScenarioPanelProps {
  demandChange: number;
  leadTimeChange: number;
  reliabilityChange: number;
  safetyStockMultiplier: number;
  leadTimeBuffer: number;
  loading: boolean;
  onDemandChange: (v: number) => void;
  onLeadTimeChange: (v: number) => void;
  onReliabilityChange: (v: number) => void;
  onSafetyStockMultiplierChange: (v: number) => void;
  onLeadTimeBufferChange: (v: number) => void;
  onSimulate: () => void;
  onReset: () => void;
}

export function ScenarioPanel({
  demandChange, leadTimeChange, reliabilityChange, safetyStockMultiplier, leadTimeBuffer, loading,
  onDemandChange, onLeadTimeChange, onReliabilityChange, onSafetyStockMultiplierChange, onLeadTimeBufferChange, onSimulate, onReset
}: ScenarioPanelProps) {
  return (
    <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg space-y-5 shadow-sm">
      <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Stress Twin Env Modifiers</span>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
        {/* Demand Shift */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono font-bold">
            <span className="text-zinc-500 dark:text-zinc-400 uppercase">Demand Shift</span>
            <span className={demandChange > 0 ? "text-red-600" : demandChange < 0 ? "text-green-600" : "text-zinc-700 dark:text-zinc-300"}>
              {demandChange > 0 ? `+${demandChange}` : demandChange}%
            </span>
          </div>
          <input
            type="range"
            min="-50"
            max="50"
            step="5"
            value={demandChange}
            onChange={(e) => onDemandChange(Number(e.target.value))}
            className="w-full accent-zinc-900 dark:accent-zinc-50 bg-zinc-200 dark:bg-zinc-800 h-1 rounded appearance-none cursor-pointer"
          />
        </div>

        {/* Lead Time Delay */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono font-bold">
            <span className="text-zinc-500 dark:text-zinc-400 uppercase">Lead Time Delay</span>
            <span className={leadTimeChange > 0 ? "text-red-600" : "text-zinc-700 dark:text-zinc-300"}>
              {leadTimeChange > 0 ? `+${leadTimeChange}` : leadTimeChange} days
            </span>
          </div>
          <input
            type="range"
            min="-10"
            max="10"
            step="1"
            value={leadTimeChange}
            onChange={(e) => onLeadTimeChange(Number(e.target.value))}
            className="w-full accent-zinc-900 dark:accent-zinc-50 bg-zinc-200 dark:bg-zinc-800 h-1 rounded appearance-none cursor-pointer"
          />
        </div>

        {/* Supplier Reliability */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono font-bold">
            <span className="text-zinc-500 dark:text-zinc-400 uppercase">Supplier Performance</span>
            <span className={reliabilityChange < 0 ? "text-red-600" : "text-zinc-700 dark:text-zinc-300"}>
              {reliabilityChange > 0 ? `+${reliabilityChange}` : reliabilityChange}%
            </span>
          </div>
          <input
            type="range"
            min="-50"
            max="50"
            step="5"
            value={reliabilityChange}
            onChange={(e) => onReliabilityChange(Number(e.target.value))}
            className="w-full accent-zinc-900 dark:accent-zinc-50 bg-zinc-200 dark:bg-zinc-800 h-1 rounded appearance-none cursor-pointer"
          />
        </div>

        {/* Safety Stock Multiplier */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono font-bold">
            <span className="text-zinc-500 dark:text-zinc-400 uppercase">Safety Stock Mult.</span>
            <span className={safetyStockMultiplier > 1.0 ? "text-green-600" : safetyStockMultiplier < 1.0 ? "text-red-600" : "text-zinc-700 dark:text-zinc-300"}>
              {safetyStockMultiplier.toFixed(1)}x
            </span>
          </div>
          <input
            type="range"
            min="0.5"
            max="3.0"
            step="0.1"
            value={safetyStockMultiplier}
            onChange={(e) => onSafetyStockMultiplierChange(Number(e.target.value))}
            className="w-full accent-zinc-900 dark:accent-zinc-50 bg-zinc-200 dark:bg-zinc-800 h-1 rounded appearance-none cursor-pointer"
          />
        </div>

        {/* Lead Time Buffer */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs font-mono font-bold">
            <span className="text-zinc-500 dark:text-zinc-400 uppercase">Lead Time Buffer</span>
            <span className={leadTimeBuffer > 0 ? "text-red-600" : "text-zinc-700 dark:text-zinc-300"}>
              {leadTimeBuffer > 0 ? `+${leadTimeBuffer}` : leadTimeBuffer} days
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="30"
            step="1"
            value={leadTimeBuffer}
            onChange={(e) => onLeadTimeBufferChange(Number(e.target.value))}
            className="w-full accent-zinc-900 dark:accent-zinc-50 bg-zinc-200 dark:bg-zinc-800 h-1 rounded appearance-none cursor-pointer"
          />
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-3 border-t border-zinc-800">
        <button
          type="button"
          onClick={onReset}
          disabled={loading}
          className="px-3 py-1.5 rounded border border-zinc-800 bg-[#111114] text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 text-xs font-mono font-semibold cursor-pointer disabled:opacity-50"
        >
          Reset Modifiers
        </button>
        <button
          type="button"
          onClick={onSimulate}
          disabled={loading}
          className="px-3 py-1.5 rounded bg-zinc-950 hover:bg-zinc-800 dark:bg-[#DC2626] dark:hover:bg-[#B91C1C] text-white text-xs font-mono font-semibold cursor-pointer disabled:opacity-50"
        >
          {loading ? "Simulating..." : "Simulate Stress"}
        </button>
      </div>
    </div>
  );
}