import { useStore } from "./store";

const API_BASE = typeof window !== "undefined"
  ? (window.location.host.includes("localhost:3000") || window.location.host.includes("127.0.0.1:3000")
      ? "http://127.0.0.1:8000/api"
      : "/api")
  : `${process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api`;


function getHeaders(isFormData = false) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return {
    // If we are uploading a file/form-data, let the browser define the boundary automatically
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request(path: string, options: RequestInit = {}) {
  const url = `${API_BASE}${path}`;
  
  // Isolate if payload is a FormData instance
  const isFormData = options.body instanceof FormData;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(isFormData),
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      if (typeof window !== "undefined") {
        const store = useStore.getState();
        if (store && typeof store.logout === "function") {
          store.logout();
        }
      }
      throw new Error("Session expired. Please log in again.");
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Auth Modules
  async login(formData: FormData) {
    const params = new URLSearchParams();
    formData.forEach((value, key) => {
      params.append(key, value.toString());
    });

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
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

  // Enterprise Operations Data Mapping 
  getDashboard(datasetId?: number) {
    const url = datasetId ? `/enterprise/dashboard?dataset_id=${datasetId}` : "/enterprise/dashboard";
    return request(url);
  },

  getDecisions(filters: { category?: string; risk_level?: string; status?: string; search?: string; datasetId?: number } = {}) {
    const params = new URLSearchParams();
    if (filters.category) params.append("category", filters.category);
    if (filters.risk_level) params.append("risk_level", filters.risk_level);
    if (filters.status) params.append("status", filters.status);
    if (filters.search) params.append("search", filters.search);
    if (filters.datasetId) params.append("dataset_id", filters.datasetId.toString());
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

  getControlTower(datasetId?: number) {
    const url = datasetId ? `/enterprise/control-tower?dataset_id=${datasetId}` : "/enterprise/control-tower";
    return request(url);
  },

  getReorder(datasetId?: number) {
    const url = datasetId ? `/enterprise/reorder?dataset_id=${datasetId}` : "/enterprise/reorder";
    return request(url);
  },

  getRevenueProtection() {
    return request("/enterprise/revenue-protection");
  },

  getSKU(sku: string) {
    return request(`/enterprise/sku/${sku}`);
  },

  getForecastQuality(datasetId?: number) {
    const url = datasetId ? `/enterprise/forecast-quality?dataset_id=${datasetId}` : "/enterprise/forecast-quality";
    return request(url);
  },

  getAuditLogs(params?: { action?: string; user?: string; search?: string }) {
    const cleanParams: any = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== "") cleanParams[k] = v;
      });
    }
    const queryParams = new URLSearchParams(cleanParams).toString();
    return request(`/enterprise/audit-logs${queryParams ? `?${queryParams}` : ""}`);
  },

  async copilotChat(query?: string, settings?: any, options?: RequestInit): Promise<any> {
    const payloadQuery = query?.trim() || "What should I order today?";
    try {
      return await request("/enterprise/copilot/chat", {
        method: "POST",
        headers: {
          "Accept": "application/json",
          ...options?.headers,
        },
        body: JSON.stringify({
          query: payloadQuery,
          prompt: payloadQuery,
          settings: settings || {},
        }),
        ...options,
      });
    } catch (err: any) {
      console.error("Network bridge initialization error:", err);
      return {
        action_cards: [],
        playbook_cards: [],
        response: err.message || "Failed to contact AI Copilot"
      };
    }
  },

  getABC() {
    return request("/enterprise/abc-analysis");
  },

  getSuppliers() {
    return request("/enterprise/suppliers");
  },

  getWarehouses(datasetId?: number) {
    const url = datasetId ? `/enterprise/warehouses?dataset_id=${datasetId}` : "/enterprise/warehouses";
    return request(url);
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

  autogeneratePO(payload: { sku: string; quantity: number; supplier_id: number }) {
    return request("/enterprise/copilot/autogenerate-po", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  runScenario(payload: {
    demand_change_pct: number;
    lead_time_change_days: number;
    supplier_reliability_change_pct: number;
    safety_stock_multiplier?: number;
    lead_time_buffer_days?: number;
  }) {
    return request("/simulation/run-scenario", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getDatasets() {
    return request("/dataset/list");
  },

  getHealth() {
    // Avoid applying internal structural json types to base status pings
    return request("/auth/health", { method: "GET", headers: { "Content-Type": "text/plain" } });
  },

  async uploadDataset(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request("/dataset/upload", {
      method: "POST",
      body: formData,
    });
  },

  importDataset(payload: {
    temp_file_id?: string;
    source_type: string;
    mapping?: Record<string, string | null>;
    confirm_low_confidence?: boolean;
    confirm_customer_identifiers?: boolean;
    confirm_custom_sku?: boolean;
  }) {
    return request("/dataset/import", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  cleanupDataset(opts?: { confirm?: boolean }) {
    const params = new URLSearchParams();
    if (opts?.confirm !== undefined) {
      params.append("confirm", String(opts.confirm));
    }
    return request(`/dataset/cleanup${params.toString() ? `?${params.toString()}` : ""}`, {
      method: "POST",
    });
  },

  deleteDataset(datasetId: number) {
    return request(`/dataset/${datasetId}/delete`, {
      method: "POST",
    });
  },

  generateExecutiveReport() {
    return request("/reports/executive", {
      method: "POST",
    });
  },

  async downloadExecutiveReport() {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const response = await fetch(`${API_BASE}/reports/download`, {
      method: "GET",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "Report download failed");
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "RetailGPT_Executive_Report.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  getRMSETrend(limit = 50) {
    return request(`/leaderboard/models?limit=${limit}`);
  },

  getMAPETrend(limit = 50) {
    return request(`/leaderboard/models?limit=${limit}`);
  },

  getModelWins(datasetId?: number) {
    const url = datasetId ? `/leaderboard/models?dataset_id=${datasetId}` : "/leaderboard/models";
    return request(url);
  },

  getAccuracySummary() {
    return request("/leaderboard/models");
  },

  getSKUPerformance() {
    return request("/leaderboard/models");
  },
};

