"use client";

import { useState } from "react";
import {
  useCampaigns,
  useCampaign,
  useCampaignStats,
  useCreateCampaign,
  useUpdateCampaign,
  useDeleteCampaign,
  usePauseCampaign,
  useResumeCampaign,
  useCampaignSteps,
  useCreateCampaignStep,
  useUpdateCampaignStep,
  useDeleteCampaignStep,
  useIcps,
  useLeads,
  useEnrollLeads,
} from "@/lib/hooks";
import { campaignsApi, Campaign, SequenceStep } from "@/lib/api-client";
import { toast } from "sonner";
import {
  Plus,
  Play,
  Pause,
  Trash2,
  Edit2,
  Sparkles,
  Users,
  Clock,
  Mail,
  CheckCircle2,
  Eye,
  Send,
  ShieldAlert,
  Loader2,
  MessageSquare,
  XCircle,
  X,
} from "lucide-react";
import { clsx } from "clsx";

// ─── Spam Score Heuristic ─────────────────────────────────────────────────────

const SPAM_WORDS = [
  "guarantee", "guaranteed", "free", "no catch", "act now", "limited time",
  "make money", "winner", "risk-free", "urgent", "congratulations",
  "100% free", "instant cash", "click here", "buy now", "save big"
];

function calculateSpamScore(subject: string, body: string): { score: number; flags: string[] } {
  let score = 0;
  const flags: string[] = [];
  const text = (subject + " " + body).toLowerCase();

  for (const word of SPAM_WORDS) {
    if (text.includes(word)) {
      score += 2;
      flags.push(`Contains trigger word: "${word}"`);
    }
  }

  if (subject.length > 60) {
    score += 1;
    flags.push("Subject is long (>60 chars)");
  }

  if (subject && subject === subject.toUpperCase() && subject.replace(/[^a-zA-Z]/g, "").length > 5) {
    score += 3;
    flags.push("Subject is in ALL CAPS");
  }

  if (/[!]{2,}|\?{2,}/.test(subject + body)) {
    score += 1.5;
    flags.push("Multiple exclamation or question marks");
  }

  if ((text.match(/\$/g) || []).length > 2) {
    score += 1.5;
    flags.push("Excessive dollar signs ($)");
  }

  return { score: Math.min(10, Math.round(score * 10) / 10), flags };
}

// ─── Campaign List & Detail Page ──────────────────────────────────────────────

