import { useStore } from "./store";

const API_BASE = "http://localhost:8000/api";

function getHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request(path: string, options: RequestInit = {}) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid — force re-login
      if (typeof window !== "undefined") {
        localStorage.clear();
      }
      useStore.getState().logout();
      throw new Error("Session expired. Please log in again.");
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(formData: FormData) {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Authentication failed");
    }
    const data = await response.json();
    if (typeof window !== "undefined") {
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("username", data.username);
      localStorage.setItem("role", data.role);
      localStorage.setItem("full_name", data.full_name);
    }
    return data;
  },

  async register(payload: any) {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  logout() {
    if (typeof window !== "undefined") {
      localStorage.clear();
    }
  },

  getCurrentUser() {
    return request("/auth/me");
  },

  getUsers() {
    return request("/auth/users");
  },

  // Modules API
  getDashboard() {
    return request("/enterprise/dashboard");
  },

  getDecisions(filters: { category?: string; risk_level?: string; status?: string; search?: string } = {}) {
    const params = new URLSearchParams();
    if (filters.category) params.append("category", filters.category);
    if (filters.risk_level) params.append("risk_level", filters.risk_level);
    if (filters.status) params.append("status", filters.status);
    if (filters.search) params.append("search", filters.search);
    return request(`/enterprise/decisions?${params.toString()}`);
  },

  assignDecision(sku: string, username: string) {
    return request(`/enterprise/decisions/${sku}/assign`, {
      method: "POST",
      body: JSON.stringify({ username }),
    });
  },

  updateDecisionStatus(sku: string, status: string) {
    return request(`/enterprise/decisions/${sku}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
  },

  addDecisionNote(sku: string, note: string) {
    return request(`/enterprise/decisions/${sku}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
  },

  updateDecisionQuantity(sku: string, quantity: number) {
    return request(`/enterprise/decisions/${sku}/quantity`, {
      method: "POST",
      body: JSON.stringify({ quantity }),
    });
  },

  getDecisionNotes(sku: string) {
    return request(`/enterprise/decisions/${sku}/notes`);
  },

  getControlTower() {
    return request("/enterprise/control-tower");
  },

  getReorder() {
    return request("/enterprise/reorder");
  },

  getRevenueProtection() {
    return request("/enterprise/revenue-protection");
  },

  getSKU(sku: string) {
    return request(`/enterprise/sku/${sku}`);
  },

  getForecastQuality() {
    return request("/enterprise/forecast-quality");
  },

  copilotChat(prompt: string, history?: any[], options?: RequestInit) {
    return request("/enterprise/copilot/chat", {
      method: "POST",
      body: JSON.stringify({ prompt, history }),
      ...options,
    });
  },

  getABC() {
    return request("/enterprise/abc-analysis");
  },

  getSuppliers() {
    return request("/enterprise/suppliers");
  },

  getWarehouses() {
    return request("/enterprise/warehouses");
  },

  createTransfer(payload: { from_wh: string; to_wh: string; sku: string; quantity: number }) {
    return request("/enterprise/transfers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getAlerts() {
    return request("/enterprise/alerts");
  },

  resolveAlert(alertId: number) {
    return request(`/enterprise/alerts/${alertId}/resolve`, {
      method: "POST",
    });
  },

  getPurchaseOrders() {
    return request("/enterprise/purchase-orders");
  },

  createPurchaseOrder(payload: { supplier_id: number; items: Array<{ sku: string; quantity: number }> }) {
    return request("/enterprise/purchase-orders/create", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  approvePurchaseOrder(poId: number) {
    return request(`/enterprise/purchase-orders/${poId}/approve`, {
      method: "POST",
    });
  },

  runScenario(payload: { demand_change_pct: number; lead_time_change_days: number; supplier_reliability_change_pct: number }) {
    return request("/simulation/run-scenario", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
