"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Database,
  ExternalLink,
  Layers,
  PlusCircle,
  RefreshCw,
  Server,
  Terminal,
  XCircle,
} from "lucide-react";
import { fetchHealth, fetchItems, createItem, HealthResponse, Item } from "@/lib/api";

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newItemTitle, setNewItemTitle] = useState("");

  const checkConnection = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
      // Attempt to load items as well
      try {
        const itemList = await fetchItems();
        setItems(itemList);
      } catch {
        // Items endpoint might be empty or DB table initialising
      }
    } catch (err: any) {
      setError(
        err.message || "Failed to connect to backend. Is the Python server running on port 8000?"
      );
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemTitle.trim()) return;

    setIsSubmitting(true);
    try {
      await createItem(newItemTitle.trim(), "Test record created from GrowthEngine frontend");
      setNewItemTitle("");
      const updated = await fetchItems();
      setItems(updated);
    } catch (err: any) {
      alert(`Could not create item in PostgreSQL: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isBackendOk = health?.backend?.status === "online";
  const isDbOk = health?.database?.status === "connected";

  return (
    <main className="min-h-screen px-4 py-12 md:py-16 max-w-6xl mx-auto flex flex-col gap-10">
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-white/10 pb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium tracking-wide bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-3">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            ARCHITECTURE BLUEPRINT
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">
            GrowthEngine
          </h1>
          <p className="text-sm md:text-base text-slate-400 mt-2">
            Minimal, production-ready stack connecting <span className="text-white font-medium">Next.js</span>,{" "}
            <span className="text-white font-medium">Python (FastAPI)</span>, and{" "}
            <span className="text-white font-medium">PostgreSQL</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={checkConnection}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Checking..." : "Recheck Connection"}
          </button>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg glass-panel text-slate-300 hover:text-white text-sm font-medium hover:border-slate-600 transition-all"
          >
            <ExternalLink className="w-4 h-4" />
            API Docs
          </a>
        </div>
      </header>

      {/* Interconnected System Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Frontend Card */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl group-hover:bg-blue-500/20 transition-all pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Layers className="w-5 h-5" />
              </div>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Active
              </span>
            </div>
            <h3 className="text-lg font-bold text-white">Frontend Service</h3>
            <p className="text-xs text-slate-400 mt-1">Next.js 14 App Router with React & TypeScript</p>
          </div>

          <div className="mt-6 pt-4 border-t border-white/5 space-y-2 text-xs font-mono text-slate-400">
            <div className="flex justify-between">
              <span>Port:</span>
              <span className="text-slate-200">3000</span>
            </div>
            <div className="flex justify-between">
              <span>Client State:</span>
              <span className="text-emerald-400">Connected</span>
            </div>
          </div>
        </div>

        {/* Backend Card */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl group-hover:bg-cyan-500/20 transition-all pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                <Server className="w-5 h-5" />
              </div>
              {isBackendOk ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Online
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  <XCircle className="w-3.5 h-3.5" />
                  Offline
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold text-white">Backend Service</h3>
            <p className="text-xs text-slate-400 mt-1">Python FastAPI with CORS and Async Engine</p>
          </div>

          <div className="mt-6 pt-4 border-t border-white/5 space-y-2 text-xs font-mono text-slate-400">
            <div className="flex justify-between">
              <span>Framework:</span>
              <span className="text-slate-200">FastAPI</span>
            </div>
            <div className="flex justify-between">
              <span>Port:</span>
              <span className="text-slate-200">8000</span>
            </div>
          </div>
        </div>

        {/* Database Card */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl group-hover:bg-indigo-500/20 transition-all pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Database className="w-5 h-5" />
              </div>
              {isDbOk ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <Activity className="w-3.5 h-3.5" />
                  Waiting
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold text-white">Database Service</h3>
            <p className="text-xs text-slate-400 mt-1">PostgreSQL 16 with asyncpg driver & SQLAlchemy</p>
          </div>

          <div className="mt-6 pt-4 border-t border-white/5 space-y-2 text-xs font-mono text-slate-400">
            <div className="flex justify-between">
              <span>Dialect:</span>
              <span className="text-slate-200">{health?.database?.engine || "postgresql+asyncpg"}</span>
            </div>
            <div className="flex justify-between">
              <span>Ping Latency:</span>
              <span className={isDbOk ? "text-emerald-400" : "text-slate-400"}>
                {health?.database?.latency_ms !== null && health?.database?.latency_ms !== undefined
                  ? `${health.database.latency_ms} ms`
                  : "N/A"}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Error Banner if connection is not up */}
      {error && (
        <div className="glass-panel p-4 rounded-xl border-rose-500/30 bg-rose-950/20 text-rose-300 text-sm flex items-start gap-3">
          <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-rose-200">Backend is not reachable on port 8000</p>
            <p className="text-xs text-rose-300/80">{error}</p>
            <p className="text-xs text-slate-400 mt-2">
              Tip: Run <code className="bg-black/40 px-2 py-0.5 rounded text-amber-300">uvicorn app.main:app --reload --port 8000</code> in the backend folder or use <code className="bg-black/40 px-2 py-0.5 rounded text-amber-300">docker compose up</code> in the root.
            </p>
          </div>
        </div>
      )}

      {/* Interactive Verification: End-to-End Database Read / Write */}
      <section className="glass-panel p-6 md:p-8 rounded-2xl flex flex-col gap-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            End-to-End Connectivity Verification
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Test the live pipeline: Next.js Frontend <ArrowRight className="w-3.5 h-3.5 inline mx-1" /> Python FastAPI Backend <ArrowRight className="w-3.5 h-3.5 inline mx-1" /> PostgreSQL Database.
          </p>
        </div>

        {/* Create Test Record */}
        <form onSubmit={handleCreateItem} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={newItemTitle}
            onChange={(e) => setNewItemTitle(e.target.value)}
            placeholder="Type a record name (e.g. Test Client #1)..."
            disabled={!isBackendOk}
            className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!isBackendOk || isSubmitting || !newItemTitle.trim()}
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-all shadow-md shadow-blue-500/20 disabled:opacity-50"
          >
            <PlusCircle className="w-4 h-4" />
            {isSubmitting ? "Saving to DB..." : "Write to PostgreSQL"}
          </button>
        </form>

        {/* Database Records List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase tracking-wider">
            <span>PostgreSQL Records ({items.length})</span>
            <span>Table: public.items</span>
          </div>

          <div className="rounded-xl border border-white/10 bg-black/30 overflow-hidden divide-y divide-white/5">
            {items.length === 0 ? (
              <div className="p-6 text-center text-sm text-slate-500">
                {isBackendOk && isDbOk
                  ? "No test records found yet. Use the input above to insert a row into PostgreSQL!"
                  : "Database disconnected or server not responding. Connect services to view records."}
              </div>
            ) : (
              items.map((item) => (
                <div key={item.id} className="p-4 flex items-center justify-between gap-4 hover:bg-white/[0.02]">
                  <div>
                    <h4 className="text-sm font-semibold text-white">{item.title}</h4>
                    {item.description && (
                      <p className="text-xs text-slate-400 mt-0.5">{item.description}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[11px] font-mono text-slate-500">
                      ID #{item.id}
                    </span>
                    <p className="text-[10px] font-mono text-slate-500">
                      {new Date(item.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      {/* Raw Health JSON Envelope */}
      {health && (
        <section className="glass-panel p-6 rounded-2xl">
          <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wider mb-3">
            Live Healthcheck JSON Envelope (/health)
          </h3>
          <pre className="p-4 rounded-xl bg-black/50 border border-white/10 font-mono text-xs text-emerald-400 overflow-x-auto leading-relaxed">
            {JSON.stringify(health, null, 2)}
          </pre>
        </section>
      )}

      {/* Quickstart Command Reference */}
      <section className="glass-panel p-6 rounded-2xl space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          Quick Start Commands
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-2">
            <span className="text-slate-400 font-semibold block">1. Run with Docker Compose (Recommended)</span>
            <code className="text-emerald-400 block bg-black/60 p-2.5 rounded">
              docker compose up --build
            </code>
            <p className="text-slate-500 text-[11px]">Starts PostgreSQL 16, Python FastAPI, and Next.js in 1 command.</p>
          </div>

          <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-2">
            <span className="text-slate-400 font-semibold block">2. Run Locally</span>
            <code className="text-cyan-400 block bg-black/60 p-2.5 rounded">
              # Terminal 1 (Backend):<br />
              cd backend &amp;&amp; uvicorn app.main:app --reload --port 8000<br /><br />
              # Terminal 2 (Frontend):<br />
              cd frontend &amp;&amp; npm run dev
            </code>
          </div>
        </div>
      </section>
    </main>
  );
}
