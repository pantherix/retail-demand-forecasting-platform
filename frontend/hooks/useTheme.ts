import { useStore } from "../app/store";

export function useTheme() {
  const theme = useStore((state) => state.theme);
  const toggleTheme = useStore((state) => state.toggleTheme);
  return { theme, toggleTheme };
}
