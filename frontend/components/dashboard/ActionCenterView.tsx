import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { DecisionQueue } from "./DecisionQueue";
import { AIReasoningConsole } from "./AIReasoningConsole";
import { CardSkeleton } from "../ui/CardSkeleton";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";

export default function ActionCenterView() {
  const { refreshTrigger, triggerRefresh, setActiveTab, setActiveSku, user } = useStore();
  const { addToast } = useToast();

  const [decisions, setDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");
  const [minExposure, setMinExposure] = useState("0");

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [submittingSku, setSubmittingSku] = useState<string | null>(null);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    api.getDecisions({ category, risk_level: riskLevel, status, search })
      .then((res) => {
        setDecisions(res);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Failed to load decisions backlog.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, [category, riskLevel, status, search, refreshTrigger]);


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

  // OPTIMISTIC ACTIONS: executePrimaryAction (approves a PO or marks Resolved)
  const executePrimaryAction = async (item: any) => {
    if (submittingSku) return;
    setSubmittingSku(item.sku);

    const originalDecisions = [...decisions];

    // Optimistically resolve locally
    setDecisions(prev => prev.filter(d => d.sku !== item.sku));

    try {
      if (item.reorder_quantity > 0) {
        await api.createPurchaseOrder({
          supplier_id: 3,
          items: [{ sku: item.sku, quantity: item.reorder_quantity }]
        });
        const pos = await api.getPurchaseOrders();
        const latestDraft = pos.find((p: any) => p.status === "Draft");
        if (latestDraft) {
          await api.approvePurchaseOrder(latestDraft.id);
          addToast(`Replenishment ordered for SKU ${item.sku}.`, "success");
          triggerRefresh();
        }
      } else {
        await api.updateDecisionStatus(item.sku, "Resolved");
        addToast(`Fulfillment exposure marked resolved for ${item.sku}.`, "success");
        triggerRefresh();
      }
    } catch (err: any) {
      // Rollback on failure
      setDecisions(originalDecisions);
      addToast(err.message || "Failed to execute decision", "error");
    } finally {
      setSubmittingSku(null);
    }
  };

  // Auto-select first decision
  useEffect(() => {
    if (decisions.length > 0) {
      if (selectedId === null || !decisions.some(d => d.id === selectedId)) {
        setSelectedId(decisions[0].id);
      }
    } else {
      setSelectedId(null);
    }
  }, [decisions, selectedId]);

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
      await handleStatusChange(dec.sku, "Resolved");
      addToast(`Recommendation for SKU ${dec.sku} rejected and resolved.`, "info");
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

  // Filtered decisions for queue (filtering exposure locally if needed)
  const filteredDecisions = useMemo(() => {
    return decisions.filter(d => {
      const exp = Number(minExposure);
      return d.revenue_impact >= exp;
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
        {/* Left column: Resolutions List */}
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

        {/* Right column: AI Spotlight Console */}
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
