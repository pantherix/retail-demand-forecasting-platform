"use client";

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
  isHydrated: boolean;
  
  hydrateStore: () => void;
  setActiveTab: (tab: string) => void;
  setActiveSku: (sku: string) => void;
  setUser: (user: Partial<UserInfo>) => void;
  setAlertsCount: (count: number) => void;
  triggerRefresh: () => void;
  logout: () => void;
  toggleTheme: () => void;
  addToast: (message: string, type?: "success" | "error" | "info", durationMs?: number) => void;
  removeToast: (id: string) => void;
}

const STORAGE_KEYS = {
  TOKEN: "token",
  USERNAME: "username",
  ROLE: "role",
  FULL_NAME: "full_name",
  THEME: "theme",
  ACTIVE_TAB: "active_tab"
} as const;

function isExpiredJwt(token: string | null): boolean {
  if (!token) return true;

  try {
    const encodedPayload = token.split(".")[1];
    const paddedPayload = encodedPayload
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(Math.ceil(encodedPayload.length / 4) * 4, "=");
    const payload = JSON.parse(
      atob(paddedPayload)
    );
    return typeof payload.exp !== "number" || payload.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}

export const useStore = create<AppState>((set, get) => {
  return {
    // 1. Safe Static Defaults for Server Pre-Rendering Phase
    activeTab: "executive",
    activeSku: "SKU-101",
    user: { token: null, username: null, role: null, fullName: null },
    alertsCount: 0,
    refreshTrigger: 0,
    theme: "light",
    toasts: [],
    isHydrated: false,

    // 2. Client Side Sync Engine (Fired after mount inside layout wrapper)
    hydrateStore: () => {
      if (typeof window === "undefined") return;

      try {
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get("token");
        const tabFromUrl = urlParams.get("tab");
        const themeFromUrl = urlParams.get("theme");

        if (tokenFromUrl) {
          localStorage.setItem(STORAGE_KEYS.TOKEN, tokenFromUrl);
          localStorage.setItem(STORAGE_KEYS.USERNAME, "admin");
          localStorage.setItem(STORAGE_KEYS.ROLE, "admin");
          localStorage.setItem(STORAGE_KEYS.FULL_NAME, "Executive Admin");
        }

        if (themeFromUrl) {
          localStorage.setItem(STORAGE_KEYS.THEME, themeFromUrl);
        }

        const savedTheme = (localStorage.getItem(STORAGE_KEYS.THEME) as "light" | "dark") || "light";
        
        // Batch configuration to DOM layout engine safely
        if (savedTheme === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }

        const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
        const token = isExpiredJwt(storedToken) ? null : storedToken;

        if (!token && storedToken) {
          Object.values(STORAGE_KEYS).forEach((key) => {
            if (key !== STORAGE_KEYS.THEME) {
              localStorage.removeItem(key);
            }
          });
        }

        set({
          isHydrated: true,
          activeTab: tabFromUrl || "executive",
          theme: savedTheme,
          user: {
            token,
            username: token ? localStorage.getItem(STORAGE_KEYS.USERNAME) : null,
            role: token ? localStorage.getItem(STORAGE_KEYS.ROLE) : null,
            fullName: token ? localStorage.getItem(STORAGE_KEYS.FULL_NAME) : null,
          }
        });
      } catch (error) {
        console.error("Zustand Hydration Fault:", error);
        set({ isHydrated: true }); // Prevent locking app access on strict sandbox browser environments
      }
    },

    setActiveTab: (tab) => {
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem(STORAGE_KEYS.ACTIVE_TAB, tab);
        } catch (e) {
          console.warn("Storage write blocked:", e);
        }
      }
      set({ activeTab: tab });
    },

    setActiveSku: (sku) => set({ activeSku: sku }),

    setUser: (userUpdate) =>
      set((state) => {
        const newUser = { ...state.user, ...userUpdate };
        if (typeof window !== "undefined") {
          try {
            if (newUser.token) localStorage.setItem(STORAGE_KEYS.TOKEN, newUser.token);
            if (newUser.username) localStorage.setItem(STORAGE_KEYS.USERNAME, newUser.username);
            if (newUser.role) localStorage.setItem(STORAGE_KEYS.ROLE, newUser.role);
            if (newUser.fullName) localStorage.setItem(STORAGE_KEYS.FULL_NAME, newUser.fullName);
          } catch (e) {
            console.warn("User credentials cache synchronization blocked:", e);
          }
        }
        return { user: newUser };
      }),

    setAlertsCount: (count) => set({ alertsCount: count }),
    
    triggerRefresh: () => set((state) => ({ refreshTrigger: state.refreshTrigger + 1 })),

    logout: () => {
      if (typeof window !== "undefined") {
        try {
          // Explicit granular deletes to prevent collateral damage to other storage partitions
          Object.values(STORAGE_KEYS).forEach((key) => {
            if (key !== STORAGE_KEYS.THEME) { // Preserve design preference across sessions
              localStorage.removeItem(key);
            }
          });
        } catch (e) {
          console.error("Logout runtime clean fault:", e);
        }
      }
      set({
        user: { token: null, username: null, role: null, fullName: null },
        activeTab: "executive",
      });
    },

    toggleTheme: () => set((state) => {
      const nextTheme = state.theme === "light" ? "dark" : "light";
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem(STORAGE_KEYS.THEME, nextTheme);
          if (nextTheme === "dark") {
            document.documentElement.classList.add("dark");
          } else {
            document.documentElement.classList.remove("dark");
          }
        } catch (e) {
          console.warn("Theme persistence blocked:", e);
        }
      }
      return { theme: nextTheme };
    }),

    addToast: (message, type = "info", durationMs = 4000) => set((state) => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const newToast: Toast = { id, message, type };

      // Self-cleaning execution thread loop to enforce structural collection control
      setTimeout(() => {
        get().removeToast(id);
      }, durationMs);

      return { toasts: [...state.toasts, newToast] };
    }),

    removeToast: (id) => set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
  };
});
