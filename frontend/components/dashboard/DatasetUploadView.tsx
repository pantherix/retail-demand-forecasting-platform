"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { 
  Upload, FileText, Database, ShieldAlert, Sparkles, RefreshCw,
  CheckCircle, AlertTriangle, AlertCircle, Trash2, ArrowRight,
  ShoppingBag, Activity, Server, FileCheck, Fuel
} from "lucide-react";

interface UploadedFileInfo {
  temp_file_id: string;
  filename: string;
  columns: string[];
  sample_data: Record<string, any>[];
  mappings: Record<string, { best_match: string | null; candidates: { column: string; confidence: number }[] }>;
  rows: number;
  columns_count: number;
}

interface ImportSummary {
  success: boolean;
  dataset_id: number;
  name: string;
  rows: number;
  sku_count: number;
  quality_score: number;
  date_range: string;
  metrics: {
    total_rows: number;
    imported_rows: number;
    rejected_rows: number;
    missing_sku_count: number;
    missing_date_count: number;
  };
  warnings: string[];
}

const CANONICAL_FIELDS = [
  "identity_key",
  "stock_on_hand",
  "date",
  "velocity_rate",
  "product_name",
  "category",
  "unit_cost",
  "unit_price",
  "warehouse"
];

export default function DatasetUploadView() {
  const { addToast } = useToast();
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [syncingApi, setSyncingApi] = useState<string | null>(null);
  const [clearingDb, setClearingDb] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  
  // Mapping workflow states
  const [uploadInfo, setUploadInfo] = useState<UploadedFileInfo | null>(null);
  const [selectedMappings, setSelectedMappings] = useState<Record<string, string>>({});
  const [isMappingMode, setIsMappingMode] = useState(false);
  
  // Quality Center dashboard states
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);

  // Historical Analysis details modal state
  const [selectedAnalysisDataset, setSelectedAnalysisDataset] = useState<any | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const list = await api.getDatasets();
      setDatasets(list || []);
    } catch (err: any) {
      addToast(err.message || "Failed to load datasets", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      await uploadFile(file);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      await uploadFile(file);
    }
  };

  const uploadFile = async (file: File) => {
    const fileExt = file.name.split(".").pop()?.toLowerCase();
    if (fileExt !== "csv" && fileExt !== "xlsx") {
      addToast("Only CSV and Excel (.xlsx) files are supported.", "error");
      return;
    }

    setUploading(true);
    setUploadProgress(15);
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 150);

    addToast(`Uploading and profiling ${file.name}...`, "info");
    try {
      const res = await api.uploadDataset(file);
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Load file metadata and detected mappings
      setUploadInfo(res);
      
      // Initialize mappings with detected best matches for canonical fields only
      const initialMappings: Record<string, string> = {};
      CANONICAL_FIELDS.forEach(key => {
        if (res.mappings[key]) {
          initialMappings[key] = res.mappings[key].best_match || "";
        }
      });
      setSelectedMappings(initialMappings);
      setIsMappingMode(true);
      setImportSummary(null);
      
      addToast(`Profiled ${res.filename}. Set schema mappings below.`, "success");
    } catch (err: any) {
      clearInterval(progressInterval);
      addToast(err.message || "Upload failed. Verify file structure.", "error");
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleMappingChange = (targetField: string, sourceCol: string) => {
    setSelectedMappings(prev => ({
      ...prev,
      [targetField]: sourceCol
    }));
  };

  const executeImport = async () => {
    if (!uploadInfo) return;

    // Validation
    const required = ["identity_key", "date", "stock_on_hand"];
    for (const req of required) {
      if (!selectedMappings[req]) {
        addToast(`Target field '${req.toUpperCase()}' must be mapped before importing!`, "error");
        return;
      }
    }

    // Check duplicate mappings
    const mappedCols = CANONICAL_FIELDS.map(key => selectedMappings[key]).filter(Boolean);
    const hasDuplicates = mappedCols.length !== new Set(mappedCols).size;
    if (hasDuplicates) {
      addToast("Duplicate mappings detected! Multiple target fields cannot map to the same column.", "error");
      return;
    }

    // Client-side confidence check
    let hasLowConfidence = false;
    let confirmLowConfidence = false;
    for (const [targetKey, sourceCol] of Object.entries(selectedMappings)) {
      if (!sourceCol) continue;
      const candidates = uploadInfo.mappings[targetKey]?.candidates || [];
      const match = candidates.find(c => c.column === sourceCol);
      const confidence = match ? match.confidence : 0;
      if (confidence < 0.7) {
        hasLowConfidence = true;
        break;
      }
    }

    if (hasLowConfidence) {
      const confirmed = window.confirm(
        "Low-confidence schema mappings detected (below 70%). Do you want to manually confirm and proceed?"
      );
      if (!confirmed) {
        return;
      }
      confirmLowConfidence = true;
    }


    setUploading(true);
    addToast("Analyzing data quality and running forecasting twin sync...", "info");

    const runImport = async (
      confirmLowConf: boolean,
      confirmCustId: boolean,
      confirmCustSku: boolean
    ) => {
      const payloadMappings: Record<string, string> = {};
      CANONICAL_FIELDS.forEach((key) => {
        if (selectedMappings[key]) {
          payloadMappings[key] = selectedMappings[key];
        }
      });

      return await api.importDataset({
        temp_file_id: uploadInfo.temp_file_id,
        source_type: uploadInfo.filename.endsWith(".csv") ? "csv" : "xlsx",
        mapping: payloadMappings,
        confirm_low_confidence: confirmLowConf,
        confirm_customer_identifiers: confirmCustId,
        confirm_custom_sku: confirmCustSku,
      });
    };

    try {
      const currentConfirmLowConfidence = confirmLowConfidence;
      let currentConfirmCustomerIdentifiers = false;
      let currentConfirmCustomSku = false;

      let success = false;
      let summary = null;
      let retries = 0;

      while (!success && retries < 3) {
        try {
          summary = await runImport(
            currentConfirmLowConfidence,
            currentConfirmCustomerIdentifiers,
            currentConfirmCustomSku
          );
          success = true;
        } catch (err: any) {
          const errMsg = err.message || "";
          const isPrivacyWarning = errMsg.includes("privacy warning") || errMsg.includes("customer identifiers");
          const isCustomSkuWarning = errMsg.includes("Invalid source column name") || errMsg.includes("invalid source column name");

          if (isPrivacyWarning && !currentConfirmCustomerIdentifiers) {
            const bypass = window.confirm(
              "Warning: You are mapping a column containing customer identifiers (like email or customer id) to the SKU field. Do you want to bypass this privacy warning and proceed?"
            );
            if (bypass) {
              currentConfirmCustomerIdentifiers = true;
              retries++;
              continue;
            } else {
              throw err;
            }
          } else if (isCustomSkuWarning && !currentConfirmCustomSku) {
            const bypass = window.confirm(
              "Warning: You are mapping a custom column to the SKU field. Do you want to bypass this warning and proceed?"
            );
            if (bypass) {
              currentConfirmCustomSku = true;
              retries++;
              continue;
            } else {
              throw err;
            }
          } else {
            throw err;
          }
        }
      }

      if (success && summary) {
        setImportSummary(summary);
        setIsMappingMode(false);
        setUploadInfo(null);
        fetchDatasets();

        if (summary.quality_score >= 85) {
          addToast(`Twin models synchronized successfully! Integrity score: ${summary.quality_score}%`, "success");
        } else {
          addToast(`Twin models synchronized with warning(s). Integrity score: ${summary.quality_score}%`, "info");
        }
      }
    } catch (err: any) {
      addToast(err.message || "Failed to import canonical data", "error");
    } finally {
      setUploading(false);
    }
  };


  const syncApiSource = async (sourceType: string) => {
    setSyncingApi(sourceType);
    addToast(`Connecting to ${sourceType.toUpperCase()} endpoint...`, "info");
    try {
      const summary = await api.importDataset({
        source_type: sourceType
      });
      setImportSummary(summary);
      setIsMappingMode(false);
      setUploadInfo(null);
      fetchDatasets();
      addToast(`${sourceType.toUpperCase()} store synced successfully! Integrity: ${summary.quality_score}%`, "success");
    } catch (err: any) {
      addToast(err.message || `Failed to sync from ${sourceType}`, "error");
    } finally {
      setSyncingApi(null);
    }
  };

  const triggerDatabaseCleanup = async () => {
    const confirmCleanup = window.confirm(
      "Are you sure you want to run database sanitization?\n\nThis will purge all fake numeric product records, invalid historical sales, and recalculate metrics for active catalog items."
    );
    if (!confirmCleanup) return;

    setClearingDb(true);
    addToast("Sanitizing database records & recalculating digital twin state...", "info");
    try {
      const res = await api.cleanupDataset({ confirm: true });
      addToast(res.message || `Database cleanup started! Purged ${res.metrics.products_removed} fake products.`, "success");
      fetchDatasets();
    } catch (err: any) {
      addToast(err.message || "Cleanup failed", "error");
    } finally {
      setClearingDb(false);
    }
  };

  const handleDeleteDataset = async (datasetId: number, datasetName: string) => {
    const confirmDelete = window.confirm(
      `Are you sure you want to permanently delete dataset "${datasetName}"?\n\nThis will purge the dataset log and all associated catalog items, sales histories, alerts, and forecasts from the database.`
    );
    if (!confirmDelete) return;

    addToast(`Deleting dataset "${datasetName}" and purging related items...`, "info");
    try {
      await api.deleteDataset(datasetId);
      addToast(`Dataset "${datasetName}" and all related elements successfully removed.`, "success");
      fetchDatasets();
    } catch (err: any) {
      addToast(err.message || "Failed to delete dataset", "error");
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="ferrari-panel p-8 space-y-8 text-zinc-100 font-sans shadow-2xl relative overflow-hidden bg-gradient-to-b from-raceBlack-1 to-raceBlack-2">
      {/* Decorative Scuderia Red/Yellow racing stripe top accent */}
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-red-600 via-yellow-500 to-red-600" />
      
      {/* Glowing grid background effect */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f1f23_1px,transparent_1px),linear-gradient(to_bottom,#1f1f23_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-20 pointer-events-none animate-gridPulse" />

      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 border-b border-zinc-800 pb-6 relative z-10">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-red-955/40 text-red-500 border border-red-900/50 font-mono text-[9px] font-bold tracking-widest uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-ping" /> PIT WALL STATUS: SECURE
            </span>
            <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase">SYS.REV: 3.8.4</span>
          </div>
          <h2 className="text-2xl font-mono font-black tracking-tight text-white flex items-center gap-2.5">
            <Fuel className="h-6 w-6 text-[#E10600] animate-pulse" /> FUEL INTAKE <span className="text-zinc-500 font-normal">/</span> TELEMETRY INGESTION
          </h2>
          <p className="text-xs text-zinc-400">
            Build canonical digital twin networks via structured schemas, simulated API connectors, and automated QA filters.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={triggerDatabaseCleanup}
            disabled={clearingDb || loading || uploading}
            className="flex items-center gap-2 px-4 py-2 border border-red-700/50 bg-red-955/20 hover:bg-red-955/40 text-red-400 hover:text-red-350 rounded-lg text-xs font-mono font-bold transition-all duration-300 cursor-pointer disabled:opacity-50 shadow-md shadow-red-950/30 hover:shadow-[0_0_12px_rgba(225,6,0,0.2)]"
            title="Purge fake SKU data and fix warehouse capacities"
          >
            {clearingDb ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            PURGE DATABASE RECORDS
          </button>
          
          <button
            onClick={fetchDatasets}
            disabled={loading || uploading}
            className="p-2 border border-zinc-800 rounded-lg bg-[#18181B] text-zinc-400 hover:text-white hover:border-zinc-700 hover:bg-zinc-800 transition-all duration-300 cursor-pointer disabled:opacity-50 shadow-sm"
            title="Refresh Registry"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* API Connectors Section */}
      {!isMappingMode && !importSummary && (
        <div className="space-y-4 relative z-10">
          <h3 className="text-[11px] font-mono font-extrabold tracking-widest text-[#FFDC00] uppercase flex items-center gap-2">
            <Server className="h-4 w-4 text-[#FFDC00]" /> ENTERPRISE ERP & LIVE TELEMETRY CHANNELS
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Shopify */}
            <div className="bg-gradient-to-b from-[#111115] to-[#070709] border border-zinc-800 hover:border-red-600/60 p-6 rounded-xl flex flex-col justify-between transition-all duration-300 group hover:-translate-y-1 shadow-md hover:shadow-[0_0_20px_rgba(225,6,0,0.15)] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-[9px] font-mono bg-zinc-900 text-zinc-400 border border-zinc-800 px-2 py-0.5 rounded uppercase tracking-wider">
                    Store API
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[9px] font-mono text-emerald-400 font-bold uppercase">LIVE</span>
                  </div>
                </div>
                <h4 className="font-mono font-bold text-sm text-white group-hover:text-red-500 transition-colors flex items-center gap-2">
                  <ShoppingBag className="h-4 w-4 text-emerald-400" /> Shopify Ingestion
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">
                  Extract real-time product catalogs, multi-location stock levels, and transaction histories from active Shopify instances.
                </p>
              </div>
              <button
                onClick={() => syncApiSource("shopify")}
                disabled={syncingApi !== null || uploading}
                className="mt-6 w-full py-2.5 rounded-lg bg-[#E10600] hover:bg-[#FF1B1B] disabled:bg-zinc-800 disabled:opacity-50 text-white font-mono font-bold text-xs tracking-wider transition-all duration-300 cursor-pointer flex items-center justify-center gap-2 shadow-md shadow-red-950/40"
              >
                {syncingApi === "shopify" ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                CONNECT & INGEST
              </button>
            </div>

            {/* Odoo */}
            <div className="bg-gradient-to-b from-[#111115] to-[#070709] border border-zinc-800 hover:border-red-600/60 p-6 rounded-xl flex flex-col justify-between transition-all duration-300 group hover:-translate-y-1 shadow-md hover:shadow-[0_0_20px_rgba(225,6,0,0.15)] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-2xl pointer-events-none" />
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-[9px] font-mono bg-zinc-900 text-zinc-400 border border-zinc-800 px-2 py-0.5 rounded uppercase tracking-wider">
                    ERP Integration
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[9px] font-mono text-emerald-400 font-bold uppercase">LIVE</span>
                  </div>
                </div>
                <h4 className="font-mono font-bold text-sm text-white group-hover:text-red-500 transition-colors flex items-center gap-2">
                  <Activity className="h-4 w-4 text-[#8A51C3]" /> Odoo Inventory
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">
                  Map Odoo inventory quant models directly. Resolves serials and updates lead times dynamically.
                </p>
              </div>
              <button
                onClick={() => syncApiSource("odoo")}
                disabled={syncingApi !== null || uploading}
                className="mt-6 w-full py-2.5 rounded-lg bg-[#E10600] hover:bg-[#FF1B1B] disabled:bg-zinc-800 disabled:opacity-50 text-white font-mono font-bold text-xs tracking-wider transition-all duration-300 cursor-pointer flex items-center justify-center gap-2 shadow-md shadow-red-950/40"
              >
                {syncingApi === "odoo" ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                CONNECT & INGEST
              </button>
            </div>

            {/* Zoho */}
            <div className="bg-gradient-to-b from-[#111115] to-[#070709] border border-zinc-800 hover:border-red-600/60 p-6 rounded-xl flex flex-col justify-between transition-all duration-300 group hover:-translate-y-1 shadow-md hover:shadow-[0_0_20px_rgba(225,6,0,0.15)] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-2xl pointer-events-none" />
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-[9px] font-mono bg-zinc-900 text-zinc-400 border border-zinc-800 px-2 py-0.5 rounded uppercase tracking-wider">
                    Warehouse Cloud
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[9px] font-mono text-emerald-400 font-bold uppercase">LIVE</span>
                  </div>
                </div>
                <h4 className="font-mono font-bold text-sm text-white group-hover:text-red-500 transition-colors flex items-center gap-2">
                  <Database className="h-4 w-4 text-blue-400" /> Zoho Inventory
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">
                  Pull stock updates, reorder point configurations, and supplier purchase records from Zoho Cloud.
                </p>
              </div>
<button
                onClick={() => syncApiSource("zoho_inventory")}
                disabled={syncingApi !== null || uploading}
                className="mt-6 w-full py-2.5 rounded-lg bg-[#E10600] hover:bg-[#FF1B1B] disabled:bg-zinc-800 disabled:opacity-50 text-white font-mono font-bold text-xs tracking-wider transition-all duration-300 cursor-pointer flex items-center justify-center gap-2 shadow-md shadow-red-950/40"
              >
                {syncingApi === "zoho_inventory" ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                CONNECT & INGEST
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Drag & Drop File Zone */}
      {!isMappingMode && !importSummary && (
        <div className="relative z-10">
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
            className={`relative bg-[#0b0b0e] border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${
              dragActive
                ? "border-[#E10600] bg-red-955/10 shadow-[0_0_25px_rgba(225,6,0,0.25)]"
                : "border-zinc-800 hover:border-[#E10600]/50 hover:bg-[#111116]"
            } ${uploading ? "opacity-60 pointer-events-none" : ""}`}
          >
            {/* Futuristic HUD corner brackets */}
            <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-zinc-700 transition-colors" />
            <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-zinc-700 transition-colors" />
            <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-zinc-700 transition-colors" />
            <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-zinc-700 transition-colors" />

            {/* Scanning laser line when dragging */}
            {dragActive && (
              <div className="absolute left-0 right-0 w-full h-[3px] bg-gradient-to-r from-transparent via-[#E10600] to-transparent shadow-[0_0_10px_#E10600] opacity-80 animate-scanline pointer-events-none" />
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              onChange={handleFileChange}
              className="hidden"
            />

            {uploading ? (
              <div className="space-y-6 w-full max-w-sm mx-auto">
                <div className="relative flex items-center justify-center">
                  <RefreshCw className="h-12 w-12 text-[#E10600] animate-spin" />
                  <span className="absolute text-[10px] font-mono font-bold text-white">{uploadProgress}%</span>
                </div>
                <div className="space-y-3">
                  <p className="font-mono font-bold text-sm text-white uppercase tracking-wider">
                    Ingesting Telemetry Stream
                  </p>
                  
                  {/* F1 styled RPM segmented progress bar */}
                  <div className="flex gap-1 justify-center items-center h-2.5 w-full max-w-xs mx-auto">
                    {Array.from({ length: 15 }).map((_, idx) => {
                      const step = (idx / 15) * 100;
                      const active = uploadProgress >= step;
                      let color = "bg-zinc-800";
                      if (active) {
                        if (idx < 8) color = "bg-green-500 shadow-[0_0_5px_#22c55e]";
                        else if (idx < 12) color = "bg-yellow-400 shadow-[0_0_5px_#facc15]";
                        else color = "bg-[#E10600] shadow-[0_0_8px_#e10600]";
                      }
                      return (
                        <div
                          key={idx}
                          className={`h-full flex-1 rounded-sm transition-all duration-300 ${color}`}
                        />
                      );
                    })}
                  </div>
                  
                  <p className="text-[10px] text-zinc-405 font-mono tracking-wide uppercase">
                    SYS.LOAD: Analyzing schema columns & mapping profiles...
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="h-14 w-14 rounded-full bg-[#050507] border border-zinc-800 flex items-center justify-center mx-auto text-[#E10600] shadow-md hover:scale-110 transition-transform">
                  <Upload className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="font-mono font-bold text-sm text-white uppercase tracking-wide">
                    Drag and drop file here, or <span className="text-[#FFDC00] hover:underline cursor-pointer">browse filesystem</span>
                  </p>
                  <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">
                    Supports CSV or Excel tables (.xlsx) up to 25MB
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mapping Workflow UI */}
      {isMappingMode && uploadInfo && (
        <div className="bg-[#0f0f13] border border-zinc-800 rounded-xl p-6 space-y-6 relative z-10">
          <div className="border-b border-zinc-800 pb-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
                <span className="text-[9px] font-mono bg-yellow-500/10 text-yellow-500 border border-yellow-800/50 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                  MAPPING INPUT FEED
                </span>
              </div>
              <h3 className="text-base font-mono font-bold text-white mt-1 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-[#FFDC00]" /> ALIGN SCHEMA TELEMETRY
              </h3>
              <p className="text-[11px] text-zinc-400 mt-1 font-mono">
                File: <span className="text-white font-bold">{uploadInfo.filename}</span> | Records: <span className="text-[#FFDC00] font-bold">{uploadInfo.rows.toLocaleString()}</span> | Columns: <span className="text-[#FFDC00] font-bold">{uploadInfo.columns_count}</span>
              </p>
            </div>
            <button
              onClick={() => {
                setIsMappingMode(false);
                setUploadInfo(null);
              }}
              className="px-3.5 py-1.5 text-xs font-mono font-bold border border-zinc-800 hover:bg-zinc-800 text-zinc-400 hover:text-white rounded-lg transition-colors cursor-pointer"
            >
              ABORT INGESTION
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Field Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-[11px] font-mono font-extrabold text-[#E10600] uppercase tracking-wider">
                  Canonical Target Mapping
                </h4>
                <span className="text-[9px] text-zinc-500 font-mono">3 MANDATORY REQUIRED</span>
              </div>
              
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-2">
                {CANONICAL_FIELDS.map(targetKey => {
                  const required = ["identity_key", "date", "stock_on_hand"].includes(targetKey);
                  const detection = uploadInfo.mappings[targetKey];
                  const bestMatch = detection?.best_match;
                  const selected = selectedMappings[targetKey];
                  const hasSelectedValue = !!selected;
                  
                  let statusBorder = "border-zinc-800 bg-[#070709]";
                  if (required && !hasSelectedValue) {
                    statusBorder = "border-red-900/40 bg-red-955/5";
                  } else if (hasSelectedValue) {
                    statusBorder = "border-zinc-800 bg-[#0b0b0f] hover:border-zinc-700";
                  }

                  return (
                    <div key={targetKey} className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 border rounded-lg transition-colors duration-200 ${statusBorder}`}>
                      <div className="space-y-0.5">
                        <span className="text-xs font-mono font-bold text-white flex items-center gap-2 uppercase">
                          {targetKey === "identity_key" ? "Identity Key (SKU)" : targetKey === "stock_on_hand" ? "Stock on Hand" : targetKey === "velocity_rate" ? "Velocity Rate" : targetKey.replace("_", " ")}
                          {required && (
                            <span className="text-[8px] font-mono text-[#E10600] border border-red-900/60 bg-red-955/40 px-1.5 rounded">
                              REQUIRED
                            </span>
                          )}
                        </span>
                        <p className="text-[10px] text-zinc-405">
                          {targetKey === "identity_key" && "Unique alphanumeric product code"}
                          {targetKey === "stock_on_hand" && "Current physical count in stock"}
                          {targetKey === "date" && "Standard date of transaction"}
                          {targetKey === "velocity_rate" && "Dynamic velocity rate mapping"}
                          {targetKey === "product_name" && "Visual catalogue title"}
                          {targetKey === "category" && "Department grouping hierarchy"}
                          {targetKey === "unit_cost" && "Wholesale purchase cost per item"}
                          {targetKey === "unit_price" && "Retail selling tag price"}
                          {targetKey === "warehouse" && "Physical distribution store node"}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2 shrink-0">
                        {bestMatch && selected === bestMatch && (
                          <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" title="High confidence auto-match" />
                        )}
                        <select
                          value={selected || ""}
                          onChange={(e) => handleMappingChange(targetKey, e.target.value)}
                          className="bg-[#121216] border border-zinc-800 text-xs text-zinc-200 rounded-lg p-2 font-mono focus:outline-none focus:border-[#E10600] w-full sm:w-[170px]"
                        >
                          <option value="">-- Ignored --</option>
                          {uploadInfo.columns.map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* File Sample Preview */}
            <div className="space-y-4">
              <h4 className="text-[11px] font-mono font-extrabold text-[#E10600] uppercase tracking-wider">
                Source Data Telemetry Preview
              </h4>
              <div className="bg-[#050507] border border-zinc-800 rounded-lg p-4 overflow-auto max-h-[380px] relative">
                <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-805 text-[8px] font-mono text-zinc-500 uppercase tracking-widest">
                  GRID PREVIEW
                </div>
                <table className="w-full text-left text-[10px] border-collapse font-mono hardware-table">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-450 bg-zinc-950/60">
                      {uploadInfo.columns.map(col => (
                        <th key={col} className="p-2.5 border-r border-zinc-800 font-bold tracking-wider">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {uploadInfo.sample_data.map((row, rIdx) => (
                      <tr key={rIdx} className="border-b border-zinc-900/60 hover:bg-[#111116] transition-colors">
                        {uploadInfo.columns.map(col => (
                          <td key={col} className="p-2.5 border-r border-zinc-900 text-zinc-300">
                            {row[col] === null ? (
                              <span className="text-zinc-650 italic">null</span>
                            ) : (
                              String(row[col])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[10px] text-zinc-505 italic font-mono uppercase tracking-wide">
                Showing first {uploadInfo.sample_data.length} telemetry samples of the input stream.
              </p>
            </div>
          </div>

          <div className="pt-5 border-t border-zinc-800 flex justify-end gap-3">
            <button
              onClick={() => {
                setIsMappingMode(false);
                setUploadInfo(null);
              }}
              className="px-5 py-2.5 border border-zinc-800 hover:bg-zinc-800 text-zinc-450 hover:text-white rounded-lg text-xs font-mono font-bold transition-all duration-300 cursor-pointer"
            >
              DISCARD INPUT
            </button>
            <button
              onClick={executeImport}
              className="px-6 py-2.5 bg-[#E10600] hover:bg-[#FF1B1B] text-white font-mono font-bold rounded-lg text-xs transition-all duration-300 cursor-pointer flex items-center gap-2 shadow-md shadow-red-950/40"
            >
              SYNC RETRAINING <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Data Quality Center Dashboard */}
      {importSummary && (
        <div className="bg-[#0f0f13] border border-zinc-800 rounded-xl p-6 space-y-6 relative z-10">
          <div className="border-b border-zinc-800 pb-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" />
                <span className="text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-900/50 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                  INGESTION COMPLETE
                </span>
              </div>
              <h3 className="text-base font-mono font-bold text-white mt-1 flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-emerald-400" /> TWIN INGESTION AUDIT REPORT
              </h3>
              <p className="text-[11px] text-zinc-405 mt-1 font-mono">
                Retraining dataset: <span className="text-white font-bold">{importSummary.name}</span> | Model Retraining: <span className="text-emerald-400 font-bold">QUEUED</span>
              </p>
            </div>
            <button
              onClick={() => setImportSummary(null)}
              className="px-4 py-2 bg-[#E10600] hover:bg-[#FF1B1B] text-white text-xs font-mono font-bold rounded-lg transition-colors duration-300 cursor-pointer shadow-md"
            >
              ACKNOWLEDGE LOGS
            </button>
          </div>

          {/* Telemetry HUD stats */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Quality speedometer circular HUD gauge */}
            <div className="lg:col-span-1 bg-[#070709] border border-zinc-800 p-6 rounded-xl flex flex-col justify-center items-center text-center space-y-4">
              <span className="text-[10px] font-mono text-zinc-405 tracking-wider uppercase font-bold">INTEGRITY COEFFICIENT</span>
              
              {/* SVG tachometer gauge */}
              <div className="relative h-28 w-28 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  {/* Background Track circle */}
                  <circle
                    cx="56"
                    cy="56"
                    r="46"
                    className="stroke-zinc-900"
                    strokeWidth="6"
                    fill="transparent"
                  />
                  {/* Dash gauge Track */}
                  <circle
                    cx="56"
                    cy="56"
                    r="46"
                    stroke={
                      importSummary.quality_score >= 90
                        ? "#10b981"
                        : importSummary.quality_score >= 70
                        ? "#facc15"
                        : "#e10600"
                    }
                    strokeWidth="6"
                    fill="transparent"
                    strokeDasharray="289"
                    strokeDashoffset={289 - (289 * importSummary.quality_score) / 100}
                    className="transition-all duration-1000 ease-out"
                    strokeLinecap="round"
                    style={{ filter: `drop-shadow(0 0 4px ${
                      importSummary.quality_score >= 90
                        ? "#10b981"
                        : importSummary.quality_score >= 70
                        ? "#facc15"
                        : "#e10600"
                    })` }}
                  />
                </svg>
                <div className="absolute flex flex-col justify-center items-center">
                  <span className={`text-2xl font-mono font-black ${
                    importSummary.quality_score >= 90
                      ? "text-emerald-400"
                      : importSummary.quality_score >= 70
                      ? "text-yellow-400"
                      : "text-red-500"
                  }`}>
                    {importSummary.quality_score}%
                  </span>
                  <span className="text-[8px] font-mono text-zinc-500 uppercase tracking-widest font-bold">QA INDEX</span>
                </div>
              </div>
              
              <span className="text-[10px] font-mono text-zinc-400 leading-normal uppercase">
                {importSummary.quality_score >= 90 ? (
                  <span className="text-emerald-400 font-bold">PRODUCTION COMPATIBLE</span>
                ) : importSummary.quality_score >= 70 ? (
                  <span className="text-yellow-400 font-bold">DEGRADED ACCURACY</span>
                ) : (
                  <span className="text-red-500 font-bold">CRITICAL CORRUPTION</span>
                )}
              </span>
            </div>

            {/* Ingestion stats */}
            <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-[#070709] border border-zinc-800 p-5 rounded-xl flex flex-col justify-between hover:border-zinc-700 transition-colors">
                <span className="text-[10px] font-mono text-zinc-400 font-bold uppercase tracking-wider">Processed stream</span>
                <span className="text-2xl font-mono font-black text-white mt-2">{importSummary.metrics.total_rows.toLocaleString()}</span>
                <span className="text-[9px] font-mono text-zinc-505 uppercase mt-1">TOTAL ROWS</span>
              </div>
              
              <div className="bg-[#070709] border border-zinc-800 p-5 rounded-xl flex flex-col justify-between hover:border-zinc-700 transition-colors">
                <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-wider">Validated Node</span>
                <span className="text-2xl font-mono font-black text-emerald-400 mt-2">{importSummary.metrics.imported_rows.toLocaleString()}</span>
                <span className="text-[9px] font-mono text-zinc-505 uppercase mt-1">IMPORTED ROWS</span>
              </div>

              <div className="bg-[#070709] border border-zinc-800 p-5 rounded-xl flex flex-col justify-between hover:border-zinc-700 transition-colors">
                <span className="text-[10px] font-mono text-red-500 font-bold uppercase tracking-wider">Purged stream</span>
                <span className="text-2xl font-mono font-black text-red-500 mt-2">{importSummary.metrics.rejected_rows.toLocaleString()}</span>
                <span className="text-[9px] font-mono text-zinc-505 uppercase mt-1">REJECTED ROWS</span>
              </div>

              <div className="bg-[#070709] border border-zinc-800 p-5 rounded-xl flex flex-col justify-between hover:border-zinc-700 transition-colors">
                <span className="text-[10px] font-mono text-white font-bold uppercase tracking-wider">Identified Catalog</span>
                <span className="text-2xl font-mono font-black text-[#FFDC00] mt-2">{importSummary.sku_count}</span>
                <span className="text-[9px] font-mono text-zinc-505 uppercase mt-1">UNIQUE SKUs</span>
              </div>
            </div>
          </div>

          {/* Warnings List */}
          <div className="space-y-3">
            <h4 className="text-[11px] font-mono font-extrabold text-[#E10600] uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" /> TELEMETRY QA WARNING LOGS ({importSummary.warnings.length})
            </h4>
            
            {importSummary.warnings.length === 0 ? (
              <div className="bg-[#070709] border border-emerald-950 p-4 rounded-lg text-xs text-emerald-400 font-mono flex items-center gap-2.5">
                <CheckCircle className="h-4 w-4 text-emerald-400" /> Telemetry validation completed with ZERO deviations. Integrity verified.
              </div>
            ) : (
              <div className="bg-[#070709] border border-zinc-800 p-4 rounded-lg font-mono text-[11px] text-yellow-500 space-y-2 max-h-[180px] overflow-y-auto leading-relaxed">
                {importSummary.warnings.map((warn, wIdx) => (
                  <div key={wIdx} className="flex items-start gap-2.5 hover:text-yellow-400 transition-colors">
                    <span className="text-[#E10600] font-black">»</span>
                    <span>{warn}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Datasets Table List */}
      <div className="space-y-4 relative z-10">
        <div className="flex justify-between items-center border-b border-zinc-800 pb-2">
          <h3 className="text-[11px] font-mono font-extrabold tracking-widest text-[#FFDC00] uppercase flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-[#FFDC00]" /> SYSTEM TELEMETRY DATASETS REGISTRY
          </h3>
          <span className="text-[9px] font-mono text-zinc-500">{datasets.length} REGISTERED FILES</span>
        </div>

        {loading && datasets.length === 0 ? (
          <div className="bg-[#0f0f13] border border-zinc-800 p-12 rounded-xl text-center text-xs text-zinc-500 font-mono flex items-center justify-center gap-2.5">
            <RefreshCw className="h-4 w-4 animate-spin text-[#E10600]" /> READING REGISTERED TELEMETRY FILES...
          </div>
        ) : datasets.length === 0 ? (
          <div className="bg-[#0f0f13] border border-zinc-800 p-16 rounded-xl text-center space-y-4">
            <FileText className="h-10 w-10 text-zinc-750 mx-auto animate-pulse" />
            <div className="space-y-1">
              <p className="font-mono font-bold text-sm text-zinc-400 uppercase">NO ACTIVE FILES REGISTRATION</p>
              <p className="text-[11px] text-zinc-505 max-w-xs mx-auto font-sans leading-relaxed">
                System registers are currently unseeded. Supply dataset CSV tables or link active API streams above.
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-[#0f0f13] border border-zinc-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse hardware-table">
                <thead>
                  <tr className="bg-[#050507] border-b border-zinc-800 text-zinc-450 font-mono text-[9px] uppercase tracking-wider">
                    <th className="p-4 font-bold">NAME</th>
                    <th className="p-4 font-bold">FILENAME</th>
                    <th className="p-4 font-bold text-right">ROWS</th>
                    <th className="p-4 font-bold text-right">SKUs</th>
                    <th className="p-4 font-bold text-center">INTEGRITY</th>
                    <th className="p-4 font-bold">DATE SPAN</th>
                    <th className="p-4 font-bold">OPERATOR</th>
                    <th className="p-4 font-bold">REGISTRY DATE</th>
                    <th className="p-4 font-bold text-center">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900 font-mono text-zinc-350">
                  {datasets.map((d) => (
                    <tr 
                      key={d.id} 
                      onClick={() => setSelectedAnalysisDataset(d)}
                      className="hover:bg-[#121217] transition-all duration-150 group border-l-2 border-transparent hover:border-l-[#E10600] cursor-pointer"
                    >
                      <td className="p-4 font-bold text-white group-hover:text-[#E10600] transition-colors flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-zinc-505" /> {d.name}
                      </td>
                      <td className="p-4 text-zinc-400 text-[11px]">{d.filename}</td>
                      <td className="p-4 text-right font-bold text-zinc-200">{d.rows.toLocaleString()}</td>
                      <td className="p-4 text-right text-zinc-200">{d.sku_count || "N/A"}</td>
                      <td className="p-4 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          d.quality_score >= 90
                            ? "bg-green-950/40 text-green-400 border border-green-900/40"
                            : d.quality_score >= 75
                            ? "bg-amber-950/40 text-amber-400 border border-amber-900/40"
                            : "bg-red-950/40 text-red-400 border border-red-900/40"
                        }`}>
                          {d.quality_score}%
                        </span>
                      </td>
                      <td className="p-4 text-zinc-405 text-[11px]">
                        {d.date_from ? `${d.date_from} → ${d.date_to}` : "N/A"}
                      </td>
                      <td className="p-4 text-zinc-400 capitalize font-sans">{d.owner}</td>
                      <td className="p-4 text-zinc-500 text-[10px]">
                        {new Date(d.uploaded_at).toLocaleString()}
                      </td>
                      <td className="p-4 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDataset(d.id, d.name);
                          }}
                          className="p-1 rounded hover:bg-red-955/20 border border-transparent hover:border-red-550/20 text-red-450 hover:text-red-400 transition-all duration-205 cursor-pointer"
                          title={`Delete dataset "${d.name}" and purge items`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Technical Standards Card */}
      <div className="bg-[#0f0f13] border border-zinc-800 rounded-xl p-5 flex items-start gap-4 relative z-10 hover:border-red-900/30 transition-all duration-300">
        <div className="p-2.5 rounded-lg bg-[#070709] border border-zinc-800 text-[#E10600]">
          <ShieldAlert className="h-5 w-5" />
        </div>
        <div className="space-y-1">
          <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
            QA VALIDATION COEFFICIENTS & RESTRICTIONS <span className="text-[9px] font-mono bg-[#070709] text-zinc-500 border border-zinc-800 px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">SCHEMA FILTER</span>
          </h4>
          <p className="text-xs text-zinc-400 leading-relaxed font-sans">
            The ingestion scheduler enforces strict relational validation. Inputs mapping to <code className="bg-[#070709] text-[#E10600] px-1 py-0.5 rounded border border-zinc-850 font-mono text-[10px]">Identity Key (SKU)</code>, <code className="bg-[#070709] text-[#E10600] px-1 py-0.5 rounded border border-zinc-850 font-mono text-[10px]">date</code>, and <code className="bg-[#070709] text-[#E10600] px-1 py-0.5 rounded border border-zinc-850 font-mono text-[10px]">stock_on_hand</code> must contain zero-null elements. Data blocks violating physical capacity ratios or structural identifiers are isolated as warning logs. Retraining operations require an integrity coefficient score above 70%.
          </p>
        </div>
      </div>

      {/* Historical Dataset Analysis Modal */}
      {selectedAnalysisDataset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#0f0f13] border border-zinc-800 rounded-xl max-w-2xl w-full relative overflow-hidden shadow-2xl font-mono text-zinc-350">
            {/* Scuderia Red/Yellow racing stripe top accent */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-600 via-yellow-500 to-red-600" />
            
            {/* Header */}
            <div className="border-b border-zinc-800 p-5 flex justify-between items-start">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" />
                  <span className="text-[9px] bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded font-bold uppercase tracking-wider text-zinc-405">
                    HISTORICAL TELEMETRY PROFILE
                  </span>
                </div>
                <h3 className="text-base font-black text-white flex items-center gap-2">
                  <FileText className="h-4 w-4 text-[#E10600]" /> {selectedAnalysisDataset.name}
                </h3>
                <p className="text-[9px] text-zinc-500">
                  Registry Record ID: <span className="text-white font-bold">{selectedAnalysisDataset.id}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedAnalysisDataset(null)}
                className="p-1 border border-zinc-800 rounded bg-[#18181B] text-zinc-405 hover:text-white hover:border-zinc-700 hover:bg-zinc-800 transition-colors cursor-pointer text-[10px] px-2.5 py-1.5 font-bold"
              >
                CLOSE
              </button>
            </div>

            {/* Body */}
            <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Quality Gauge (circular) */}
              <div className="bg-[#070709] border border-zinc-800 p-5 rounded-xl flex flex-col justify-center items-center text-center space-y-4">
                <span className="text-[9px] text-zinc-405 tracking-wider uppercase font-bold">INTEGRITY COEFFICIENT</span>
                
                <div className="relative h-24 w-24 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      className="stroke-zinc-900"
                      strokeWidth="5"
                      fill="transparent"
                    />
                    <circle
                      cx="48"
                      cy="48"
                      r="40"
                      stroke={
                        selectedAnalysisDataset.quality_score >= 90
                          ? "#10b981"
                          : selectedAnalysisDataset.quality_score >= 75
                          ? "#facc15"
                          : "#e10600"
                      }
                      strokeWidth="5"
                      fill="transparent"
                      strokeDasharray="251"
                      strokeDashoffset={251 - (251 * selectedAnalysisDataset.quality_score) / 100}
                      className="transition-all duration-1000 ease-out"
                      strokeLinecap="round"
                      style={{ filter: `drop-shadow(0 0 4px ${
                        selectedAnalysisDataset.quality_score >= 90
                          ? "#10b981"
                          : selectedAnalysisDataset.quality_score >= 75
                          ? "#facc15"
                          : "#e10600"
                      })` }}
                    />
                  </svg>
                  <div className="absolute flex flex-col justify-center items-center">
                    <span className={`text-xl font-black ${
                      selectedAnalysisDataset.quality_score >= 90
                        ? "text-emerald-400"
                        : selectedAnalysisDataset.quality_score >= 75
                        ? "text-yellow-400"
                        : "text-red-500"
                    }`}>
                      {selectedAnalysisDataset.quality_score}%
                    </span>
                    <span className="text-[8px] text-zinc-500 uppercase tracking-widest font-bold">QA INDEX</span>
                  </div>
                </div>
                
                <span className="text-[9px] leading-normal uppercase">
                  {selectedAnalysisDataset.quality_score >= 90 ? (
                    <span className="text-emerald-400 font-bold">PRODUCTION COMPATIBLE</span>
                  ) : selectedAnalysisDataset.quality_score >= 75 ? (
                    <span className="text-yellow-400 font-bold">DEGRADED ACCURACY</span>
                  ) : (
                    <span className="text-red-500 font-bold">CRITICAL CORRUPTION</span>
                  )}
                </span>
              </div>

              {/* Metrics grid */}
              <div className="md:col-span-2 space-y-4">
                <h4 className="text-[9px] font-extrabold text-[#E10600] uppercase tracking-wider border-b border-zinc-850 pb-1">
                  Ingestion Parameters
                </h4>
                <div className="grid grid-cols-2 gap-3.5">
                  <div className="bg-[#070709] border border-zinc-800 p-3 rounded-xl">
                    <div className="text-[9px] text-zinc-405 uppercase font-bold">Total Sales Records</div>
                    <div className="text-base font-black text-white mt-0.5">{selectedAnalysisDataset.rows.toLocaleString()}</div>
                    <div className="text-[8px] text-zinc-500 uppercase mt-0.5">Rows Ingested</div>
                  </div>
                  
                  <div className="bg-[#070709] border border-zinc-800 p-3 rounded-xl">
                    <div className="text-[9px] text-zinc-405 uppercase font-bold">Unique SKUs</div>
                    <div className="text-base font-black text-white mt-0.5">{selectedAnalysisDataset.sku_count || "N/A"}</div>
                    <div className="text-[8px] text-zinc-500 uppercase mt-0.5">Catalog Items</div>
                  </div>
                  
                  <div className="bg-[#070709] border border-zinc-800 p-3 rounded-xl col-span-2">
                    <div className="text-[9px] text-zinc-405 uppercase font-bold">Telemetry Date Span</div>
                    <div className="text-[11px] font-bold text-white mt-1 flex items-center gap-1.5">
                      <span className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded font-mono text-zinc-350">
                        {selectedAnalysisDataset.date_from || "N/A"}
                      </span>
                      <span className="text-zinc-500">→</span>
                      <span className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded font-mono text-zinc-350">
                        {selectedAnalysisDataset.date_to || "N/A"}
                      </span>
                    </div>
                  </div>

                  <div className="bg-[#070709] border border-zinc-800 p-3.5 rounded-xl col-span-2 space-y-1.5 font-sans">
                    <div className="flex justify-between items-center text-[9px] border-b border-zinc-800 pb-1 font-mono">
                      <span className="text-zinc-500 font-bold uppercase">Metadata Field</span>
                      <span className="text-zinc-505 font-bold uppercase">Value</span>
                    </div>
                    <div className="flex justify-between text-[10px] items-center">
                      <span className="text-zinc-405 font-mono uppercase">Filename</span>
                      <span className="text-zinc-200 truncate max-w-[200px]" title={selectedAnalysisDataset.filename}>{selectedAnalysisDataset.filename}</span>
                    </div>
                    <div className="flex justify-between text-[10px] items-center">
                      <span className="text-zinc-405 font-mono uppercase">Registered Operator</span>
                      <span className="text-zinc-200 capitalize">{selectedAnalysisDataset.owner}</span>
                    </div>
                    <div className="flex justify-between text-[10px] items-center">
                      <span className="text-zinc-405 font-mono uppercase">Registry Date</span>
                      <span className="text-zinc-200 text-[10px] font-mono">{new Date(selectedAnalysisDataset.uploaded_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-zinc-800 p-4 bg-[#070709] flex justify-end gap-2.5">
              <button
                onClick={() => {
                  const targetDataset = selectedAnalysisDataset;
                  setSelectedAnalysisDataset(null);
                  handleDeleteDataset(targetDataset.id, targetDataset.name);
                }}
                className="px-3.5 py-2 border border-red-750/50 bg-red-955/20 hover:bg-red-955/40 text-red-400 hover:text-red-350 rounded-lg text-[10px] font-bold transition-colors cursor-pointer flex items-center gap-1"
              >
                <Trash2 className="h-3 w-3" /> DELETE RECORD
              </button>
              <button
                onClick={() => setSelectedAnalysisDataset(null)}
                className="px-4.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-[10px] font-bold transition-colors cursor-pointer"
              >
                ACKNOWLEDGE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
