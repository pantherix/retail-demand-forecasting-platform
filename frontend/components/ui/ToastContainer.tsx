import { useStore } from "../../app/store";
import Toast from "./Toast";

export default function ToastContainer() {
  const toasts = useStore((state) => state.toasts);
  const removeToast = useStore((state) => state.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div 
      className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 w-full max-w-sm pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto w-full flex justify-end">
          <Toast
            id={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        </div>
      ))}
    </div>
  );
}
