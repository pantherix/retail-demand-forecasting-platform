import { create } from "zustand";

export interface UserInfo {
  token: string | null;
  username: string | null;
  role: string | null;
  fullName: string | null;
}

export interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface AppState {
  activeTab: string;
  activeSku: string;
  user: UserInfo;
  alertsCount: number;
  refreshTrigger: number;
  theme: "light" | "dark";
  toasts: Toast[];
  
  setActiveTab: (tab: string) => void;
  setActiveSku: (sku: string) => void;
  setUser: (user: Partial<UserInfo>) => void;
  setAlertsCount: (count: number) => void;
  triggerRefresh: () => void;
  logout: () => void;
  toggleTheme: () => void;
  addToast: (message: string, type?: "success" | "error" | "info") => void;
  removeToast: (id: string) => void;
}

export const useStore = create<AppState>((set) => {
  // Safe SSR initial state
  const isClient = typeof window !== "undefined";
  const urlParams = isClient ? new URLSearchParams(window.location.search) : null;
  const tokenFromUrl = urlParams ? urlParams.get("token") : null;
  const tabFromUrl = urlParams ? urlParams.get("tab") : null;

  if (isClient && tokenFromUrl) {
    localStorage.setItem("token", tokenFromUrl);
    localStorage.setItem("username", "admin");
    localStorage.setItem("role", "admin");
    localStorage.setItem("full_name", "Executive Admin");
  }

  // Set initial theme class on root HTML node to prevent flash
  if (isClient) {
    const savedTheme = localStorage.getItem("theme") || "light";
    if (savedTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }

  const initialUser: UserInfo = {
    token: isClient ? localStorage.getItem("token") : null,
    username: isClient ? localStorage.getItem("username") : null,
    role: isClient ? localStorage.getItem("role") : null,
    fullName: isClient ? localStorage.getItem("full_name") : null,
  };

  const initialTheme: "light" | "dark" = isClient
    ? (localStorage.getItem("theme") as "light" | "dark") || "light"
    : "light";

  return {
    activeTab: tabFromUrl || "executive",
    activeSku: "SKU-101",
    user: initialUser,
    alertsCount: 0,
    refreshTrigger: 0,
    theme: initialTheme,
    toasts: [],

    setActiveTab: (tab) => set({ activeTab: tab }),
    setActiveSku: (sku) => set({ activeSku: sku }),
    setUser: (userUpdate) =>
      set((state) => {
        const newUser = { ...state.user, ...userUpdate };
        if (isClient) {
          if (newUser.token) localStorage.setItem("token", newUser.token);
          if (newUser.username) localStorage.setItem("username", newUser.username);
          if (newUser.role) localStorage.setItem("role", newUser.role);
          if (newUser.fullName) localStorage.setItem("full_name", newUser.fullName);
        }
        return { user: newUser };
      }),
    setAlertsCount: (count) => set({ alertsCount: count }),
    triggerRefresh: () => set((state) => ({ refreshTrigger: state.refreshTrigger + 1 })),
    logout: () => {
      if (isClient) {
        localStorage.clear();
      }
      set({
        user: { token: null, username: null, role: null, fullName: null },
        activeTab: "executive",
      });
    },
    toggleTheme: () => set((state) => {
      const nextTheme = state.theme === "light" ? "dark" : "light";
      if (isClient) {
        localStorage.setItem("theme", nextTheme);
        if (nextTheme === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }
      return { theme: nextTheme };
    }),
    addToast: (message, type = "info") => set((state) => {
      const newToast: Toast = {
        id: Math.random().toString(36).substring(2, 9),
        message,
        type,
      };
      return { toasts: [...state.toasts, newToast] };
    }),
    removeToast: (id) => set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
  };
});
