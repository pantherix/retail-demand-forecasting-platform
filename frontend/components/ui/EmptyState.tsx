import { ReactNode } from "react";
import { HelpCircle } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-900/50 my-4 space-y-3">
      <div className="p-3 bg-zinc-900 rounded-full border border-zinc-150 dark:border-zinc-800">
        <HelpCircle className="h-6 w-6 text-zinc-400 dark:text-zinc-500" />
      </div>
      <div className="space-y-1 max-w-sm">
        <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-50">{title}</h3>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">{description}</p>
      </div>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}
