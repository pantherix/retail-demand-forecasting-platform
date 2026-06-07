import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center border border-red-200 dark:border-red-950/30 rounded-lg bg-red-50/20 dark:bg-red-950/5 my-4 space-y-4">
      <div className="p-3 bg-red-50 dark:bg-red-950/30 rounded-full border border-red-150 dark:border-red-900/50">
        <AlertTriangle className="h-6 w-6 text-red-500" />
      </div>
      <div className="space-y-1 max-w-md">
        <h3 className="text-sm font-bold text-red-800 dark:text-red-200">Execution Error</h3>
        <p className="text-xs text-red-600 dark:text-red-400 font-mono leading-relaxed break-all">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 px-3 py-1.5 bg-zinc-950 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-950 text-white font-mono font-bold text-[10px] uppercase tracking-wider rounded transition-colors cursor-pointer"
        >
          <RefreshCw className="h-3 w-3 animate-spin-slow" />
          Retry Load
        </button>
      )}
    </div>
  );
}
