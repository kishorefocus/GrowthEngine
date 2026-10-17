"use client";

import React, { useState } from "react";
import {
  useIdeas,
  useGenerateIdeasBatch,
  useCreateIdea,
  useDeleteIdea,
  useGeneratePlatformPosts,
} from "@/lib/hooks";
import {
  Sparkles,
  Plus,
  RefreshCw,
  Layers,
  ArrowRight,
  Trash2,
  CheckCircle2,
  Filter,
  Lightbulb,
  Share2,
} from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";
import Link from "next/link";
import { useRouter } from "next/navigation";

const PILLARS = [
  { id: "all", label: "All Pillars", color: "bg-slate-800 text-slate-300" },
  { id: "how-to", label: "How-To Tutorials", color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20" },
  { id: "build-in-public", label: "Build in Public", color: "bg-sky-500/15 text-sky-400 border-sky-500/20" },
  { id: "competitor_alternatives", label: "Competitor Alternatives", color: "bg-purple-500/15 text-purple-400 border-purple-500/20" },
  { id: "industry_lead_lists", label: "Industry Lead Lists", color: "bg-amber-500/15 text-amber-400 border-amber-500/20" },
  { id: "tips_and_stats", label: "Tips & Stats", color: "bg-rose-500/15 text-rose-400 border-rose-500/20" },
];

export default function IdeasPage() {
  const router = useRouter();
  const [selectedPillar, setSelectedPillar] = useState<string>("all");
  const [isGenerating, setIsGenerating] = useState(false);
  const [showNewModal, setShowNewModal] = useState(false);
  const [newTopic, setNewTopic] = useState("");
  const [newPillar, setNewPillar] = useState("how-to");
  const [customPrompt, setCustomPrompt] = useState("");

  const { data: ideas, isLoading, refetch } = useIdeas({
    pillar: selectedPillar === "all" ? undefined : selectedPillar,
  });
  const generateBatchMutation = useGenerateIdeasBatch();
  const createIdeaMutation = useCreateIdea();
  const deleteIdeaMutation = useDeleteIdea();
  const generatePostsMutation = useGeneratePlatformPosts();

  const handleGenerateBatch = async () => {
    setIsGenerating(true);
    try {
      const res = await generateBatchMutation.mutateAsync({
        count: 20,
        customPrompt: customPrompt || undefined,
      });
      toast.success(`Generated ${res.generated_count} high-performing content ideas!`);
      setCustomPrompt("");
    } catch (err: any) {
      toast.error(`Generation error: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopic.trim()) return;
    try {
      await createIdeaMutation.mutateAsync({
        topic: newTopic.trim(),
        pillar: newPillar as any,
        source: "manual",
        status: "draft",
      });
      toast.success("Idea added successfully!");
      setNewTopic("");
      setShowNewModal(false);
    } catch (err: any) {
      toast.error(`Failed to add idea: ${err.message}`);
    }
  };

  const handleConvertToPosts = async (ideaId: string, topic: string) => {
    try {
      toast.info(`Drafting platform-adapted posts for: "${topic.slice(0, 35)}..."`);
      const res = await generatePostsMutation.mutateAsync({
        ideaId,
        platforms: ["x", "linkedin", "instagram", "facebook"],
      });
      toast.success(`Drafted ${res.posts.length} posts! Review them in the Approval Queue.`);
      router.push("/admin/calendar");
    } catch (err: any) {
      toast.error(`Adaptation failed: ${err.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteIdeaMutation.mutateAsync(id);
      toast.success("Idea deleted");
    } catch (err: any) {
      toast.error("Could not delete idea");
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            Content Ideas Studio
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 font-mono">
              5 Pillars
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Generate 20-idea batches across core growth pillars and convert them into platform-adapted posts with 1 click.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-200 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-all"
          >
            <Plus className="w-4 h-4 text-slate-400" />
            Add Manual
          </button>
          <button
            onClick={handleGenerateBatch}
            disabled={isGenerating || generateBatchMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 shadow-sm shadow-violet-600/30 transition-all disabled:opacity-50"
          >
            <Sparkles className={clsx("w-3.5 h-3.5", isGenerating && "animate-spin")} />
            {isGenerating ? "Generating 20 Ideas..." : "Generate Batch (20 Ideas)"}
          </button>
        </div>
      </div>

      {/* Pillar Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        {PILLARS.map((p) => (
          <button
            key={p.id}
            onClick={() => setSelectedPillar(p.id)}
            className={clsx(
              "px-3 py-1.5 rounded-xl text-xs font-medium border transition-all whitespace-nowrap",
              selectedPillar === p.id
                ? "bg-violet-600 text-white border-violet-500 shadow-sm shadow-violet-600/30"
                : "bg-white/[0.03] text-slate-400 border-white/[0.06] hover:bg-white/[0.06] hover:text-slate-200"
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Ideas List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-32 rounded-2xl bg-white/[0.02] border border-white/[0.06] animate-pulse" />
          ))}
        </div>
      ) : !ideas || ideas.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
          <Lightbulb className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No content ideas found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Click &quot;Generate Batch (20 Ideas)&quot; to immediately create curated lead generation and B2B growth concepts.
          </p>
          <button
            onClick={handleGenerateBatch}
            disabled={isGenerating}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generate First Batch
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ideas.map((idea) => {
            const pillarBadge = PILLARS.find((p) => p.id === idea.pillar) || {
              label: idea.pillar || "General",
              color: "bg-slate-800 text-slate-400 border-white/[0.06]",
            };

            return (
              <div
                key={idea.id}
                className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-white/10 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <span className={clsx("text-[10px] font-semibold px-2 py-0.5 rounded-md border", pillarBadge.color)}>
                      {pillarBadge.label}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      {idea.source}
                    </span>
                  </div>
                  <h4 className="text-sm font-medium text-slate-100 leading-snug">
                    {idea.topic}
                  </h4>
                </div>

                <div className="mt-5 pt-3 border-t border-white/[0.04] flex items-center justify-between gap-2">
                  <button
                    onClick={() => handleDelete(idea.id)}
                    className="p-1.5 rounded-lg text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                    title="Delete idea"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleConvertToPosts(idea.id, idea.topic)}
                    disabled={generatePostsMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/20 transition-all"
                  >
                    <Share2 className="w-3 h-3 text-violet-400" />
                    Convert to Posts
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Idea Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-2xl bg-[#0e0e17] border border-white/[0.08] shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Add Content Idea</h3>
            <form onSubmit={handleCreateManual} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Topic / Title</label>
                <textarea
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  placeholder="e.g. How to find verified real estate founders with 0% bounce..."
                  className="w-full h-24 px-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white text-xs placeholder-slate-600 focus:outline-none focus:border-violet-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Growth Pillar</label>
                <select
                  value={newPillar}
                  onChange={(e) => setNewPillar(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white text-xs focus:outline-none focus:border-violet-500"
                >
                  <option value="how-to">How-To Tutorials</option>
                  <option value="build-in-public">Build in Public</option>
                  <option value="competitor_alternatives">Competitor Alternatives</option>
                  <option value="industry_lead_lists">Industry Lead Lists</option>
                  <option value="tips_and_stats">Tips & Stats</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createIdeaMutation.isPending}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 transition-all"
                >
                  Save Idea
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
