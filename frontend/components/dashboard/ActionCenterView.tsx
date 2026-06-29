"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { DecisionQueue } from "./DecisionQueue";
import { AIReasoningConsole } from "./AIReasoningConsole";
import { CardSkeleton } from "../ui/CardSkeleton";
import { ErrorState } from "../ui/ErrorState";

export default function ActionCenterView() {
  const { refreshTrigger, triggerRefresh, user } = useStore();
  const { addToast } = useToast();

  const [decisions, setDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters State Engine
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [minExposure, setMinExposure] = useState("0");

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [submittingSku, setSubmittingSku] = useState<string | null>(null);

  // Reference track to break recursive state loop updates safely
  const standardizingSelectionRef = useRef<boolean>(false);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    api.getDecisions({ category, risk_level: riskLevel, status, search })
      .then((res) => {
        // Guarantee payload is always map-safe array format
        setDecisions(Array.isArray(res) ? res : []);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Failed to load decisions backlog.");
        setLoading(false);
      });
  };

  // Synchronize remote data feeds on parameter changes
  useEffect(() => {
    fetchData();
  }, [category, riskLevel, status, search, refreshTrigger]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWS = () => {
      try {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api";
        let apiHost = apiBase.replace("http://", "").replace("https://", "").replace("/api", "");
        if (!apiHost) {
          if (window.location.host.includes("localhost:3000") || window.location.host.includes("127.0.0.1:3000")) {
            apiHost = "localhost:8000";
          } else {
            apiHost = window.location.host;
          }
        }
        const wsUrl = `${wsProtocol}//${apiHost}/api/ws`;

        socket = new WebSocket(wsUrl);

        socket.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            console.log("Action Center WS received:", msg);
            addToast(`Queue Alert: ${msg.message || "Mutation occurred."}`, "info");
            fetchData();
          } catch (e) {
            console.error("Failed to parse WS message:", e);
          }
        };

        socket.onclose = () => {
          reconnectTimeout = setTimeout(connectWS, 5000);
        };
      } catch (err) {
        console.error("Action Center WS connection failed:", err);
      }
    };

    connectWS();

    return () => {
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  const handleStatusChange = async (sku: string, newStatus: string) => {
    try {
      await api.updateDecisionStatus(sku, newStatus);
      addToast(`Status updated to ${newStatus} for SKU ${sku}.`, "success");
      triggerRefresh();
    } catch (err: any) {
      addToast(err.message || "Failed to update status", "error");
    }
  };

  const handleAddNote = async (sku: string, noteText: string) => {
    if (!noteText.trim()) return;
    try {
      await api.addDecisionNote(sku, noteText);
      triggerRefresh();
    } catch (err: any) {
      addToast(err.message || "Failed to add comment", "error");
      throw err;
    }
  };

  // Optimistic UI Transformer Pipeline
  const executePrimaryAction = async (item: any) => {
    if (submittingSku) return;
    setSubmittingSku(item.sku);

    const originalDecisions = [...decisions];

    // Optimistically update the UI list state immediately to keep interactions smooth
    setDecisions(prev => prev.filter(d => d.sku !== item.sku));

    try {
      if (item.reorder_quantity > 0) {
        const supplier_id = item.supplier_id;
        if (!supplier_id) {
          addToast("Supplier relationship missing. PO creation prevented.", "error");
          throw new Error("Supplier relationship missing");
        }
        const res = await api.createPurchaseOrder({
          supplier_id,
          items: [{ sku: item.sku, quantity: item.reorder_quantity }]
        });
        if (res && res.po_id) {
          await api.approvePurchaseOrder(res.po_id);
          addToast(`Replenishment ordered successfully for SKU ${item.sku}.`, "success");
          triggerRefresh();
        } else {
          throw new Error("Failed to generate structural purchase order");
        }
      } else {
        await api.updateDecisionStatus(item.sku, "Resolved");
        addToast(`Fulfillment exposure marked resolved for ${item.sku}.`, "success");
        triggerRefresh();
      }
    } catch (err: any) {
      // Revert the local list state back if the backend database errors out
      setDecisions(originalDecisions);
      addToast(err.message || "Failed to execute structural decision execution step.", "error");
    } finally {
      setSubmittingSku(null);
    }
  };

  // Safe selection tracking effect (No recursive dependencies)
  useEffect(() => {
    if (standardizingSelectionRef.current) return;

    if (decisions.length > 0) {
      const matchExists = decisions.some(d => d.id === selectedId);
      if (selectedId === null || !matchExists) {
        standardizingSelectionRef.current = true;
        setSelectedId(decisions[0].id);
        // Release lock on the next frame execution tick
        setTimeout(() => { standardizingSelectionRef.current = false; }, 0);
      }
    } else if (selectedId !== null) {
      setSelectedId(null);
    }
  }, [decisions]); // Track array value transformations only!

  const selectedDecision = useMemo(() => {
    return decisions.find(d => d.id === selectedId) || null;
  }, [decisions, selectedId]);

  const handleApprove = (id: number, qty: number) => {
    const dec = decisions.find(d => d.id === id);
    if (dec) {
      executePrimaryAction({ ...dec, reorder_quantity: qty });
    }
  };

  const handleReject = async (id: number) => {
    const dec = decisions.find(d => d.id === id);
    if (dec) {
      await handleStatusChange(dec.sku, "Rejected");
      addToast(`Recommendation for SKU ${dec.sku} rejected.`, "info");
    }
  };

  const handleModify = async (id: number, qty: number) => {
    const dec = decisions.find(d => d.id === id);
    if (dec) {
      try {
        await api.updateDecisionQuantity(dec.sku, qty);
        addToast(`Quantity modified to ${qty} for SKU ${dec.sku}.`, "success");
        triggerRefresh();
      } catch (err: any) {
        addToast(err.message || "Failed to modify quantity", "error");
      }
    }
  };

  const handleEscalate = async (id: number, role: string) => {
    const dec = decisions.find(d => d.id === id);
    if (dec) {
      try {
        await api.assignDecision(dec.sku, role);
        addToast(`Decision for SKU ${dec.sku} escalated to ${role}.`, "success");
        triggerRefresh();
      } catch (err: any) {
        addToast(err.message || "Failed to escalate decision", "error");
      }
    }
  };

  const filteredDecisions = useMemo(() => {
    const exp = Number(minExposure) || 0;
    return decisions.filter(d => {
      // Safely default revenue metrics if property fields are omitted
      const revImpact = d.revenue_impact !== undefined ? d.revenue_impact : (d.revenue_at_risk || 0);
      return revImpact >= exp;
    });
  }, [decisions, minExposure]);

  if (loading && decisions.length === 0) {
    return (
      <div className="max-w-6xl mx-auto space-y-8 py-2">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  if (errorMsg) {
    return <ErrorState message={errorMsg} onRetry={fetchData} />;
  }

  return (
    <div className="max-w-6xl mx-auto py-2">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left column: Resolutions List Queue */}
        <div className="lg:col-span-5">
          <DecisionQueue
            decisions={filteredDecisions}
            selectedId={selectedId}
            onSelect={setSelectedId}
            search={search}
            onSearchChange={setSearch}
            category={category}
            onCategoryChange={setCategory}
            riskLevel={riskLevel}
            onRiskLevelChange={setRiskLevel}
            minExposure={minExposure}
            onMinExposureChange={setMinExposure}
          />
        </div>

        {/* Right column: AI Spotlight Operations Console */}
        <div className="lg:col-span-7">
          <AIReasoningConsole
            decision={selectedDecision}
            onApprove={handleApprove}
            onReject={handleReject}
            onModify={handleModify}
            onEscalate={handleEscalate}
            onAddNote={handleAddNote}
            currentUserId={user?.username || "admin"}
          />
        </div>
      </div>
    </div>
  );
}