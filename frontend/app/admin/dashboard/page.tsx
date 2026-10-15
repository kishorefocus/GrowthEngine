"use client";

import { useAnalyticsOverview } from "@/lib/hooks";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Mail,
  MousePointer,
  RefreshCw,
  TrendingUp,
  Users,
} from "lucide-react";
import { clsx } from "clsx";

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={clsx("bg-white/[0.04] rounded-lg animate-pulse", className)} />
  );
}

// ─── KPI Card ────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string;
  value: string | number;
  subLabel?: string;
  icon: React.ReactNode;
  color: string;
  loading?: boolean;
}

function KpiCard({ label, value, subLabel, icon, color, loading }: KpiCardProps) {
  if (loading) {
    return (
      <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
        <Skeleton className="h-4 w-24 mb-4" />
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-3 w-16" />
      </div>
    );
  }

  return (
    <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:border-white/10 transition-all group">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</span>
        <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center text-xs", color)}>
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-white tabular-nums">{value}</p>
      {subLabel && <p className="text-xs text-slate-500 mt-1">{subLabel}</p>}
    </div>
  );
}

// ─── Channel Chart ────────────────────────────────────────────────────────────

const CHANNEL_COLORS: Record<string, string> = {
  email: "#8b5cf6",
  x: "#22d3ee",
  linkedin: "#3b82f6",
  instagram: "#ec4899",
  facebook: "#6366f1",
  youtube: "#ef4444",
  seo: "#10b981",
  tools: "#f59e0b",
  product_hunt: "#f97316",
  reddit: "#ff4500",
  indiehackers: "#14b8a6",
  direct: "#64748b",
};

interface ChannelData {
  channel: string;
  visits: number;
}

function ChannelChart({ data, loading }: { data: ChannelData[]; loading: boolean }) {
  if (loading) {
    return <Skeleton className="h-56 w-full" />;
  }

  const nonEmpty = data.filter((d) => d.visits > 0);
  const chartData = nonEmpty.length > 0 ? nonEmpty : data.slice(0, 5);

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <XAxis
          dataKey="channel"
          tick={{ fontSize: 10, fill: "#64748b" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#64748b" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#0d0d14",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#e2e8f0",
          }}
          cursor={{ fill: "rgba(255,255,255,0.03)" }}
        />
        <Bar dataKey="visits" radius={[4, 4, 0, 0]}>
          {chartData.map((entry) => (
            <Cell
              key={entry.channel}
              fill={CHANNEL_COLORS[entry.channel] || "#6366f1"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data, isLoading, error, refetch } = useAnalyticsOverview();

  const channelData: ChannelData[] = Object.entries(data?.channels || {}).map(([channel, visits]) => ({
    channel,
    visits: visits as number,
  }));

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Dashboard</h2>
          <p className="text-sm text-slate-500 mt-0.5">Overview of your growth channels</p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-all"
        >
          <RefreshCw className={clsx("w-3.5 h-3.5", isLoading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          Could not load analytics. Is the backend running?
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Visits"
          value={data?.overview.total_visits.toLocaleString() ?? "—"}
          icon={<MousePointer className="w-4 h-4" />}
          color="bg-violet-500/15 text-violet-400"
          loading={isLoading}
        />
        <KpiCard
          label="Signups"
          value={data?.overview.total_signups.toLocaleString() ?? "—"}
          icon={<Users className="w-4 h-4" />}
          color="bg-emerald-500/15 text-emerald-400"
          loading={isLoading}
        />
        <KpiCard
          label="Conversion Rate"
          value={data ? `${data.overview.conversion_rate_pct}%` : "—"}
          icon={<TrendingUp className="w-4 h-4" />}
          color="bg-blue-500/15 text-blue-400"
          loading={isLoading}
        />
        <KpiCard
          label="Emails Sent"
          value={data?.email.sent.toLocaleString() ?? "—"}
          subLabel={data ? `Reply ${data.email.reply_rate_pct}% · Bounce ${data.email.bounce_rate_pct}%` : undefined}
          icon={<Mail className="w-4 h-4" />}
          color="bg-amber-500/15 text-amber-400"
          loading={isLoading}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Channel attribution chart */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Channel Attribution (Visits)</h3>
            <span className="text-xs text-slate-500">UTM source</span>
          </div>
          <ChannelChart data={channelData} loading={isLoading} />
        </div>

        {/* Today's tasks placeholder */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-400" />
            Today's Tasks
          </h3>
          <div className="space-y-2">
            {[
              { label: "Review approval queue", done: false },
              { label: "Check email bounce rate", done: false },
              { label: "Schedule social posts", done: false },
            ].map((task) => (
              <div key={task.label} className="flex items-center gap-2.5 py-2 border-b border-white/[0.04] last:border-0">
                <CheckCircle2 className={clsx("w-4 h-4 shrink-0", task.done ? "text-emerald-400" : "text-slate-700")} />
                <span className={clsx("text-xs", task.done ? "text-slate-500 line-through" : "text-slate-300")}>
                  {task.label}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/10">
            <p className="text-xs text-emerald-400 font-medium">Approval queue</p>
            <p className="text-xs text-slate-500 mt-1">No items pending approval.</p>
          </div>
        </div>
      </div>

      {/* Top Posts + Top SEO Pages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top posts */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
          <h3 className="text-sm font-semibold text-white mb-3">Top Published Posts</h3>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : data?.top_posts.length === 0 ? (
            <div className="text-center py-8 text-slate-600 text-sm">
              No published posts yet. Build campaigns in Prompt 3.
            </div>
          ) : (
            <div className="space-y-2">
              {data?.top_posts.map((post) => (
                <div key={post.id} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="text-xs font-mono bg-white/[0.06] text-slate-400 px-2 py-0.5 rounded capitalize shrink-0">
                    {post.platform}
                  </span>
                  <p className="text-xs text-slate-400 truncate">{post.body_preview}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top SEO pages */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
          <h3 className="text-sm font-semibold text-white mb-3">Top SEO Pages</h3>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : data?.top_seo_pages.length === 0 ? (
            <div className="text-center py-8 text-slate-600 text-sm">
              No SEO pages yet. Build them in Prompt 4.
            </div>
          ) : (
            <div className="space-y-2">
              {data?.top_seo_pages.map((page) => (
                <div key={page.id} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-300 truncate">{page.title || page.slug}</p>
                    <p className="text-[11px] text-slate-600 truncate">/{page.slug}</p>
                  </div>
                  {page.quality_score != null && (
                    <span className="text-xs font-mono text-emerald-400 shrink-0 ml-2">{page.quality_score}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
