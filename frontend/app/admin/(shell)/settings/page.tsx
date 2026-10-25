"use client";

import { useState } from "react";
import { useBrandProfile, useUpdateBrandProfile, useDomainHealth } from "@/lib/hooks";
import { toast } from "sonner";
import {
  Loader2,
  Save,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Flame,
  Globe,
  RefreshCw,
  ExternalLink,
  Info,
} from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";

function SectionCard({
  title,
  description,
  badge,
  children,
}: {
  title: string;
  description?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {description && <p className="text-xs text-slate-500 mt-1">{description}</p>}
        </div>
        {badge}
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-400 mb-1.5">{label}</label>
      {children}
    </div>
  );
}

const INPUT_CLS =
  "w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-violet-500/50 transition-all";
const TEXTAREA_CLS = INPUT_CLS + " resize-none";

export default function SettingsPage() {
  const { data: brand, isLoading } = useBrandProfile();
  const update = useUpdateBrandProfile();

  const [form, setForm] = useState({
    product_name: "",
    one_liner: "",
    tone: "",
    value_props: "",
    banned_phrases: "",
    website_url: "",
    physical_address: "",
  });

  const [checkDomain, setCheckDomain] = useState("getyourclientsb2b.com");
  const [activeDomainQuery, setActiveDomainQuery] = useState("getyourclientsb2b.com");
  const { data: domainHealth, isLoading: isCheckingDomain, refetch: refetchDomain } = useDomainHealth(activeDomainQuery);

  const [initialized, setInitialized] = useState(false);
  if (brand && !initialized) {
    setForm({
      product_name: brand.product_name || "",
      one_liner: brand.one_liner || "",
      tone: brand.tone || "",
      value_props: (brand.value_props || []).join("\n"),
      banned_phrases: (brand.banned_phrases || []).join("\n"),
      website_url: brand.website_url || "",
      physical_address: brand.physical_address || "",
    });
    if (brand.website_url) {
      try {
        const url = new URL(brand.website_url);
        setCheckDomain(url.hostname.replace(/^www\./, ""));
        setActiveDomainQuery(url.hostname.replace(/^www\./, ""));
      } catch (e) {
        // use default
      }
    }
    setInitialized(true);
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await update.mutateAsync({
        product_name: form.product_name,
        one_liner: form.one_liner,
        tone: form.tone,
        value_props: form.value_props.split("\n").map((s) => s.trim()).filter(Boolean),
        banned_phrases: form.banned_phrases.split("\n").map((s) => s.trim()).filter(Boolean),
        website_url: form.website_url,
        physical_address: form.physical_address,
      });
      toast.success("Brand profile saved.");
    } catch (err: any) {
      toast.error(err.message || "Failed to save brand profile.");
    }
  };

  const handleDomainCheck = (e: React.FormEvent) => {
    e.preventDefault();
    if (!checkDomain.trim()) return;
    setActiveDomainQuery(checkDomain.trim().toLowerCase());
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-sm p-8">
        <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
        Loading settings...
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Settings & Deliverability</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Configure your brand profile, sending domain authentication, and outreach compliance
        </p>
      </div>

      {/* Sending Domain Health Checklist */}
      <SectionCard
        title="Sending Domain Health & DNS Authentication"
        description="Verify SPF, DKIM, and DMARC records to ensure maximum inbox deliverability and prevent spam flagging."
        badge={
          domainHealth && (
            <span
              className={clsx(
                "text-xs font-mono px-2.5 py-1 rounded-full border capitalize font-semibold flex items-center gap-1.5",
                domainHealth.overall === "pass"
                  ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  : domainHealth.overall === "warn"
                  ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                  : "bg-rose-500/15 text-rose-400 border-rose-500/30"
              )}
            >
              {domainHealth.overall === "pass" ? (
                <CheckCircle2 className="w-3.5 h-3.5" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5" />
              )}
              {domainHealth.overall}
            </span>
          )
        }
      >
        <div className="space-y-4">
          <form onSubmit={handleDomainCheck} className="flex gap-2">
            <div className="relative flex-1">
              <Globe className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                value={checkDomain}
                onChange={(e) => setCheckDomain(e.target.value)}
                placeholder="sendingdomain.com"
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50"
              />
            </div>
            <button
              type="submit"
              disabled={isCheckingDomain}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold shrink-0 transition-all shadow-md shadow-violet-500/20 disabled:opacity-60"
            >
              {isCheckingDomain ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Verifying DNS...</>
              ) : (
                <><RefreshCw className="w-3.5 h-3.5" /> Check Records</>
              )}
            </button>
          </form>

          {domainHealth && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* SPF Check */}
              <DnsRecordCard
                name="SPF Record"
                status={domainHealth.spf.status}
                value={domainHealth.spf.record || "No TXT record"}
                hint={domainHealth.spf.hint}
              />
              {/* DKIM Check */}
              <DnsRecordCard
                name="DKIM Signature"
                status={domainHealth.dkim.status}
                value={domainHealth.dkim.selector ? `Selector: ${domainHealth.dkim.selector}` : "Key not found"}
                hint={domainHealth.dkim.hint}
              />
              {/* DMARC Check */}
              <DnsRecordCard
                name="DMARC Policy"
                status={domainHealth.dmarc.status}
                value={domainHealth.dmarc.record || "Not configured"}
                hint={domainHealth.dmarc.hint}
              />
            </div>
          )}
        </div>
      </SectionCard>

      {/* Warm-Up Guidance Card */}
      <SectionCard
        title="Domain Warm-Up Guidance & Ramp Schedule"
        description="To protect your sender reputation, never send at full volume immediately. Follow this progressive 6-week warm-up ramp."
        badge={
          <span className="flex items-center gap-1 text-xs font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full">
            <Flame className="w-3.5 h-3.5" /> Warm-up Protocol
          </span>
        }
      >
        <div className="space-y-3">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.08] text-slate-500">
                  <th className="pb-2 font-medium">Timeline</th>
                  <th className="pb-2 font-medium">Recommended Daily Volume</th>
                  <th className="pb-2 font-medium">Protocol & Deliverability Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {(domainHealth?.warmup_schedule || [
                  { week: 1, daily_limit: 20, note: "Start conservative. High personalization only." },
                  { week: 2, daily_limit: 40, note: "Monitor bounce rate (<2%) and spam complaints (<0.1%)." },
                  { week: 3, daily_limit: 75, note: "Expand ICP segment gradually." },
                  { week: 4, daily_limit: 125, note: "Full sequence testing with A/B subject lines." },
                  { week: 5, daily_limit: 200, note: "Healthy domain reputation established." },
                  { week: 6, daily_limit: 300, note: "Scale to standard operating volume." },
                ]).map((item) => (
                  <tr key={item.week} className="hover:bg-white/[0.01]">
                    <td className="py-2.5 font-medium text-white">Week {item.week}</td>
                    <td className="py-2.5 font-mono text-violet-400 font-semibold">
                      {item.daily_limit} emails / day
                    </td>
                    <td className="py-2.5 text-slate-400">{item.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-2.5 text-xs text-slate-400">
            <Info className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
            <span>
              <strong>Auto-Pause Safety Thresholds:</strong> The background worker checks campaign health every 15 minutes. Any campaign exceeding a <strong>5.0% bounce rate</strong> or <strong>0.3% complaint rate</strong> is automatically paused to safeguard your domain.
            </span>
          </div>
        </div>
      </SectionCard>

      {/* Brand Profile */}
      <form onSubmit={handleSave}>
        <SectionCard
          title="Brand Profile"
          description="Injected into every AI prompt (email copy, social posts, reply classification) to keep voice consistent."
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Product Name">
                <input
                  id="brand-product-name"
                  type="text"
                  value={form.product_name}
                  onChange={(e) => setForm({ ...form, product_name: e.target.value })}
                  className={INPUT_CLS}
                  placeholder="GetyourclientsB2B"
                />
              </Field>
              <Field label="Website URL">
                <input
                  id="brand-website-url"
                  type="url"
                  value={form.website_url}
                  onChange={(e) => setForm({ ...form, website_url: e.target.value })}
                  className={INPUT_CLS}
                  placeholder="https://getyourclientsb2b.com"
                />
              </Field>
            </div>

            <Field label="One-liner">
              <input
                id="brand-one-liner"
                type="text"
                value={form.one_liner}
                onChange={(e) => setForm({ ...form, one_liner: e.target.value })}
                className={INPUT_CLS}
                placeholder="We help founders get international B2B clients"
              />
            </Field>

            <Field label="Tone">
              <input
                id="brand-tone"
                type="text"
                value={form.tone}
                onChange={(e) => setForm({ ...form, tone: e.target.value })}
                className={INPUT_CLS}
                placeholder="professional, direct, honest — no hype"
              />
            </Field>

            <Field label="Value Props (one per line)">
              <textarea
                id="brand-value-props"
                rows={3}
                value={form.value_props}
                onChange={(e) => setForm({ ...form, value_props: e.target.value })}
                className={TEXTAREA_CLS}
                placeholder="Reach clients in 50+ countries&#10;Official social APIs only&#10;Human in the loop on every send"
              />
            </Field>

            <Field label="Banned Phrases (one per line)">
              <textarea
                id="brand-banned-phrases"
                rows={2}
                value={form.banned_phrases}
                onChange={(e) => setForm({ ...form, banned_phrases: e.target.value })}
                className={TEXTAREA_CLS}
                placeholder="guaranteed ROI&#10;10x your leads"
              />
            </Field>

            <Field label="Physical Address (Legal footer requirement for CAN-SPAM / GDPR)">
              <input
                id="brand-physical-address"
                type="text"
                value={form.physical_address}
                onChange={(e) => setForm({ ...form, physical_address: e.target.value })}
                className={INPUT_CLS}
                placeholder="123 Growth Way, San Francisco, CA 94107"
              />
            </Field>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={update.isPending}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold transition-all shadow-lg shadow-violet-500/20 disabled:opacity-60"
              >
                {update.isPending ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
                ) : (
                  <><Save className="w-4 h-4" /> Save Brand Profile</>
                )}
              </button>
            </div>
          </div>
        </SectionCard>
      </form>

      {/* Suppression List Quick Link */}
      <SectionCard
        title="Suppression List Management"
        description="Addresses and domains permanently blocked from outreach. Checked automatically before every single send."
      >
        <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <div className="text-xs text-slate-400">
            Manage unsubscribes, manual opt-outs, and auto-suppressed complaint addresses in the unified Leads center.
          </div>
          <Link
            href="/admin/leads"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs font-semibold text-white transition-all shrink-0"
          >
            <span>Open Suppression List</span>
            <ExternalLink className="w-3.5 h-3.5 text-violet-400" />
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}

// ─── DNS Record Card ──────────────────────────────────────────────────────────

function DnsRecordCard({
  name,
  status,
  value,
  hint,
}: {
  name: string;
  status: "pass" | "fail" | "warn";
  value: string;
  hint?: string;
}) {
  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-white">{name}</span>
        <span
          className={clsx(
            "text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold flex items-center gap-1",
            status === "pass"
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : status === "warn"
              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
          )}
        >
          {status === "pass" ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
          {status}
        </span>
      </div>
      <p className="text-[11px] font-mono text-slate-300 truncate bg-black/40 p-2 rounded-lg border border-white/[0.04]">
        {value}
      </p>
      {hint && (
        <p className="text-[11px] text-slate-500 leading-tight">
          {hint}
        </p>
      )}
    </div>
  );
}
