import { LoadingSkeleton } from "./LoadingSkeleton";

export function CardSkeleton() {
  return (
    <div className="p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg space-y-4 shadow-sm">
      <LoadingSkeleton className="h-4 w-1/3" />
      <LoadingSkeleton className="h-8 w-2/3" />
      <div className="space-y-2">
        <LoadingSkeleton className="h-3 w-full" />
        <LoadingSkeleton className="h-3 w-5/6" />
      </div>
    </div>
  );
}
