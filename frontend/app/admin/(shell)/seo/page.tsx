"use client";

import React, { useState } from "react";
import {
  useSEOTemplates,
  useCreateSEOTemplate,
  useDeleteSEOTemplate,
  useSEOPages,
  useGenerateSEOPages,
  useBatchPublishSEOPages,
} from "@/lib/hooks";
import { SEOPageItem, SEOTemplate } from "@/lib/api-client";

export default function SEOAdminPage() {
  const { data: templates, isLoading: loadingTemplates } = useSEOTemplates();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [minQuality, setMinQuality] = useState<number | undefined>(undefined);

  const { data: pages, isLoading: loadingPages } = useSEOPages({
    template_id: selectedTemplateId || undefined,
    status: statusFilter || undefined,
    min_quality_score: minQuality,
  });

  const generateMutation = useGenerateSEOPages();
  const batchPublishMutation = useBatchPublishSEOPages();
  const createTemplateMutation = useCreateSEOTemplate();
  const deleteTemplateMutation = useDeleteSEOTemplate();

  // Modals state
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [previewPage, setPreviewPage] = useState<SEOPageItem | null>(null);

  // Selected pages for batch publishing
  const [selectedPageIds, setSelectedPageIds] = useState<string[]>([]);

  // Generation form
  const [genTemplateId, setGenTemplateId] = useState<string>("");
  const [csvContent, setCsvContent] = useState<string>("");
  const [manualVarsText, setManualVarsText] = useState<string>(
    JSON.stringify(
      [
        { industry: "FinTech", city: "Chicago" },
        { industry: "Healthcare", city: "Boston" },
        { industry: "E-Commerce", city: "Seattle" },
      ],
      null,
      2
    )
  );

  // Template creation form
  const [newTemplateType, setNewTemplateType] = useState("industry_city");
  const [newUrlPattern, setNewUrlPattern] = useState("/find-leads/{industry}/{city}");
  const [newTitlePattern, setNewTitlePattern] = useState("Find {industry} Leads in {city} | GlobalReach");
  const [newH1Pattern, setNewH1Pattern] = useState("Find Verified {industry} Leads in {city}");
  const [newBodyPrompt, setNewBodyPrompt] = useState("Write actionable lead gen strategies for {industry} in {city}.");

  const totalPages = pages?.length || 0;
  const publishedPages = pages?.filter((p) => p.status === "published").length || 0;
  const draftPages = pages?.filter((p) => p.status === "draft").length || 0;
  const avgQuality =
    totalPages > 0
      ? Math.round((pages?.reduce((acc, p) => acc + (p.quality_score || 0), 0) || 0) / totalPages)
      : 0;

  const handleToggleSelectPage = (id: string) => {
    setSelectedPageIds((prev) =>
      prev.includes(id) ? prev.filter((pId) => pId !== id) : [...prev, id]
    );
  };

  const handleSelectAllDrafts = () => {
    const drafts = (pages || []).filter((p) => p.status === "draft").map((p) => p.id);
    setSelectedPageIds(drafts.slice(0, 50));
  };

  const handleBatchPublish = async () => {
    if (selectedPageIds.length === 0) return;
    await batchPublishMutation.mutateAsync(selectedPageIds);
    setSelectedPageIds([]);
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    const tId = genTemplateId || templates?.[0]?.id;
    if (!tId) return;

    let varsList = [];
    try {
      if (manualVarsText.trim()) {
        varsList = JSON.parse(manualVarsText);
      }
    } catch {
      alert("Invalid JSON format in manual variables.");
      return;
    }

    await generateMutation.mutateAsync({
      templateId: tId,
      variablesList: varsList,
      csvContent: csvContent.trim() || undefined,
    });
    setShowGenerateModal(false);
  };

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTemplateMutation.mutateAsync({
      type: newTemplateType,
      url_pattern: newUrlPattern,
      title_pattern: newTitlePattern,
      h1_pattern: newH1Pattern,
      body_prompt: newBodyPrompt,
    });
    setShowTemplateModal(false);
  };

  return (
    <div className="space-y-8">
      {/* Top Banner & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Programmatic SEO Manager</h1>
          <p className="text-xs text-slate-400 mt-1">
            Generate and publish thousands of high-converting programmatic SEO pages from templates.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowTemplateModal(true)}
            className="px-3.5 py-2 rounded-lg border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
          >
            + New Template
          </button>
          <button
            onClick={() => {
              setGenTemplateId(templates?.[0]?.id || "");
              setShowGenerateModal(true);
            }}
            className="px-4 py-2 rounded-lg font-bold text-xs text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110 shadow-md shadow-cyan-500/20 transition-all"
          >
            ⚡ Generate Batch
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-slate-400 font-medium">Total Pages</div>
          <div className="text-2xl font-bold text-white mt-1">{totalPages}</div>
          <div className="text-[10px] text-slate-500 mt-1">Across all templates</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-emerald-400 font-medium">Published</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{publishedPages}</div>
          <div className="text-[10px] text-slate-500 mt-1">Live in sitemap & indexing</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-amber-400 font-medium">Drafts Awaiting Approval</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{draftPages}</div>
          <div className="text-[10px] text-slate-500 mt-1">Quality checked & ready</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-cyan-400 font-medium">Avg Quality Score</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">{avgQuality} / 100</div>
          <div className="text-[10px] text-slate-500 mt-1">Enforced {">"} 65 threshold</div>
        </div>
      </div>

      {/* Filter & Batch Actions Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-xs text-slate-200"
          >
            <option value="">All Statuses</option>
            <option value="draft">Drafts Only</option>
            <option value="published">Published</option>
            <option value="rejected">Rejected (Thin/Duplicate)</option>
          </select>

          {/* Template Filter */}
          <select
            value={selectedTemplateId}
            onChange={(e) => setSelectedTemplateId(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-xs text-slate-200"
          >
            <option value="">All Templates</option>
            {templates?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.type} ({t.url_pattern})
              </option>
            ))}
          </select>

          {/* Quality Filter */}
          <select
            value={minQuality === undefined ? "" : String(minQuality)}
            onChange={(e) => setMinQuality(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-xs text-slate-200"
          >
            <option value="">All Quality Scores</option>
            <option value="80">Score ≥ 80 (High Quality)</option>
            <option value="70">Score ≥ 70 (Approved)</option>
          </select>
        </div>

        {/* Batch Publish Selected */}
        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <button
            onClick={handleSelectAllDrafts}
            className="text-xs text-slate-400 hover:text-slate-200 px-2 py-1"
          >
            Select Batch (20-50)
          </button>
          <button
            onClick={handleBatchPublish}
            disabled={selectedPageIds.length === 0 || batchPublishMutation.isPending}
            className="px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-950 bg-emerald-400 hover:brightness-110 disabled:opacity-40 transition-all"
          >
            {batchPublishMutation.isPending
              ? "Publishing..."
              : `Approve & Publish Batch (${selectedPageIds.length})`}
          </button>
        </div>
      </div>

      {/* Pages Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/30 overflow-hidden">
        {loadingPages ? (
          <div className="p-8 text-center text-xs text-slate-400">Loading SEO pages...</div>
        ) : pages && pages.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-semibold uppercase text-slate-400 bg-slate-950/40">
                  <th className="py-3 px-4 w-10">
                    <input
                      type="checkbox"
                      checked={selectedPageIds.length > 0 && selectedPageIds.length === pages.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPageIds(pages.map((p) => p.id));
                        } else {
                          setSelectedPageIds([]);
                        }
                      }}
                    />
                  </th>
                  <th className="py-3 px-4">Slug & Title</th>
                  <th className="py-3 px-4">Variables</th>
                  <th className="py-3 px-4">Quality Score</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {pages.map((p) => {
                  const isSelected = selectedPageIds.includes(p.id);
                  const isHighQuality = (p.quality_score || 0) >= 70;
                  return (
                    <tr key={p.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="py-3.5 px-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelectPage(p.id)}
                        />
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-200">
                        <div className="font-semibold text-white truncate max-w-sm">
                          {p.title || p.slug}
                        </div>
                        <div className="text-[11px] text-cyan-400 hover:underline">
                          /{p.slug}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">
                        {p.variables ? (
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(p.variables).map(([k, v]) => (
                              <span key={k} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px]">
                                {k}: {String(v)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5 font-bold">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isHighQuality ? "bg-emerald-400" : "bg-amber-400"
                            }`}
                          />
                          <span className={isHighQuality ? "text-emerald-400" : "text-amber-400"}>
                            {p.quality_score ?? "—"}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            p.status === "published"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : p.status === "rejected"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-2">
                        <button
                          onClick={() => setPreviewPage(p)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
                        >
                          Preview
                        </button>
                        {p.status === "draft" && (
                          <button
                            onClick={() => batchPublishMutation.mutateAsync([p.id])}
                            className="px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 text-xs font-semibold"
                          >
                            Approve
                          </button>
                        )}
                        {p.status === "published" && (
                          <a
                            href={`/${p.slug}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-2.5 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-semibold inline-block"
                          >
                            Live ↗
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500 text-xs">
            No programmatic pages generated yet. Click "Generate Batch" to create pages from variable combinations.
          </div>
        )}
      </div>

      {/* Generate Batch Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-2">⚡ Generate Programmatic SEO Pages</h3>
            <p className="text-xs text-slate-400 mb-4">
              Enter variable combinations (JSON or CSV). Each page will be drafted by Claude, evaluated for quality ({">"} 600 words, no duplicate content), and claims-checked.
            </p>

            <form onSubmit={handleGenerate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Choose Template
                </label>
                <select
                  value={genTemplateId}
                  onChange={(e) => setGenTemplateId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                >
                  {templates?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.type} — {t.url_pattern}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Variable Combinations (JSON Array)
                </label>
                <textarea
                  value={manualVarsText}
                  onChange={(e) => setManualVarsText(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white font-mono"
                  placeholder='[{"industry": "SaaS", "city": "Austin"}]'
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Or Upload / Paste CSV Content
                </label>
                <textarea
                  value={csvContent}
                  onChange={(e) => setCsvContent(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white font-mono"
                  placeholder="industry,city&#10;Logistics,Dallas&#10;Real Estate,Miami"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={generateMutation.isPending}
                  className="px-5 py-2 rounded-lg text-xs font-bold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110 disabled:opacity-50"
                >
                  {generateMutation.isPending ? "Generating Pages..." : "Generate Pages"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Template Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Create New SEO Template</h3>
            <p className="text-xs text-slate-400 mb-4">
              Define URL and title patterns with variable placeholders like {"{industry}"} and {"{city}"}.
            </p>

            <form onSubmit={handleCreateTemplate} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Type Slug</label>
                <input
                  type="text"
                  value={newTemplateType}
                  onChange={(e) => setNewTemplateType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">URL Pattern</label>
                <input
                  type="text"
                  value={newUrlPattern}
                  onChange={(e) => setNewUrlPattern(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Title Pattern</label>
                <input
                  type="text"
                  value={newTitlePattern}
                  onChange={(e) => setNewTitlePattern(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">H1 Pattern</label>
                <input
                  type="text"
                  value={newH1Pattern}
                  onChange={(e) => setNewH1Pattern(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Body Prompt</label>
                <textarea
                  value={newBodyPrompt}
                  onChange={(e) => setNewBodyPrompt(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTemplateModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTemplateMutation.isPending}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-cyan-400 hover:brightness-110"
                >
                  Save Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Page Preview Modal */}
      {previewPage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div>
                <h3 className="text-base font-bold text-white">{previewPage.title}</h3>
                <div className="text-xs text-cyan-400 font-mono">/{previewPage.slug}</div>
              </div>
              <button
                onClick={() => setPreviewPage(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-300 leading-relaxed">
              <div>
                <strong className="text-white block mb-1">Meta Description:</strong>
                <p className="text-slate-400 italic">{previewPage.meta_description}</p>
              </div>

              <div>
                <strong className="text-white block mb-1">Introduction:</strong>
                <p>{previewPage.content_json?.intro}</p>
              </div>

              <div>
                <strong className="text-white block mb-2">Sections ({previewPage.content_json?.sections?.length || 0}):</strong>
                <div className="space-y-3">
                  {previewPage.content_json?.sections?.map((s, idx) => (
                    <div key={idx} className="p-3 rounded-lg border border-slate-800 bg-slate-950">
                      <div className="font-bold text-cyan-300 mb-1">{s.heading}</div>
                      <div className="text-slate-400 whitespace-pre-line">{s.content}</div>
                    </div>
                  ))}
                </div>
              </div>

              {previewPage.content_json?.faq && (
                <div>
                  <strong className="text-white block mb-2">FAQs ({previewPage.content_json.faq.length}):</strong>
                  <div className="space-y-2">
                    {previewPage.content_json.faq.map((f, idx) => (
                      <div key={idx} className="p-2 rounded bg-slate-800/40">
                        <div className="font-semibold text-slate-200">Q: {f.question}</div>
                        <div className="text-slate-400">A: {f.answer}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-slate-800 mt-6">
              <button
                onClick={() => setPreviewPage(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700"
              >
                Close Preview
              </button>
              {previewPage.status === "draft" && (
                <button
                  onClick={async () => {
                    await batchPublishMutation.mutateAsync([previewPage.id]);
                    setPreviewPage(null);
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-emerald-400 hover:brightness-110"
                >
                  Approve & Publish Now
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
