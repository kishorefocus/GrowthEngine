"use client";

import React, { useState } from "react";
import Link from "next/link";
import { toolsApi, EmailVerifyToolResult } from "@/lib/api-client";

export default function EmailVerifierToolPage() {
  const [email, setEmail] = useState("founder@example.com");
  const [emailCaptured, setEmailCaptured] = useState("");
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EmailVerifyToolResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (e?: React.FormEvent, unlockEmail?: string) => {
    if (e) e.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const captured = unlockEmail || emailCaptured || undefined;
      const res = await toolsApi.verifyEmail(email.trim(), captured, "tool_email_verifier");
      setResult(res);
      if (res.requires_email_unlock) {
        setShowUnlockModal(true);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to verify email. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === "valid") {
      return <span className="px-3 py-1 rounded-full text-xs font-bold border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">✓ Deliverable (Valid)</span>;
    }
    if (status === "risky") {
      return <span className="px-3 py-1 rounded-full text-xs font-bold border border-amber-500/30 bg-amber-500/10 text-amber-400">⚠️ Risky (Disposable or Role-based)</span>;
    }
    if (status === "locked") {
      return <span className="px-3 py-1 rounded-full text-xs font-bold border border-violet-500/30 bg-violet-500/10 text-violet-400">🔒 Daily Limit Reached</span>;
    }
    return <span className="px-3 py-1 rounded-full text-xs font-bold border border-rose-500/30 bg-rose-500/10 text-rose-400">✕ Undeliverable (Invalid)</span>;
  };

  return (
    <div className="py-12 sm:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="mb-6 flex items-center gap-2 text-xs text-slate-400">
          <Link href="/" className="hover:text-cyan-400 transition-colors">Home</Link>
          <span className="text-slate-600">/</span>
          <span className="text-slate-300 font-medium">Free Tools</span>
          <span className="text-slate-600">/</span>
          <span className="text-cyan-400 font-medium">Email Verifier</span>
        </nav>

        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-teal-500/30 bg-teal-500/10 text-teal-300 text-xs font-semibold uppercase tracking-wider mb-4">
            🛡️ Zero-Bounce Verifier
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
            Free Single Email Verifier
          </h1>
          <p className="text-slate-300 text-base leading-relaxed">
            Verify email deliverability in real time with syntax inspection, live MX DNS resolution, disposable mailbox detection, and role account checks.
          </p>
        </div>

        {/* Verification Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 sm:p-8 backdrop-blur-sm shadow-xl mb-8">
          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Email Address to Verify
              </label>
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-700 bg-slate-950/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-500 font-mono"
                  required
                />
                <button
                  type="submit"
                  disabled={loading || !email.trim()}
                  className="py-3 px-8 rounded-xl font-bold text-sm text-slate-950 bg-gradient-to-r from-teal-400 to-cyan-300 hover:brightness-110 shadow-lg shadow-teal-500/20 disabled:opacity-50 transition-all cursor-pointer whitespace-nowrap"
                >
                  {loading ? "Checking MX Records..." : "Verify Deliverability →"}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Free tier limit: 5 checks per day per IP</span>
              {result && (
                <span className="text-cyan-400 font-medium">
                  {result.daily_checks_remaining} daily checks remaining
                </span>
              )}
            </div>
          </form>

          {error && (
            <div className="mt-4 p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs">
              {error}
            </div>
          )}
        </div>

        {/* Result Card */}
        {result && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 backdrop-blur-sm">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">Checked Address</div>
                  <div className="text-lg font-bold text-white font-mono break-all">{result.email}</div>
                </div>
                <div>{getStatusBadge(result.status)}</div>
              </div>

              {/* 4 Pillars Breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-6 border-b border-slate-800">
                <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 text-center">
                  <div className="text-xs text-slate-400 mb-1">Syntax Format</div>
                  <div className={`text-sm font-bold ${result.syntax_ok ? "text-emerald-400" : "text-rose-400"}`}>
                    {result.syntax_ok ? "Valid" : "Invalid"}
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 text-center">
                  <div className="text-xs text-slate-400 mb-1">Domain MX DNS</div>
                  <div className={`text-sm font-bold ${result.mx_ok ? "text-emerald-400" : "text-rose-400"}`}>
                    {result.mx_ok ? "Active MX" : "No Records"}
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 text-center">
                  <div className="text-xs text-slate-400 mb-1">Disposable Mailbox</div>
                  <div className={`text-sm font-bold ${result.is_disposable ? "text-rose-400" : "text-emerald-400"}`}>
                    {result.is_disposable ? "Burner/Temp" : "Legitimate"}
                  </div>
                </div>

                <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 text-center">
                  <div className="text-xs text-slate-400 mb-1">Role Account</div>
                  <div className={`text-sm font-bold ${result.is_role ? "text-amber-400" : "text-emerald-400"}`}>
                    {result.is_role ? "Generic/Role" : "Individual"}
                  </div>
                </div>
              </div>

              {/* Notes */}
              {result.notes && result.notes.length > 0 && (
                <div className="pt-4">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Deliverability Notes</div>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {result.notes.map((n, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span className="text-cyan-400">•</span>
                        <span>{n}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* GlobalReach Call to Action */}
            <div className="rounded-2xl border border-teal-500/30 bg-gradient-to-r from-teal-950/40 via-slate-900/60 to-cyan-950/40 p-8 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between gap-6 shadow-2xl">
              <div>
                <h3 className="text-xl sm:text-2xl font-extrabold text-white mb-2">
                  {result.cta.headline}
                </h3>
                <p className="text-sm text-slate-300 max-w-xl">
                  {result.cta.subheadline}
                </p>
              </div>
              <a
                href={result.cta.url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 rounded-xl font-bold text-sm text-slate-950 bg-gradient-to-r from-teal-400 via-cyan-300 to-emerald-400 hover:brightness-110 shadow-lg shadow-teal-500/20 whitespace-nowrap transition-transform hover:-translate-y-0.5"
              >
                {result.cta.button_text}
              </a>
            </div>
          </div>
        )}

        {/* Email Unlock Modal */}
        {showUnlockModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
              <h3 className="text-lg font-bold text-white mb-2">Unlock Unlimited Verifications</h3>
              <p className="text-xs text-slate-400 mb-4">
                You have reached your 5 free daily verifications. Enter your work email below to unlock bulk list uploads and unlimited single checks in GlobalReach.
              </p>
              <input
                type="email"
                placeholder="you@company.com"
                value={emailCaptured}
                onChange={(e) => setEmailCaptured(e.target.value)}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-700 bg-slate-950 text-white text-xs mb-3 focus:outline-none focus:border-cyan-500"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowUnlockModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowUnlockModal(false);
                    handleVerify(undefined, emailCaptured);
                  }}
                  disabled={!emailCaptured.includes("@")}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-teal-400 hover:brightness-110 disabled:opacity-50"
                >
                  Unlock & Verify Now
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
