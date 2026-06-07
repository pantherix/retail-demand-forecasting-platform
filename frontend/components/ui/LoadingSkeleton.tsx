export function LoadingSkeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-zinc-200 dark:bg-zinc-800 rounded ${className}`} />;
}
