"use client";

import React, { useState } from "react";
import Link from "next/link";
import { toolsApi, SubjectGradeResult } from "@/lib/api-client";

export default function SubjectLineGraderPage() {
  const [subject, setSubject] = useState("Quick question regarding {{company}}'s lead pipeline");
  const [industry, setIndustry] = useState("SaaS");
  const [emailCaptured, setEmailCaptured] = useState("");
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SubjectGradeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGrade = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!subject.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await toolsApi.gradeSubject(subject, industry, emailCaptured || undefined, "tool_subject_grader");
      setResult(res);
    } catch (err: any) {
      setError(err?.message || "Failed to grade subject line. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 60) return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    return "text-rose-400 border-rose-500/30 bg-rose-500/10";
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
          <span className="text-cyan-400 font-medium">Subject Line Grader</span>
        </nav>

        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-semibold uppercase tracking-wider mb-4">
            ⚡ Free Deliverability Tool
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
            Cold Email Subject Line Grader
          </h1>
          <p className="text-slate-300 text-base leading-relaxed">
            Test your cold email subject line for spam trigger keywords, optimal character length, and executive open rates. Get instant AI rewrites.
          </p>
        </div>

        {/* Input Form Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 sm:p-8 backdrop-blur-sm shadow-xl mb-8">
          <form onSubmit={handleGrade} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Cold Email Subject Line
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Quick question regarding {{company}}'s lead pipeline"
                className="w-full px-4 py-3 rounded-xl border border-slate-700 bg-slate-950/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all font-mono"
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Target Industry (Optional)
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-700 bg-slate-950/80 text-white text-xs focus:outline-none focus:border-cyan-500"
                >
                  <option value="SaaS">B2B SaaS / Tech</option>
                  <option value="Agency">Digital & Marketing Agencies</option>
                  <option value="Recruiting">Staffing & Recruiting</option>
                  <option value="Real Estate">Real Estate & Commercial</option>
                  <option value="Financial">FinTech & Financial Services</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={loading || !subject.trim()}
                  className="w-full py-2.5 px-6 rounded-lg font-bold text-sm text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110 shadow-lg shadow-cyan-500/20 disabled:opacity-50 transition-all cursor-pointer"
                >
                  {loading ? "Analyzing Subject Line..." : "Grade Subject Line →"}
                </button>
              </div>
            </div>
          </form>

          {error && (
            <div className="mt-4 p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs">
              {error}
            </div>
          )}
        </div>

        {/* Results Display */}
        {result && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Score & Breakdown Card */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 backdrop-blur-sm">
              <div className="flex flex-col sm:flex-row items-center gap-6 pb-6 border-b border-slate-800">
                <div className={`w-28 h-28 rounded-2xl border-2 flex flex-col items-center justify-center font-extrabold text-3xl shadow-xl ${getScoreColor(result.score)}`}>
                  <span>{result.score}</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mt-1">/ 100</span>
                </div>

                <div className="flex-1 text-center sm:text-left">
                  <h3 className="text-xl font-bold text-white mb-1">
                    {result.score >= 80 ? "🔥 Excellent Deliverability Score" : result.score >= 60 ? "⚠️ Moderate — Needs Polish" : "🚨 Low Score — Spam Risk"}
                  </h3>
                  <p className="text-xs text-slate-400 mb-3">
                    Character Count: <strong className="text-slate-200">{result.input_stats?.character_count} chars</strong> ({result.input_stats?.word_count} words) • Personalization: <strong className="text-slate-200">{result.input_stats?.has_personalization ? "Detected" : "None"}</strong>
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
                    {result.reasons.map((r, i) => (
                      <span key={i} className="text-xs px-2.5 py-1 rounded-md border border-slate-700 bg-slate-800/60 text-slate-300">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* 3 AI Rewrites */}
              <div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-base font-bold text-white">✨ 3 Optimized AI Rewrites</h4>
                  <button
                    onClick={() => setShowEmailModal(true)}
                    className="text-xs text-cyan-400 hover:underline font-medium"
                  >
                    Unlock 10+ niche variations →
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {result.rewrites.map((rw, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 hover:border-slate-700 transition-colors"
                    >
                      <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 mb-1">
                        {rw.style}
                      </div>
                      <div className="text-sm font-semibold text-slate-100 font-mono mb-2 break-words">
                        "{rw.subject}"
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        {rw.why_it_works}
                      </p>
                      <button
                        onClick={() => {
                          setSubject(rw.subject);
                          navigator.clipboard.writeText(rw.subject);
                        }}
                        className="mt-3 text-[11px] font-medium text-slate-400 hover:text-cyan-300 transition-colors"
                      >
                        Copy & Test This Line ↗
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* GlobalReach Call to Action */}
            <div className="rounded-2xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-indigo-950/40 p-8 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between gap-6 shadow-2xl">
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
                className="px-6 py-3 rounded-xl font-bold text-sm text-slate-950 bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400 hover:brightness-110 shadow-lg shadow-cyan-500/20 whitespace-nowrap transition-transform hover:-translate-y-0.5"
              >
                {result.cta.button_text}
              </a>
            </div>
          </div>
        )}

        {/* Email Unlock Modal */}
        {showEmailModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
              <h3 className="text-lg font-bold text-white mb-2">Unlock 10+ Tailored Rewrites</h3>
              <p className="text-xs text-slate-400 mb-4">
                Enter your work email to receive our full playbook of 50+ tested subject lines and weekly deliverability tips.
              </p>
              <input
                type="email"
                placeholder="you@company.com"
                value={emailCaptured}
                onChange={(e) => setEmailCaptured(e.target.value)}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-700 bg-slate-950 text-white text-xs mb-3"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowEmailModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowEmailModal(false);
                    handleGrade();
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-cyan-400 hover:brightness-110"
                >
                  Unlock Variations
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
