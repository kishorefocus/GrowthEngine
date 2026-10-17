"use client";

import {
  useAnalyticsOverview,
  useCampaigns,
  usePosts,
  useSEOPages,
  useToolsOverview,
  useLaunchTasks,
} from "@/lib/hooks";
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
  AlertTriangle,
  Send,
  Eye,
  MessageSquare,
  XCircle,
  ExternalLink,
  CheckSquare,
  Share2,
  Rocket,
  Wrench,
  Search,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";

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
  const { data: campaigns } = useCampaigns();
  const { data: pendingPosts } = usePosts({ status: "pending_approval" });
  const { data: toolsOverview } = useToolsOverview();
  const { data: launchTasks } = useLaunchTasks();
  const { data: publishedSeoPages } = useSEOPages({ status: "published" });

  const pendingCount = pendingPosts?.length || 0;

  const totalLaunch = launchTasks?.length || 0;
  const completedLaunch = launchTasks?.filter((t) => t.status === "done").length || 0;
  const launchProgressPct = totalLaunch > 0 ? Math.round((completedLaunch / totalLaunch) * 100) : 0;

  const channelData: ChannelData[] = Object.entries(data?.channels || {}).map(([channel, visits]) => ({
    channel,
    visits: visits as number,
  }));

  // Detect campaign health alerts
  const pausedCampaigns = campaigns?.filter((c) => c.status === "paused") || [];

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Dashboard</h2>
          <p className="text-sm text-slate-500 mt-0.5">Overview of your growth engine and outreach</p>
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

      {/* Items Awaiting Approval Banner */}
      {pendingCount > 0 && (
        <div className="p-4 rounded-xl bg-violet-500/10 border border-violet-500/25 text-violet-200 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <CheckSquare className="w-4 h-4 text-violet-400 shrink-0" />
            <div>
              <p className="font-semibold text-white">Items Awaiting Approval</p>
              <p className="mt-0.5 text-violet-200/80">
                {pendingCount} social post {pendingCount === 1 ? "draft is" : "drafts are"} queued for your human review before publishing.
              </p>
            </div>
          </div>
          <Link
            href="/admin/calendar"
            className="flex items-center gap-1 font-semibold text-white bg-violet-600 px-3 py-1.5 rounded-lg hover:bg-violet-500 transition-all shrink-0"
          >
            Review Approval Queue <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Campaign Health Alerts */}
      {pausedCampaigns.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 flex items-start justify-between gap-3 text-xs">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <div>
              <p className="font-semibold text-white">Campaign Safety Alert</p>
              <p className="mt-0.5 text-amber-200/80">
                {pausedCampaigns.length === 1
                  ? `Campaign "${pausedCampaigns[0].name}" is paused. Auto-paused if bounce rate > 5% or complaint rate > 0.3%.`
                  : `${pausedCampaigns.length} campaigns are currently paused.`}
              </p>
            </div>
          </div>
          <Link
            href="/admin/campaigns"
            className="flex items-center gap-1 font-semibold text-white bg-amber-500/20 px-3 py-1.5 rounded-lg hover:bg-amber-500/30 transition-all shrink-0"
          >
            Review Campaigns <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          Could not load analytics. Is the backend running?
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
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
          label="Awaiting Approval"
          value={pendingCount}
          subLabel="Social review queue"
          icon={<CheckSquare className="w-4 h-4" />}
          color="bg-purple-500/15 text-purple-400"
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

      {/* Outreach Health & Channel Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Channel attribution chart */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Channel Attribution (Visits)</h3>
              <span className="text-xs text-slate-500">UTM source attribution</span>
            </div>
            <ChannelChart data={channelData} loading={isLoading} />
          </div>

          {/* Channel Breakdown Rows (Social, SEO, Free Tools, Launch) */}
          <div className="mt-4 pt-3 border-t border-white/[0.04] flex flex-wrap items-center gap-3.5 text-xs">
            <span className="text-slate-500 text-[11px] font-medium">Attribution:</span>
            {[
              { id: "x", label: "X" },
              { id: "linkedin", label: "LinkedIn" },
              { id: "instagram", label: "Instagram" },
              { id: "facebook", label: "Facebook" },
              { id: "youtube", label: "YouTube" },
              { id: "seo", label: "SEO" },
              { id: "tools", label: "Tools" },
              { id: "product_hunt", label: "PH" },
              { id: "reddit", label: "Reddit" },
            ].map((ch) => {
              const visits = data?.channels?.[ch.id] || 0;
              return (
                <div key={ch.id} className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: CHANNEL_COLORS[ch.id] || "#64748b" }}
                  />
                  <span className="text-slate-400">{ch.label}:</span>
                  <span className="font-mono text-white font-medium">{visits}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Email Outreach Performance summary */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-violet-400" />
                Email Deliverability
              </h3>
              <Link href="/admin/campaigns" className="text-xs text-violet-400 hover:underline">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Total Sent</span>
                <span className="font-mono text-white font-semibold">
                  {data?.email.sent.toLocaleString() ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Total Scheduled</span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {data?.email.total_scheduled.toLocaleString() ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Reply Rate</span>
                <span className="font-mono text-white font-semibold">
                  {data?.email.reply_rate_pct ?? 0}%
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Bounce Rate</span>
                <span className={clsx(
                  "font-mono font-semibold",
                  (data?.email.bounce_rate_pct ?? 0) > 5 ? "text-rose-400" : "text-slate-300"
                )}>
                  {data?.email.bounce_rate_pct ?? 0}%
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/[0.04]">
            <Link
              href="/admin/inbox"
              className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-all"
            >
              <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
              Open Prospect Inbox
            </Link>
          </div>
        </div>
      </div>

      {/* Free Tools + Launch Progress Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Free Lead-Magnet Tools Card */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Wrench className="w-4 h-4 text-cyan-400" />
                Free Lead-Magnet Tools
              </h3>
              <span className="text-xs text-cyan-400 font-mono">
                {toolsOverview?.conversion_rate_pct ?? 0}% conversion
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-4 text-center">
              <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                <div className="text-[10px] text-slate-400">Total Tool Runs</div>
                <div className="text-lg font-bold text-white mt-0.5">
                  {toolsOverview?.total_runs ?? 0}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                <div className="text-[10px] text-emerald-400">Emails Captured</div>
                <div className="text-lg font-bold text-emerald-400 mt-0.5">
                  {toolsOverview?.emails_captured ?? 0}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                <div className="text-[10px] text-slate-400">Daily IP Limit</div>
                <div className="text-lg font-bold text-slate-300 mt-0.5">5 / day</div>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-white/[0.04] flex items-center justify-between text-xs">
            <Link
              href="/tools/subject-line-grader"
              target="_blank"
              className="text-slate-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
            >
              Subject Grader <ExternalLink className="w-3 h-3" />
            </Link>
            <Link
              href="/tools/email-verifier"
              target="_blank"
              className="text-slate-400 hover:text-teal-300 flex items-center gap-1 transition-colors"
            >
              Email Verifier <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Product Launch Hub Progress Card */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Rocket className="w-4 h-4 text-amber-400" />
                Launch Hub Progress
              </h3>
              <Link href="/admin/launch" className="text-xs text-amber-400 hover:underline">
                Manage Hub
              </Link>
            </div>

            <div className="mb-4">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-slate-400">Checklist Completion</span>
                <span className="font-mono text-white font-semibold">{launchProgressPct}%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-amber-400 to-cyan-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${launchProgressPct}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2 rounded-lg bg-white/[0.02]">
                <span className="text-[10px] text-slate-500 block">Tasks Done</span>
                <span className="font-mono font-bold text-emerald-400">{completedLaunch} / {totalLaunch}</span>
              </div>
              <div className="p-2 rounded-lg bg-white/[0.02]">
                <span className="text-[10px] text-slate-500 block">Platforms</span>
                <span className="font-mono font-bold text-white">5 Active</span>
              </div>
              <div className="p-2 rounded-lg bg-white/[0.02]">
                <span className="text-[10px] text-slate-500 block">Reviews Sent</span>
                <span className="font-mono font-bold text-cyan-400">G2/Capterra</span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-white/[0.04]">
            <Link
              href="/admin/launch"
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold text-slate-300 transition-all"
            >
              Open Launch Kanban Board →
            </Link>
          </div>
        </div>
      </div>

      {/* Top Posts + Top SEO Pages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Top posts */}
        <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.06]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Top Published Posts</h3>
            <Link href="/admin/calendar" className="text-xs text-slate-400 hover:text-white">
              Calendar
            </Link>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : data?.top_posts.length === 0 ? (
            <div className="text-center py-8 text-slate-600 text-sm">
              No published posts yet. Schedule and approve in the Content Studio.
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
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Search className="w-4 h-4 text-emerald-400" />
              Top Programmatic SEO Pages
            </h3>
            <Link href="/admin/seo" className="text-xs text-emerald-400 hover:underline">
              SEO Manager
            </Link>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : (data?.top_seo_pages.length === 0 && (!publishedSeoPages || publishedSeoPages.length === 0)) ? (
            <div className="text-center py-8 text-slate-600 text-sm">
              No published SEO pages yet. Generate and publish in the SEO Manager.
            </div>
          ) : (
            <div className="space-y-2">
              {(data?.top_seo_pages.length ? data.top_seo_pages : publishedSeoPages?.slice(0, 5) || []).map((page: any) => (
                <div key={page.id} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                  <div className="min-w-0 pr-2">
                    <p className="text-xs font-medium text-slate-300 truncate">{page.title || page.slug}</p>
                    <a
                      href={`/${page.slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-cyan-400 hover:underline truncate block"
                    >
                      /{page.slug}
                    </a>
                  </div>
                  {page.quality_score != null && (
                    <span className="text-xs font-mono font-bold text-emerald-400 shrink-0 ml-2 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                      Score: {page.quality_score}
                    </span>
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