export default function CampaignsPage() {
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data: campaigns, isLoading } = useCampaigns();

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Outreach Campaigns</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Compliant multi-step cold email sequences with AI personalization
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold transition-all shadow-lg shadow-violet-500/20 w-fit"
        >
          <Plus className="w-4 h-4" />
          New Campaign
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12 text-slate-500 text-sm gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
          Loading campaigns...
        </div>
      ) : campaigns && campaigns.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06]">
          <Mail className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No campaigns yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Create your first multi-step cold outreach sequence to target your verified leads.
          </p>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold"
          >
            <Plus className="w-4 h-4" />
            Create Campaign
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Campaign List Sidebar */}
          <div className="lg:col-span-4 space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
              Active & Draft Campaigns ({campaigns?.length})
            </h3>
            {campaigns?.map((c) => {
              const isSelected = (selectedCampaignId || campaigns[0]?.id) === c.id;
              const winText = c.sending_window ? `${c.sending_window.start} - ${c.sending_window.end}` : "09:00 - 17:00";
              return (
                <div
                  key={c.id}
                  onClick={() => setSelectedCampaignId(c.id)}
                  className={clsx(
                    "p-4 rounded-xl border cursor-pointer transition-all text-left",
                    isSelected
                      ? "bg-violet-600/10 border-violet-500/40 shadow-sm"
                      : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] hover:border-white/10"
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm text-white truncate mr-2">
                      {c.name}
                    </span>
                    <span
                      className={clsx(
                        "text-[10px] font-mono px-2 py-0.5 rounded-full capitalize shrink-0 font-medium",
                        c.status === "active" && "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
                        c.status === "paused" && "bg-amber-500/15 text-amber-400 border border-amber-500/30",
                        c.status === "draft" && "bg-slate-500/15 text-slate-400 border border-slate-500/30",
                        c.status === "completed" && "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                      )}
                    >
                      {c.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {winText}
                    </span>
                    <span>Limit: {c.daily_limit}/day</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Campaign Detail / Builder */}
          <div className="lg:col-span-8">
            <CampaignDetailView
              campaignId={selectedCampaignId || campaigns?.[0]?.id || ""}
            />
          </div>
        </div>
      )}

      {/* Create Modal */}
      {isCreateOpen && (
        <CreateCampaignModal onClose={() => setIsCreateOpen(false)} />
      )}
    </div>
  );
}

// ─── Campaign Detail View ─────────────────────────────────────────────────────

function CampaignDetailView({ campaignId }: { campaignId: string }) {
  const { data: campaign, isLoading } = useCampaign(campaignId);
  const { data: stats } = useCampaignStats(campaignId);
  const { data: steps, refetch: refetchSteps } = useCampaignSteps(campaignId);
  const pause = usePauseCampaign();
  const resume = useResumeCampaign();
  const deleteCamp = useDeleteCampaign();

  const [isEditingSettings, setIsEditingSettings] = useState(false);
  const [isAddStepOpen, setIsAddStepOpen] = useState(false);
  const [editingStep, setEditingStep] = useState<SequenceStep | null>(null);
  const [isEnrollOpen, setIsEnrollOpen] = useState(false);

  if (isLoading || !campaign) {
    return (
      <div className="p-8 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-violet-400" />
        Loading campaign details...
      </div>
    );
  }

  const winText = campaign.sending_window
    ? `${campaign.sending_window.start} - ${campaign.sending_window.end}`
    : "09:00 - 17:00";

  const handleToggleStatus = async () => {
    try {
      if (campaign.status === "active") {
        await pause.mutateAsync(campaign.id);
        toast.info("Campaign paused");
      } else {
        await resume.mutateAsync(campaign.id);
        toast.success("Campaign resumed / activated");
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to update campaign status");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this campaign?")) return;
    try {
      await deleteCamp.mutateAsync(campaign.id);
      toast.success("Campaign deleted");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete campaign");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Controls */}
      <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-bold text-white">{campaign.name}</h3>
              <span
                className={clsx(
                  "text-xs font-mono px-2.5 py-0.5 rounded-full capitalize font-medium",
                  campaign.status === "active" && "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
                  campaign.status === "paused" && "bg-amber-500/15 text-amber-400 border border-amber-500/30",
                  campaign.status === "draft" && "bg-slate-500/15 text-slate-400 border border-slate-500/30"
                )}
              >
                {campaign.status}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Window: {winText} ({campaign.timezone_mode}) · Daily Limit: {campaign.daily_limit} emails
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsEnrollOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs font-medium text-slate-200 border border-white/[0.08] transition-all"
            >
              <Users className="w-3.5 h-3.5 text-violet-400" />
              Enroll Leads
            </button>
            <button
              onClick={handleToggleStatus}
              disabled={pause.isPending || resume.isPending}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-sm",
                campaign.status === "active"
                  ? "bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white"
              )}
            >
              {campaign.status === "active" ? (
                <><Pause className="w-3.5 h-3.5" /> Pause</>
              ) : (
                <><Play className="w-3.5 h-3.5" /> Launch / Resume</>
              )}
            </button>
            <button
              onClick={() => setIsEditingSettings(!isEditingSettings)}
              className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.08] text-slate-400 hover:text-white transition-all"
              title="Edit Settings"
            >
              <Edit2 className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 transition-all"
              title="Delete Campaign"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Quick Settings Edit Drawer */}
        {isEditingSettings && (
          <CampaignSettingsForm
            campaign={campaign}
            onClose={() => setIsEditingSettings(false)}
          />
        )}
      </div>

      {/* Aggregate Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatMetric label="Sent" value={stats?.sent ?? 0} icon={<Send className="w-3.5 h-3.5 text-violet-400" />} />
        <StatMetric label="Delivered" value={stats?.delivered ?? 0} icon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />} />
        <StatMetric label="Opened" value={stats?.opened ?? 0} icon={<Eye className="w-3.5 h-3.5 text-blue-400" />} />
        <StatMetric label="Replied" value={stats?.replied ?? 0} icon={<MessageSquare className="w-3.5 h-3.5 text-amber-400" />} />
        <StatMetric label="Bounced" value={stats?.bounced ?? 0} icon={<XCircle className="w-3.5 h-3.5 text-rose-400" />} />
      </div>

      {/* Sequence Steps Builder */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-white">Sequence Steps</h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated follow-ups that automatically stop on reply, bounce, or unsubscribe.
            </p>
          </div>
          <button
            onClick={() => setIsAddStepOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 text-xs font-semibold border border-violet-500/30 transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Step
          </button>
        </div>

        {steps && steps.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-white/[0.01] border border-dashed border-white/[0.08]">
            <p className="text-xs text-slate-500">No steps defined yet. Add Step 1 to begin your sequence.</p>
          </div>
        ) : (
          <div className="space-y-4 relative">
            {steps?.map((step, idx) => (
              <StepCard
                key={step.id}
                step={step}
                campaignId={campaign.id}
                isFirst={idx === 0}
                onEdit={() => setEditingStep(step)}
                onDeleted={() => refetchSteps()}
              />
            ))}
          </div>
        )}
      </div>

      {/* Add Step Modal */}
      {isAddStepOpen && (
        <StepEditorModal
          campaignId={campaign.id}
          nextStepNumber={(steps?.length || 0) + 1}
          onClose={() => {
            setIsAddStepOpen(false);
            refetchSteps();
          }}
        />
      )}

      {/* Edit Step Modal */}
      {editingStep && (
        <StepEditorModal
          campaignId={campaign.id}
          step={editingStep}
          onClose={() => {
            setEditingStep(null);
            refetchSteps();
          }}
        />
      )}

      {/* Enroll Leads Modal */}
      {isEnrollOpen && (
        <EnrollLeadsModal
          campaignId={campaign.id}
          icpId={campaign.icp_id}
          onClose={() => setIsEnrollOpen(false)}
        />
      )}
    </div>
  );
}

// ─── Metric Box ───────────────────────────────────────────────────────────────

function StatMetric({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] flex items-center gap-3">
      <div className="p-2 rounded-lg bg-white/[0.04]">{icon}</div>
      <div>
        <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">{label}</p>
        <p className="text-base font-bold text-white tabular-nums">{value.toLocaleString()}</p>
      </div>
    </div>
  );
}

