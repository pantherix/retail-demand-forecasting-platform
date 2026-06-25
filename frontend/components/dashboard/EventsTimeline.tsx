import React, { memo } from "react";
import { UserCheck, AlertCircle, ShoppingCart, ArrowRightLeft, Activity, ShieldCheck } from "lucide-react";

export interface TimelineEvent {
  id: string;
  type: "alert" | "audit";
  title: string;
  message: string;
  severity: string;
  timestamp: string;
}

interface EventsTimelineProps {
  events: TimelineEvent[];
  isUnavailable: boolean;
}

export const EventsTimeline: React.FC<EventsTimelineProps> = memo(({ events, isUnavailable }) => {
  
  const getEventIcon = (event: TimelineEvent) => {
    const titleLower = event.title.toLowerCase();
    const msgLower = event.message.toLowerCase();

    if (titleLower.includes("purchase-orders") || titleLower.includes("po") || msgLower.includes("purchase order")) {
      return {
        icon: <ShoppingCart className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />,
        border: "border-indigo-200 dark:border-indigo-900/40",
        bg: "bg-indigo-50 dark:bg-indigo-950/20",
      };
    }
    if (titleLower.includes("transfers") || titleLower.includes("transfer") || msgLower.includes("transfer")) {
      return {
        icon: <ArrowRightLeft className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
        border: "border-emerald-200 dark:border-emerald-900/40",
        bg: "bg-emerald-50 dark:bg-emerald-950/20",
      };
    }
    if (event.type === "alert" || titleLower.includes("alert") || event.severity === "Critical" || event.severity === "High") {
      return {
        icon: <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />,
        border: "border-rose-200 dark:border-rose-900/40",
        bg: "bg-rose-50 dark:bg-rose-950/20",
      };
    }
    if (msgLower.includes("seed") || msgLower.includes("initialized")) {
      return {
        icon: <ShieldCheck className="h-4 w-4 text-teal-600 dark:text-teal-400" />,
        border: "border-teal-200 dark:border-teal-900/40",
        bg: "bg-teal-50 dark:bg-teal-950/20",
      };
    }

    return {
      icon: <UserCheck className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />,
      border: "border-zinc-800",
      bg: "bg-zinc-900/50",
    };
  };

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return "Just now";
    }
  };

  const formatDateLabel = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return "Today";
    }
  };

  return (
    <div
      className="backdrop-blur-md bg-white/70 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/60 p-6 rounded-xl shadow-sm space-y-5 flex flex-col justify-between"
      role="region"
      aria-label="Recent Audit Logs & Alerts Timeline"
    >
      <div className="space-y-1">
        <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
          Activity Ledger
        </span>
        <h3 className="text-lg tracking-tight font-extrabold text-zinc-900 dark:text-zinc-50">
          Recent Events & Timeline
        </h3>
      </div>

      {isUnavailable ? (
        <div className="py-8 text-center text-zinc-400 font-mono italic text-xs">
          Data currently unavailable
        </div>
      ) : events.length === 0 ? (
        <div className="py-8 border border-dashed border-zinc-800 rounded-lg text-center text-zinc-400 font-mono text-xs">
          No recent activity logs.
        </div>
      ) : (
        <div className="relative border-l border-zinc-800 ml-4 py-2 space-y-6">
          {events.map((event, idx) => {
            const styling = getEventIcon(event);
            return (
              <div key={event.id || idx} className="relative pl-7 group" role="listitem">
                {/* Connector Node */}
                <div
                  className={`absolute -left-[17px] top-1 h-8 w-8 rounded-full border flex items-center justify-center shrink-0 shadow-sm ${styling.bg} ${styling.border} transition-transform group-hover:scale-105 duration-200`}
                  aria-hidden="true"
                >
                  {styling.icon}
                </div>

                {/* Event text */}
                <div className="space-y-1">
                  <div className="flex justify-between items-baseline gap-4">
                    <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                      {event.title}
                    </h4>
                    <span className="text-[10px] font-mono text-zinc-400 shrink-0 select-none">
                      {formatDateLabel(event.timestamp)} • {formatTime(event.timestamp)}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed font-sans font-medium">
                    {event.message}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
});

EventsTimeline.displayName = "EventsTimeline";
