"use client";

import { useState } from "react";
import { useBrandProfile, useUpdateBrandProfile } from "@/lib/hooks";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";
import { clsx } from "clsx";

function SectionCard({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
      <div className="mb-5">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        {description && <p className="text-xs text-slate-500 mt-1">{description}</p>}
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

const INPUT_CLS = "w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-violet-500/50 transition-all";
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

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-sm">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading settings...
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Settings</h2>
        <p className="text-sm text-slate-500 mt-0.5">Configure your brand profile and team</p>
      </div>

      {/* Brand Profile */}
      <form onSubmit={handleSave}>
        <SectionCard
          title="Brand Profile"
          description="This context is injected into every AI prompt to keep tone and messaging consistent."
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
                  placeholder="GlobalReach"
                />
              </Field>
              <Field label="Website URL">
                <input
                  id="brand-website-url"
                  type="url"
                  value={form.website_url}
                  onChange={(e) => setForm({ ...form, website_url: e.target.value })}
                  className={INPUT_CLS}
                  placeholder="https://www.getyourclientsb2b.com"
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

            <Field label="Physical Address (required in email footer)">
              <input
                id="brand-physical-address"
                type="text"
                value={form.physical_address}
                onChange={(e) => setForm({ ...form, physical_address: e.target.value })}
                className={INPUT_CLS}
                placeholder="123 Main St, City, Country"
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

      {/* Suppression List */}
      <SectionCard
        title="Suppression List"
        description="Emails and domains that will never receive outreach. Checked before every send."
      >
        <div className="p-4 rounded-xl bg-amber-500/[0.06] border border-amber-500/10 text-center">
          <p className="text-xs text-slate-500">
            Suppression list management is built in <span className="text-amber-400">Prompt 2</span>.
          </p>
          <p className="text-xs text-slate-600 mt-1">
            The suppression_list table is live in the database. Import/export will be added next.
          </p>
        </div>
      </SectionCard>

      {/* Team Users */}
      <SectionCard
        title="Team Users"
        description="Invite editors and manage roles. Only the owner can do this."
      >
        <div className="p-4 rounded-xl bg-blue-500/[0.06] border border-blue-500/10 text-center">
          <p className="text-xs text-slate-500">
            Team invite flow is built in <span className="text-blue-400">Prompt 2</span>.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}
