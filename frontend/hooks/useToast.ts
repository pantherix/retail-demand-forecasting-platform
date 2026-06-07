import { useStore } from "../app/store";

export function useToast() {
  const addToast = useStore((state) => state.addToast);
  const removeToast = useStore((state) => state.removeToast);
  return { addToast, removeToast };
}
