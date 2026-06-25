import { LoadingSkeleton } from "./LoadingSkeleton";

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden w-full">
      <div className="bg-zinc-900/50 p-4 border-b border-zinc-200 dark:border-zinc-800 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <LoadingSkeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      <div className="p-4 space-y-4 bg-white dark:bg-zinc-900">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4">
            {Array.from({ length: cols }).map((_, c) => (
              <LoadingSkeleton key={c} className="h-3.5 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
