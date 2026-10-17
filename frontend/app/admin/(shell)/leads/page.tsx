"use client";

import { useState } from "react";
import {
  useCreateICP,
  useCreateLead,
  useDeleteICP,
  useDeleteLead,
  useEnrollLeads,
  useICPs,
  useImportCsv,
  useImportGlobalReach,
  useLeads,
  useSuppressionList,
  useAddSuppression,
  useRemoveSuppression,
  useVerifyLead,
  useCampaigns,
} from "@/lib/hooks";
import { ICP, Lead } from "@/lib/api-client";
import { toast } from "sonner";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Download,
  Filter,
  Globe,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Upload,
  UserCheck,
  UserPlus,
  Users,
  X,
  FileSpreadsheet,
  Layers,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";

export default function LeadsPage() {
  const [activeTab, setActiveTab] = useState<"leads" | "icps" | "suppression">("leads");

  // Filters
  const [selectedIcp, setSelectedIcp] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [selectedVerification, setSelectedVerification] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  // Queries
  const { data: icps, isLoading: loadingIcps } = useICPs();
  const { data: leads, isLoading: loadingLeads, refetch: refetchLeads } = useLeads({
    icp_id: selectedIcp || undefined,
    status: selectedStatus || undefined,
    verification_status: selectedVerification || undefined,
  });
  const { data: campaigns } = useCampaigns();

  // Mutations
  const verifyLead = useVerifyLead();
  const deleteLead = useDeleteLead();
  const enrollLeads = useEnrollLeads();

  // Selection
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);

  // Modals
  const [showCreateLead, setShowCreateLead] = useState(false);
  const [showImportCsv, setShowImportCsv] = useState(false);
  const [showImportGr, setShowImportGr] = useState(false);
  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState("");

  const filteredLeads = (leads || []).filter((l) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      l.email.toLowerCase().includes(q) ||
      (l.first_name && l.first_name.toLowerCase().includes(q)) ||
      (l.company && l.company.toLowerCase().includes(q))
    );
  });

  const toggleSelectAll = () => {
    if (selectedLeadIds.length === filteredLeads.length) {
      setSelectedLeadIds([]);
    } else {
      setSelectedLeadIds(filteredLeads.map((l) => l.id));
    }
  };

  const toggleSelectOne = (id: string) => {
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleVerifyOne = async (id: string) => {
    try {
      const res = await verifyLead.mutateAsync(id);
      toast.success(`Verification: ${res.verification_status.toUpperCase()}`);
    } catch (err: any) {
      toast.error(err.message || "Verification failed");
    }
  };

  const handleBulkVerify = async () => {
    if (!selectedLeadIds.length) return;
    toast.info(`Verifying ${selectedLeadIds.length} leads...`);
    let count = 0;
    for (const id of selectedLeadIds) {
      try {
        await verifyLead.mutateAsync(id);
        count++;
      } catch {}
    }
    toast.success(`Verified ${count} leads.`);
  };

  const handleDeleteOne = async (id: string) => {
    if (!confirm("Erase lead? Under GDPR, lead data will be removed while email is kept in suppression.")) return;
    try {
      await deleteLead.mutateAsync(id);
      toast.success("Lead erased and email suppressed.");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete lead");
    }
  };

  const handleEnroll = async () => {
    if (!selectedCampaignId) {
      toast.error("Please select a campaign.");
      return;
    }
    try {
      const res = await enrollLeads.mutateAsync({
        campaign_id: selectedCampaignId,
        lead_ids: selectedLeadIds,
      });
      toast.success(`Enrolled ${res.enrolled} verified leads into campaign!`);
      if (res.skipped?.length) {
        toast.info(`Skipped ${res.skipped.length} leads (not valid or already enrolled).`);
      }
      setShowEnrollModal(false);
      setSelectedLeadIds([]);
    } catch (err: any) {
      toast.error(err.message || "Enrollment failed.");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white tracking-tight">Lead Engine</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Dogfooding Ready
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Build ICPs, import leads, verify deliverability, and enforce zero-spam suppression.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1.5 p-1 bg-white/[0.03] border border-white/[0.08] rounded-xl self-start sm:self-auto">
          <button
            onClick={() => setActiveTab("leads")}
            className={clsx(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2",
              activeTab === "leads"
                ? "bg-violet-600 text-white shadow-md shadow-violet-500/20"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <Users className="w-3.5 h-3.5" />
            Leads {leads ? `(${leads.length})` : ""}
          </button>
          <button
            onClick={() => setActiveTab("icps")}
            className={clsx(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2",
              activeTab === "icps"
                ? "bg-violet-600 text-white shadow-md shadow-violet-500/20"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <Layers className="w-3.5 h-3.5" />
            ICPs {icps ? `(${icps.length})` : ""}
          </button>
          <button
            onClick={() => setActiveTab("suppression")}
            className={clsx(
              "px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2",
              activeTab === "suppression"
                ? "bg-violet-600 text-white shadow-md shadow-violet-500/20"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            Suppression
          </button>
        </div>
      </div>

      {activeTab === "leads" && (
        <div className="space-y-4">
          {/* Action Bar */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
            {/* Search and Filters */}
            <div className="flex flex-wrap items-center gap-2.5 flex-1">
              <div className="relative min-w-[220px] flex-1 max-w-xs">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search leads by name, email, company..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-500/50"
                />
              </div>

              {/* ICP filter */}
              <select
                value={selectedIcp}
                onChange={(e) => setSelectedIcp(e.target.value)}
                className="bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-violet-500/50"
              >
                <option value="" className="bg-[#12121e]">All ICPs</option>
                {(icps || []).map((i) => (
                  <option key={i.id} value={i.id} className="bg-[#12121e]">
                    {i.name}
                  </option>
                ))}
              </select>

              {/* Verification filter */}
              <select
                value={selectedVerification}
                onChange={(e) => setSelectedVerification(e.target.value)}
                className="bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-violet-500/50"
              >
                <option value="" className="bg-[#12121e]">All Verification</option>
                <option value="valid" className="bg-[#12121e]">Valid Only</option>
                <option value="risky" className="bg-[#12121e]">Risky</option>
                <option value="invalid" className="bg-[#12121e]">Invalid</option>
                <option value="pending" className="bg-[#12121e]">Pending</option>
              </select>

              {/* Status filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-violet-500/50"
              >
                <option value="" className="bg-[#12121e]">All Statuses</option>
                <option value="new" className="bg-[#12121e]">New</option>
                <option value="queued" className="bg-[#12121e]">Queued</option>
                <option value="contacted" className="bg-[#12121e]">Contacted</option>
                <option value="replied" className="bg-[#12121e]">Replied</option>
                <option value="signed_up" className="bg-[#12121e]">Signed Up</option>
                <option value="unsubscribed" className="bg-[#12121e]">Unsubscribed</option>
              </select>

              {(selectedIcp || selectedVerification || selectedStatus || searchQuery) && (
                <button
                  onClick={() => {
                    setSelectedIcp("");
                    setSelectedVerification("");
                    setSelectedStatus("");
                    setSearchQuery("");
                  }}
                  className="text-xs text-violet-400 hover:text-violet-300 px-2 py-1"
                >
                  Reset
                </button>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowImportGr(true)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-violet-500/15 border border-violet-500/30 text-violet-300 hover:bg-violet-500/25 text-xs font-semibold transition-all shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                GlobalReach API
              </button>
              <button
                onClick={() => setShowImportCsv(true)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-slate-300 hover:bg-white/[0.08] text-xs font-semibold transition-all"
              >
                <Upload className="w-3.5 h-3.5 text-slate-400" />
                CSV Import
              </button>
              <button
                onClick={() => setShowCreateLead(true)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-lg shadow-violet-500/20"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Lead
              </button>
            </div>
          </div>

          {/* Bulk Action Bar (when items selected) */}
          {selectedLeadIds.length > 0 && (
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-violet-600/15 border border-violet-500/30 text-white text-xs animate-in fade-in">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-violet-300">
                  {selectedLeadIds.length} lead{selectedLeadIds.length > 1 ? "s" : ""} selected
                </span>
                <span className="text-slate-500">|</span>
                <button
                  onClick={handleBulkVerify}
                  disabled={verifyLead.isPending}
                  className="hover:text-emerald-400 flex items-center gap-1.5 transition-colors"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Verify Deliverability
                </button>
                <button
                  onClick={() => setShowEnrollModal(true)}
                  className="hover:text-indigo-400 flex items-center gap-1.5 transition-colors"
                >
                  <Mail className="w-3.5 h-3.5 text-indigo-400" />
                  Enroll in Campaign
                </button>
              </div>
              <button
                onClick={() => setSelectedLeadIds([])}
                className="text-slate-400 hover:text-slate-200"
              >
                Deselect
              </button>
            </div>
          )}

          {/* Leads Table */}
          <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-white/[0.01] text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-3.5 px-4 w-10">
                      <input
                        type="checkbox"
                        checked={filteredLeads.length > 0 && selectedLeadIds.length === filteredLeads.length}
                        onChange={toggleSelectAll}
                        className="rounded border-white/20 bg-white/5 text-violet-600 focus:ring-0 cursor-pointer"
                      />
                    </th>
                    <th className="py-3.5 px-4">Contact</th>
                    <th className="py-3.5 px-4">Company & Title</th>
                    <th className="py-3.5 px-4">Country</th>
                    <th className="py-3.5 px-4">Verification</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] text-xs">
                  {loadingLeads ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-500">
                        <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-violet-400" />
                        Loading leads...
                      </td>
                    </tr>
                  ) : filteredLeads.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-500">
                        No leads found matching your criteria. Import leads using GlobalReach API or CSV.
                      </td>
                    </tr>
                  ) : (
                    filteredLeads.map((lead) => (
                      <tr
                        key={lead.id}
                        className="hover:bg-white/[0.02] transition-colors group"
                      >
                        <td className="py-3.5 px-4">
                          <input
                            type="checkbox"
                            checked={selectedLeadIds.includes(lead.id)}
                            onChange={() => toggleSelectOne(lead.id)}
                            className="rounded border-white/20 bg-white/5 text-violet-600 focus:ring-0 cursor-pointer"
                          />
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="font-medium text-white">
                            {lead.first_name || lead.last_name
                              ? `${lead.first_name || ""} ${lead.last_name || ""}`.trim()
                              : "—"}
                          </div>
                          <div className="text-[11px] font-mono text-slate-400">{lead.email}</div>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="text-slate-300 font-medium">{lead.company || "—"}</div>
                          <div className="text-[11px] text-slate-500">{lead.title || "—"}</div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-400">
                          {lead.country || "—"}
                        </td>
                        <td className="py-3.5 px-4">
                          <VerificationBadge status={lead.verification_status} />
                        </td>
                        <td className="py-3.5 px-4">
                          <StatusBadge status={lead.status} />
                        </td>
                        <td className="py-3.5 px-4 text-right space-x-1">
                          <button
                            title="Verify deliverability"
                            onClick={() => handleVerifyOne(lead.id)}
                            disabled={verifyLead.isPending}
                            className="p-1.5 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-emerald-400 transition-colors"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                          </button>
                          <button
                            title="GDPR Erasure"
                            onClick={() => handleDeleteOne(lead.id)}
                            disabled={deleteLead.isPending}
                            className="p-1.5 rounded-lg hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ICP Management Tab */}
      {activeTab === "icps" && <ICPsTab />}

      {/* Suppression Management Tab */}
      {activeTab === "suppression" && <SuppressionTab />}

      {/* Modal: Create Single Lead */}
      {showCreateLead && (
        <CreateLeadModal
          icps={icps || []}
          onClose={() => setShowCreateLead(false)}
        />
      )}

      {/* Modal: GlobalReach Import */}
      {showImportGr && (
        <GlobalReachImportModal
          icps={icps || []}
          onClose={() => setShowImportGr(false)}
        />
      )}

      {/* Modal: CSV Import */}
      {showImportCsv && (
        <CsvImportModal
          icps={icps || []}
          onClose={() => setShowImportCsv(false)}
        />
      )}

      {/* Modal: Enroll in Campaign */}
      {showEnrollModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#12121e] border border-white/10 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Enroll in Campaign</h3>
              <button onClick={() => setShowEnrollModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Only verified leads with status <span className="text-emerald-400 font-mono">valid</span> will be enrolled.
            </p>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Select Campaign</label>
              <select
                value={selectedCampaignId}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500"
              >
                <option value="" className="bg-[#12121e]">Choose a campaign...</option>
                {(campaigns || []).map((c) => (
                  <option key={c.id} value={c.id} className="bg-[#12121e]">
                    {c.name} ({c.status})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowEnrollModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleEnroll}
                disabled={enrollLeads.isPending}
                className="px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/25"
              >
                {enrollLeads.isPending ? "Enrolling..." : "Enroll Leads"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Verification & Status Badges ─────────────────────────────────────────────

function VerificationBadge({ status }: { status: string }) {
  switch (status) {
    case "valid":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" />
          Valid
        </span>
      );
    case "risky":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3" />
          Risky
        </span>
      );
    case "invalid":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <X className="w-3 h-3" />
          Invalid
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
          Pending
        </span>
      );
  }
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    new: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    queued: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
    contacted: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    replied: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    signed_up: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    bounced: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    unsubscribed: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium uppercase border",
        styles[status] || styles.new
      )}
    >
      {status}
    </span>
  );
}

// ─── Modal: Create Single Lead ────────────────────────────────────────────────

function CreateLeadModal({ icps, onClose }: { icps: ICP[]; onClose: () => void }) {
  const createLead = useCreateLead();
  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    company: "",
    title: "",
    website: "",
    country: "",
    industry: "",
    icp_id: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createLead.mutateAsync(form);
      toast.success("Lead created.");
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to create lead.");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#12121e] border border-white/10 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white">Create Lead</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Email *</label>
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                placeholder="founder@company.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Company</label>
              <input
                type="text"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                placeholder="Acme Web Studio"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">First Name</label>
              <input
                type="text"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Last Name</label>
              <input
                type="text"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Title</label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                placeholder="CEO & Co-founder"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Country</label>
              <input
                type="text"
                value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                placeholder="US"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Assign ICP</label>
            <select
              value={form.icp_id}
              onChange={(e) => setForm({ ...form, icp_id: e.target.value })}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
            >
              <option value="" className="bg-[#12121e]">None</option>
              {icps.map((i) => (
                <option key={i.id} value={i.id} className="bg-[#12121e]">{i.name}</option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createLead.isPending}
              className="px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/25"
            >
              {createLead.isPending ? "Creating..." : "Save Lead"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Modal: GlobalReach API Dogfooding Import ─────────────────────────────────

function GlobalReachImportModal({ icps, onClose }: { icps: ICP[]; onClose: () => void }) {
  const importGr = useImportGlobalReach();
  const [icpId, setIcpId] = useState(icps[0]?.id || "");
  const [maxResults, setMaxResults] = useState(50);

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!icpId) {
      toast.error("Please select an ICP to import leads for.");
      return;
    }
    try {
      const res = await importGr.mutateAsync({ icp_id: icpId, max_results: maxResults });
      toast.success(`Imported ${res.imported} new leads from GlobalReach! (Skipped ${res.duplicates_skipped} duplicates)`);
      onClose();
    } catch (err: any) {
      toast.error(err.message || "GlobalReach API import failed. Ensure GLOBALREACH_API_KEY is configured.");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#12121e] border border-white/10 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-violet-500/20 border border-violet-500/30 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Dogfooding Lead Pull</h3>
              <p className="text-[11px] text-slate-400">Import via GlobalReach official API</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed bg-white/[0.02] p-3 rounded-xl border border-white/[0.04]">
          Pulls targeted B2B agency leads matching your chosen Ideal Customer Profile from the GlobalReach lead database.
        </p>

        <form onSubmit={handleImport} className="space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Target ICP *</label>
            <select
              required
              value={icpId}
              onChange={(e) => setIcpId(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white"
            >
              {icps.map((i) => (
                <option key={i.id} value={i.id} className="bg-[#12121e]">{i.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Max Leads to Pull</label>
            <input
              type="number"
              min={5}
              max={250}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={importGr.isPending}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/25"
            >
              {importGr.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Pull Leads
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Modal: CSV Import ────────────────────────────────────────────────────────

function CsvImportModal({ icps, onClose }: { icps: ICP[]; onClose: () => void }) {
  const importCsv = useImportCsv();
  const [csvText, setCsvText] = useState("");
  const [icpId, setIcpId] = useState("");
  const [mapping, setMapping] = useState({
    email: "email",
    first_name: "first_name",
    last_name: "last_name",
    company: "company",
    title: "title",
    website: "website",
    country: "country",
  });

  const handleParseAndUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvText.trim()) {
      toast.error("Please paste CSV data.");
      return;
    }

    const lines = csvText.trim().split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length < 2) {
      toast.error("CSV must have a header row and at least one data row.");
      return;
    }

    const headers = lines[0].split(",").map((h) => h.trim().replace(/^["']|["']$/g, ""));
    const rows: Record<string, string>[] = [];

    for (let i = 1; i < lines.length; i++) {
      const parts = lines[i].split(",").map((p) => p.trim().replace(/^["']|["']$/g, ""));
      const row: Record<string, string> = {};
      headers.forEach((h, idx) => {
        row[h] = parts[idx] || "";
      });
      rows.push(row);
    }

    try {
      const res = await importCsv.mutateAsync({
        icp_id: icpId || undefined,
        column_mapping: mapping,
        rows,
      });
      toast.success(`Imported ${res.imported} leads! (Duplicates skipped: ${res.duplicates_skipped})`);
      onClose();
    } catch (err: any) {
      toast.error(err.message || "CSV import failed.");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#12121e] border border-white/10 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-violet-400" />
            CSV Lead Import
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleParseAndUpload} className="space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Assign to ICP (Optional)</label>
            <select
              value={icpId}
              onChange={(e) => setIcpId(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
            >
              <option value="" className="bg-[#12121e]">None</option>
              {icps.map((i) => (
                <option key={i.id} value={i.id} className="bg-[#12121e]">{i.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Paste CSV Content (with header row)
            </label>
            <textarea
              required
              rows={5}
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              placeholder="email,first_name,company,title,country&#10;sarah@designagency.com,Sarah,DesignCraft,Owner,US&#10;mark@webflowpros.io,Mark,FlowPros,CEO,UK"
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl p-3 text-xs text-white font-mono"
            />
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] space-y-2">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Column Mapping</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500">Email column:</span>
                <input
                  type="text"
                  value={mapping.email}
                  onChange={(e) => setMapping({ ...mapping, email: e.target.value })}
                  className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-2 py-1 text-xs text-white mt-0.5"
                />
              </div>
              <div>
                <span className="text-slate-500">Company column:</span>
                <input
                  type="text"
                  value={mapping.company}
                  onChange={(e) => setMapping({ ...mapping, company: e.target.value })}
                  className="w-full bg-white/[0.04] border border-white/10 rounded-lg px-2 py-1 text-xs text-white mt-0.5"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={importCsv.isPending}
              className="px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/25"
            >
              {importCsv.isPending ? "Importing..." : "Process Import"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── ICPs Tab Component ───────────────────────────────────────────────────────

function ICPsTab() {
  const { data: icps, isLoading } = useICPs();
  const createIcp = useCreateICP();
  const deleteIcp = useDeleteICP();
  const [showAddModal, setShowAddModal] = useState(false);
  const [form, setForm] = useState({
    name: "",
    industry: "",
    geography: "",
    company_size: "",
    titles: "",
    keywords: "",
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createIcp.mutateAsync({
        name: form.name,
        industry: form.industry,
        geography: form.geography,
        company_size: form.company_size,
        titles: form.titles.split(",").map((s) => s.trim()).filter(Boolean),
        keywords: form.keywords.split(",").map((s) => s.trim()).filter(Boolean),
      });
      toast.success("ICP created.");
      setShowAddModal(false);
      setForm({ name: "", industry: "", geography: "", company_size: "", titles: "", keywords: "" });
    } catch (err: any) {
      toast.error(err.message || "Failed to create ICP.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this ICP?")) return;
    try {
      await deleteIcp.mutateAsync(id);
      toast.success("ICP deleted.");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete ICP.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">
          Define Ideal Customer Profiles to pull targeted leads via GlobalReach and organize outreach campaigns.
        </p>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/20"
        >
          <Plus className="w-3.5 h-3.5" />
          Create ICP
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-full py-12 text-center text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-violet-400" />
            Loading ICPs...
          </div>
        ) : (icps || []).length === 0 ? (
          <div className="col-span-full py-12 text-center text-slate-500 bg-white/[0.02] border border-white/[0.06] rounded-2xl">
            No Ideal Customer Profiles defined yet. Click "Create ICP" to add your target audience.
          </div>
        ) : (
          (icps || []).map((icp) => (
            <div
              key={icp.id}
              className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-white/10 transition-all flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-white text-sm">{icp.name}</h4>
                  <button
                    onClick={() => handleDelete(icp.id)}
                    className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="space-y-1.5 text-xs text-slate-400">
                  {icp.industry && <div><span className="text-slate-600">Industry:</span> {icp.industry}</div>}
                  {icp.geography && <div><span className="text-slate-600">Geo:</span> {icp.geography}</div>}
                  {icp.company_size && <div><span className="text-slate-600">Size:</span> {icp.company_size}</div>}
                </div>
              </div>

              {icp.titles && icp.titles.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-3 border-t border-white/[0.04]">
                  {icp.titles.map((t, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] bg-white/[0.04] text-slate-300">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#12121e] border border-white/10 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">New ICP Profile</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Profile Name *</label>
                <input
                  required
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. US Web Design Agencies 1-10"
                  className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Industry</label>
                  <input
                    type="text"
                    value={form.industry}
                    onChange={(e) => setForm({ ...form, industry: e.target.value })}
                    placeholder="Web Design, Marketing"
                    className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Geography</label>
                  <input
                    type="text"
                    value={form.geography}
                    onChange={(e) => setForm({ ...form, geography: e.target.value })}
                    placeholder="US, UK, CA"
                    className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Company Size</label>
                <input
                  type="text"
                  value={form.company_size}
                  onChange={(e) => setForm({ ...form, company_size: e.target.value })}
                  placeholder="1-10 employees"
                  className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Target Titles (comma separated)</label>
                <input
                  type="text"
                  value={form.titles}
                  onChange={(e) => setForm({ ...form, titles: e.target.value })}
                  placeholder="Founder, Owner, Creative Director"
                  className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createIcp.isPending}
                  className="px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all shadow-md shadow-violet-500/25"
                >
                  {createIcp.isPending ? "Saving..." : "Save Profile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Suppression Tab Component ────────────────────────────────────────────────

function SuppressionTab() {
  const [search, setSearch] = useState("");
  const { data: suppression, isLoading } = useSuppressionList(search);
  const addSup = useAddSuppression();
  const removeSup = useRemoveSuppression();

  const [newEmail, setNewEmail] = useState("");
  const [reason, setReason] = useState("");

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail.trim()) return;
    try {
      await addSup.mutateAsync({ email: newEmail.trim().toLowerCase(), reason: reason.trim() || "manual_admin" });
      toast.success("Added to suppression list.");
      setNewEmail("");
      setReason("");
    } catch (err: any) {
      toast.error(err.message || "Failed to suppress email.");
    }
  };

  const handleRemove = async (id: string) => {
    if (!confirm("Remove from suppression list? An audit log entry will be created.")) return;
    try {
      await removeSup.mutateAsync(id);
      toast.success("Removed from suppression list.");
    } catch (err: any) {
      toast.error(err.message || "Failed to remove.");
    }
  };

  return (
    <div className="space-y-4">
      {/* Quick Add */}
      <form onSubmit={handleAdd} className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px]">
          <input
            required
            type="text"
            placeholder="Email or domain to suppress (e.g. competitor.com or user@xyz.com)"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white"
          />
        </div>
        <div className="w-48">
          <input
            type="text"
            placeholder="Reason (e.g. competitor, opt_out)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white"
          />
        </div>
        <button
          type="submit"
          disabled={addSup.isPending}
          className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-all shadow-md shadow-rose-500/20"
        >
          {addSup.isPending ? "Adding..." : "Suppress"}
        </button>
      </form>

      {/* Suppression Table */}
      <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] overflow-hidden">
        <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
          <div className="relative w-72">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search suppression records..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white"
            />
          </div>
          <span className="text-xs text-slate-500">
            Enforced before every single outbound email send.
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.06] text-[11px] font-semibold text-slate-400 uppercase">
                <th className="py-3 px-4">Email or Domain</th>
                <th className="py-3 px-4">Reason</th>
                <th className="py-3 px-4">Added Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {isLoading ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">Loading suppression list...</td>
                </tr>
              ) : (suppression || []).length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">No suppression records found.</td>
                </tr>
              ) : (
                (suppression || []).map((s) => (
                  <tr key={s.id} className="hover:bg-white/[0.02]">
                    <td className="py-3 px-4 font-mono font-medium text-rose-300">{s.email_or_domain}</td>
                    <td className="py-3 px-4 text-slate-400">{s.reason || "unspecified"}</td>
                    <td className="py-3 px-4 text-slate-500">{new Date(s.added_at).toLocaleDateString()}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleRemove(s.id)}
                        disabled={removeSup.isPending}
                        className="text-slate-500 hover:text-white px-2 py-1 rounded"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
