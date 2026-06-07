import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

interface ToastProps {
  id: string;
  message: string;
  type: "success" | "error" | "info";
  onClose: () => void;
}

export default function Toast({ message, type, onClose }: ToastProps) {
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true);
    }, 4000);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (exiting) {
      const exitTimer = setTimeout(() => {
        onClose();
      }, 150);
      return () => clearTimeout(exitTimer);
    }
  }, [exiting, onClose]);

  const icons = {
    success: <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />,
    error: <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />,
    info: <Info className="h-4 w-4 text-zinc-500 shrink-0" />,
  };

  const bgStyles = {
    success: "bg-white dark:bg-zinc-900 border-emerald-100 dark:border-emerald-950/50 shadow-emerald-500/5",
    error: "bg-white dark:bg-zinc-900 border-red-100 dark:border-red-950/50 shadow-red-500/5",
    info: "bg-white dark:bg-zinc-900 border-zinc-150 dark:border-zinc-800 shadow-zinc-500/5",
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className={`flex items-start gap-3 p-4 rounded-lg border shadow-lg max-w-sm w-full transition-all duration-200 select-none ${
        bgStyles[type]
      } ${exiting ? "animate-fadeOut" : "animate-slideIn"}`}
    >
      {icons[type]}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-sans font-semibold text-zinc-900 dark:text-zinc-50 leading-relaxed">
          {message}
        </p>
      </div>
      <button
        type="button"
        onClick={() => setExiting(true)}
        className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 p-0.5 rounded transition-colors"
        aria-label="Close notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