// ─── Step Card Component ──────────────────────────────────────────────────────

function StepCard({
  step,
  campaignId,
  isFirst,
  onEdit,
  onDeleted,
}: {
  step: SequenceStep;
  campaignId: string;
  isFirst: boolean;
  onEdit: () => void;
  onDeleted: () => void;
}) {
  const deleteStep = useDeleteCampaignStep(campaignId);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete Step ${step.step_number}?`)) return;
    try {
      await deleteStep.mutateAsync(step.id);
      toast.success(`Step ${step.step_number} deleted`);
      onDeleted();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete step");
    }
  };

  const spam = calculateSpamScore(step.subject_template || "", step.body_template || "");

  return (
    <div className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.1] transition-all space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-full bg-violet-600/20 text-violet-400 font-mono text-xs flex items-center justify-center font-bold">
            {step.step_number}
          </span>
          <span className="text-sm font-semibold text-white">
            {isFirst ? "Initial Outreach" : `Follow-up (+${step.delay_days} days)`}
          </span>
          {step.ai_personalize && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-medium">
              <Sparkles className="w-3 h-3" />
              AI Personalized
            </span>
          )}
          {/* Spam hint */}
          <span
            className={clsx(
              "text-[10px] font-mono px-2 py-0.5 rounded-md border",
              spam.score < 2
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : spam.score < 5
                ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
            )}
            title={spam.flags.join(", ") || "Clean copy"}
          >
            Spam Risk: {spam.score}/10
          </span>
        </div>

        <div className="flex items-center gap-2">
          {step.ai_personalize && (
            <button
              onClick={() => setIsPreviewOpen(true)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-medium border border-amber-500/20 transition-all"
            >
              <Eye className="w-3.5 h-3.5" />
              AI Preview
            </button>
          )}
          <button
            onClick={onEdit}
            className="p-1 rounded-lg text-slate-400 hover:text-white transition-all"
            title="Edit Step"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1 rounded-lg text-rose-400 hover:text-rose-300 transition-all"
            title="Delete Step"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Subject & Preview */}
      <div className="p-3 rounded-lg bg-black/40 border border-white/[0.04] space-y-1">
        <p className="text-xs text-slate-300">
          <span className="text-slate-500 font-mono">Subject: </span>
          {step.subject_template}
        </p>
        <p className="text-xs text-slate-400 line-clamp-2">
          <span className="text-slate-500 font-mono">Body: </span>
          {step.body_template}
        </p>
      </div>

      {/* AI Preview Modal */}
      {isPreviewOpen && (
        <AiPreviewModal
          campaignId={campaignId}
          stepId={step.id}
          stepNumber={step.step_number}
          onClose={() => setIsPreviewOpen(false)}
        />
      )}
    </div>
  );
}

// ─── Step Editor Modal ────────────────────────────────────────────────────────

function StepEditorModal({
  campaignId,
  step,
  nextStepNumber = 1,
  onClose,
}: {
  campaignId: string;
  step?: SequenceStep;
  nextStepNumber?: number;
  onClose: () => void;
}) {
  const createStep = useCreateCampaignStep(campaignId);
  const updateStep = useUpdateCampaignStep(campaignId);

  const [form, setForm] = useState({
    step_number: step ? step.step_number : nextStepNumber,
    delay_days: step ? step.delay_days : (nextStepNumber === 1 ? 0 : 3),
    subject_template: step ? (step.subject_template || "") : "",
    body_template: step ? (step.body_template || "") : "",
    ai_personalize: step ? step.ai_personalize : false,
  });

  const spam = calculateSpamScore(form.subject_template, form.body_template);

  const insertMerge = (field: string, target: "subject" | "body") => {
    if (target === "subject") {
      setForm((prev) => ({ ...prev, subject_template: prev.subject_template + ` {${field}}` }));
    } else {
      setForm((prev) => ({ ...prev, body_template: prev.body_template + ` {${field}}` }));
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.subject_template.trim() || !form.body_template.trim()) {
      toast.error("Subject and body are required");
      return;
    }

    try {
      if (step) {
        await updateStep.mutateAsync({
          stepId: step.id,
          data: form,
        });
        toast.success(`Step ${form.step_number} updated`);
      } else {
        await createStep.mutateAsync(form);
        toast.success(`Step ${form.step_number} added to sequence`);
      }
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to save step");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f0f17] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-white/[0.08]">
          <h3 className="text-base font-bold text-white">
            {step ? `Edit Step ${step.step_number}` : `Add Step ${nextStepNumber}`}
          </h3>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-5 space-y-4 overflow-y-auto flex-1">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Step Number</label>
              <input
                type="number"
                min={1}
                value={form.step_number}
                onChange={(e) => setForm({ ...form, step_number: parseInt(e.target.value) || 1 })}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Delay After Previous Step (Days)
              </label>
              <input
                type="number"
                min={0}
                value={form.delay_days}
                onChange={(e) => setForm({ ...form, delay_days: parseInt(e.target.value) || 0 })}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
              />
            </div>
          </div>

          {/* AI Personalize Toggle */}
          <div className="p-3.5 rounded-xl bg-amber-500/[0.06] border border-amber-500/20 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <div>
                <p className="text-xs font-semibold text-white">AI Personalization (Claude 3.5 Sonnet)</p>
                <p className="text-[11px] text-slate-400">
                  Researches lead company & website, generates truthful 60-100 word copy verified with claims guard.
                </p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={form.ai_personalize}
                onChange={(e) => setForm({ ...form, ai_personalize: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-500"></div>
            </label>
          </div>

          {/* Merge Field Selector */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-400">Insert Merge Tag</label>
              <span className="text-[11px] text-slate-500">Click to append to template</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {["first_name", "last_name", "company", "title", "website", "country"].map((field) => (
                <button
                  type="button"
                  key={field}
                  onClick={() => insertMerge(field, "body")}
                  className="px-2 py-1 rounded bg-white/[0.04] hover:bg-violet-600/20 hover:text-violet-300 text-[11px] font-mono text-slate-400 border border-white/[0.06] transition-all"
                >
                  +{`{${field}}`}
                </button>
              ))}
            </div>
          </div>

          {/* Subject Line */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-400">Subject Template</label>
              <span className="text-[10px] text-slate-500">{form.subject_template.length}/60 chars</span>
            </div>
            <input
              type="text"
              value={form.subject_template}
              onChange={(e) => setForm({ ...form, subject_template: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50"
              placeholder="Quick question regarding {company}"
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Email Body (Plain Text)</label>
            <textarea
              rows={6}
              value={form.body_template}
              onChange={(e) => setForm({ ...form, body_template: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50 font-sans resize-none"
              placeholder="Hi {first_name},&#10;&#10;I noticed {company} has been expanding recently. We found your profile through GlobalReach...&#10;&#10;Would you have 10 minutes next Tuesday?"
            />
          </div>

          {/* Spam Score Card */}
          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-3">
            <ShieldAlert className={clsx("w-4 h-4 mt-0.5 shrink-0", spam.score < 3 ? "text-emerald-400" : spam.score < 5 ? "text-amber-400" : "text-rose-400")} />
            <div className="text-xs space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white">Spam Score Heuristic: {spam.score}/10</span>
                <span className={clsx("text-[10px] font-medium", spam.score < 3 ? "text-emerald-400" : spam.score < 5 ? "text-amber-400" : "text-rose-400")}>
                  {spam.score < 3 ? "Great deliverability" : spam.score < 5 ? "Moderate risk" : "High spam trigger risk"}
                </span>
              </div>
              {spam.flags.length > 0 && (
                <ul className="text-slate-400 list-disc list-inside text-[11px]">
                  {spam.flags.map((flag, i) => (
                    <li key={i}>{flag}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createStep.isPending || updateStep.isPending}
              className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/20 disabled:opacity-60"
            >
              {createStep.isPending || updateStep.isPending ? "Saving..." : "Save Step"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── AI Preview Modal ─────────────────────────────────────────────────────────

function AiPreviewModal({
  campaignId,
  stepId,
  stepNumber,
  onClose,
}: {
  campaignId: string;
  stepId: string;
  stepNumber: number;
  onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [leadId, setLeadId] = useState("");
  const { data: leads } = useLeads({ verification_status: "valid" });

  const handleGenerate = async (selectedId?: string) => {
    const targetLeadId = selectedId || leadId;
    if (!targetLeadId) {
      toast.error("Please select a lead first");
      return;
    }
    setLoading(true);
    try {
      const res = await campaignsApi.previewAi(campaignId, targetLeadId, stepId);
      setResult(res);
      toast.success("AI personalization generated");
    } catch (err: any) {
      toast.error(err.message || "Failed to generate AI copy preview");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-[#0f0f17] border border-white/10 rounded-2xl w-full max-w-xl max-h-[85vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <h3 className="text-base font-bold text-white">AI Copy Preview (Step {stepNumber})</h3>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Select Sample Lead to Personalize For
            </label>
            <div className="flex gap-2">
              <select
                value={leadId}
                onChange={(e) => setLeadId(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
              >
                <option value="">Select a verified lead...</option>
                {leads?.map((lead) => (
                  <option key={lead.id} value={lead.id}>
                    {lead.first_name} {lead.last_name || ""} ({lead.company || lead.email})
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => handleGenerate()}
                disabled={loading || !leadId}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-semibold shrink-0 transition-all disabled:opacity-60"
              >
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                Generate
              </button>
            </div>
          </div>

          {result && (
            <div className="space-y-3 pt-2">
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block mb-1">
                    Generated Subject
                  </span>
                  <p className="text-sm font-semibold text-white bg-black/40 p-2.5 rounded-lg border border-white/[0.04]">
                    {result.subject}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block mb-1">
                    Generated Body
                  </span>
                  <p className="text-xs text-slate-300 bg-black/40 p-3 rounded-lg border border-white/[0.04] whitespace-pre-wrap leading-relaxed">
                    {result.body}
                  </p>
                </div>
              </div>

              {/* Guardrails check */}
              <div className="flex items-center gap-4 text-[11px] text-slate-400 px-1">
                <span className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Claims Guard Passed
                </span>
                <span>Word count: {result.body.split(/\s+/).length} words</span>
                <span className="text-amber-400 font-mono">Dogfooding pitch included</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end p-4 border-t border-white/[0.08]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-xs font-semibold text-white"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Campaign Settings Form ───────────────────────────────────────────────────

function CampaignSettingsForm({
  campaign,
  onClose,
}: {
  campaign: Campaign;
  onClose: () => void;
}) {
  const update = useUpdateCampaign();
  const [form, setForm] = useState({
    name: campaign.name,
    daily_limit: campaign.daily_limit,
    sending_window_start: campaign.sending_window?.start ? parseInt(campaign.sending_window.start.split(":")[0]) : 9,
    sending_window_end: campaign.sending_window?.end ? parseInt(campaign.sending_window.end.split(":")[0]) : 17,
    timezone_mode: campaign.timezone_mode,
  });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await update.mutateAsync({
        id: campaign.id,
        data: {
          name: form.name,
          daily_limit: form.daily_limit,
          sending_window: {
            start: `${String(form.sending_window_start).padStart(2, "0")}:00`,
            end: `${String(form.sending_window_end).padStart(2, "0")}:00`,
          },
          timezone_mode: form.timezone_mode,
        },
      });
      toast.success("Campaign settings updated");
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to update settings");
    }
  };

  return (
    <form onSubmit={handleSave} className="mt-4 pt-4 border-t border-white/[0.08] space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Campaign Name</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Daily Limit (Max sends/day)</label>
          <input
            type="number"
            value={form.daily_limit}
            onChange={(e) => setForm({ ...form, daily_limit: parseInt(e.target.value) || 20 })}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Sending Window (Hour)</label>
          <div className="flex items-center gap-1">
            <input
              type="number"
              min={0}
              max={23}
              value={form.sending_window_start}
              onChange={(e) => setForm({ ...form, sending_window_start: parseInt(e.target.value) || 9 })}
              className="w-16 bg-white/[0.03] border border-white/[0.08] rounded-xl px-2 py-1.5 text-xs text-white focus:outline-none text-center"
            />
            <span className="text-slate-500 text-xs">to</span>
            <input
              type="number"
              min={0}
              max={23}
              value={form.sending_window_end}
              onChange={(e) => setForm({ ...form, sending_window_end: parseInt(e.target.value) || 17 })}
              className="w-16 bg-white/[0.03] border border-white/[0.08] rounded-xl px-2 py-1.5 text-xs text-white focus:outline-none text-center"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Timezone Mode</label>
          <select
            value={form.timezone_mode}
            onChange={(e) => setForm({ ...form, timezone_mode: e.target.value as "recipient" | "fixed" })}
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none"
          >
            <option value="recipient">Recipient local timezone</option>
            <option value="fixed">Fixed sender timezone</option>
          </select>
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={update.isPending}
          className="px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-sm"
        >
          {update.isPending ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </form>
  );
}

// ─── Create Campaign Modal ────────────────────────────────────────────────────

function CreateCampaignModal({ onClose }: { onClose: () => void }) {
  const create = useCreateCampaign();
  const { data: icps } = useIcps();

  const [form, setForm] = useState({
    name: "",
    icp_id: "",
    daily_limit: 20,
    sending_window_start: 9,
    sending_window_end: 17,
    timezone_mode: "recipient" as "recipient" | "fixed",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Campaign name is required");
      return;
    }

    try {
      await create.mutateAsync({
        name: form.name,
        icp_id: form.icp_id || undefined,
        daily_limit: form.daily_limit,
        sending_window: {
          start: `${String(form.sending_window_start).padStart(2, "0")}:00`,
          end: `${String(form.sending_window_end).padStart(2, "0")}:00`,
        },
        timezone_mode: form.timezone_mode,
      });
      toast.success("Campaign created");
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to create campaign");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0f0f17] border border-white/10 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white">Create New Outreach Campaign</h3>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Campaign Name</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50"
              placeholder="e.g. US Web Design Agencies Q4"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Target ICP</label>
            <select
              value={form.icp_id}
              onChange={(e) => setForm({ ...form, icp_id: e.target.value })}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="">None / General Audience</option>
              {icps?.map((icp) => (
                <option key={icp.id} value={icp.id}>
                  {icp.name} ({icp.industry || "All industries"})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Daily Sending Limit</label>
              <input
                type="number"
                min={5}
                max={500}
                value={form.daily_limit}
                onChange={(e) => setForm({ ...form, daily_limit: parseInt(e.target.value) || 20 })}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white focus:outline-none"
              />
              <span className="text-[10px] text-slate-500">Start at 20/day during warm-up</span>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Sending Window (Hours)</label>
              <div className="flex items-center gap-1 mt-1">
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={form.sending_window_start}
                  onChange={(e) => setForm({ ...form, sending_window_start: parseInt(e.target.value) || 9 })}
                  className="w-16 bg-white/[0.03] border border-white/[0.08] rounded-xl px-2 py-1.5 text-xs text-white text-center"
                />
                <span className="text-slate-500 text-xs">to</span>
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={form.sending_window_end}
                  onChange={(e) => setForm({ ...form, sending_window_end: parseInt(e.target.value) || 17 })}
                  className="w-16 bg-white/[0.03] border border-white/[0.08] rounded-xl px-2 py-1.5 text-xs text-white text-center"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={create.isPending}
              className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/20 disabled:opacity-60"
            >
              {create.isPending ? "Creating..." : "Create Campaign"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Enroll Leads Modal ───────────────────────────────────────────────────────

function EnrollLeadsModal({
  campaignId,
  icpId,
  onClose,
}: {
  campaignId: string;
  icpId?: string;
  onClose: () => void;
}) {
  const { data: leads, isLoading } = useLeads({
    icp_id: icpId,
    verification_status: "valid",
  });
  const enroll = useEnrollLeads(campaignId);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (!leads) return;
    if (selectedIds.length === leads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(leads.map((l) => l.id));
    }
  };

  const handleEnroll = async () => {
    if (selectedIds.length === 0) return;
    try {
      const res = await enroll.mutateAsync(selectedIds);
      toast.success(`Enrolled ${res.enrolled} verified leads into campaign`);
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to enroll leads");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-[#0f0f17] border border-white/10 rounded-2xl w-full max-w-xl max-h-[85vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-white/[0.08]">
          <div>
            <h3 className="text-base font-bold text-white">Enroll Verified Leads</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Only leads with verification status <span className="text-emerald-400 font-mono">valid</span> are eligible.
            </p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 flex-1 overflow-y-auto space-y-3">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              <Loader2 className="w-4 h-4 animate-spin mx-auto mb-2 text-violet-400" />
              Loading verified leads...
            </div>
          ) : !leads || leads.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No verified leads found. Import leads or run verification first.
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-white/[0.06]">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="text-violet-400 hover:underline font-medium"
                >
                  {selectedIds.length === leads.length ? "Deselect All" : "Select All"}
                </button>
                <span>{selectedIds.length} of {leads.length} selected</span>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {leads.map((lead) => {
                  const isChecked = selectedIds.includes(lead.id);
                  return (
                    <div
                      key={lead.id}
                      onClick={() => toggleSelect(lead.id)}
                      className={clsx(
                        "flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-all text-xs",
                        isChecked
                          ? "bg-violet-600/10 border-violet-500/40 text-white"
                          : "bg-white/[0.02] border-white/[0.04] text-slate-300 hover:bg-white/[0.04]"
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="rounded border-white/20 text-violet-600 focus:ring-0"
                        />
                        <div className="min-w-0">
                          <p className="font-medium truncate">
                            {lead.first_name} {lead.last_name || ""} {lead.company ? `(${lead.company})` : ""}
                          </p>
                          <p className="text-[11px] text-slate-500 truncate">{lead.email}</p>
                        </div>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 shrink-0">
                        valid
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 p-4 border-t border-white/[0.08]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleEnroll}
            disabled={selectedIds.length === 0 || enroll.isPending}
            className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shadow-md shadow-violet-500/20 disabled:opacity-50"
          >
            {enroll.isPending ? "Enrolling..." : `Enroll ${selectedIds.length} Leads`}
          </button>
        </div>
      </div>
    </div>
  );
}
