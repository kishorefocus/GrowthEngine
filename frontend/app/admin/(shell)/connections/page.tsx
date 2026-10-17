"use client";

import React, { useState } from "react";
import {
  useConnections,
  useConnectMock,
  useDisconnectAccount,
} from "@/lib/hooks";
import {
  ShieldCheck,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Unlink,
  Link2,
  Sparkles,
  Info,
} from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";

interface PlatformConfig {
  id: "x" | "linkedin" | "instagram" | "facebook" | "youtube";
  name: string;
  category: string;
  description: string;
  scopes: string[];
  gradient: string;
  iconBg: string;
  officialDocUrl: string;
}

const PLATFORMS: PlatformConfig[] = [
  {
    id: "x",
    name: "X (Twitter)",
    category: "Microblogging",
    description: "Official API v2 integration with single tweets and multi-tweet thread support.",
    scopes: ["tweet.read", "tweet.write", "users.read", "offline.access"],
    gradient: "from-sky-500/10 to-blue-600/10 border-sky-500/20",
    iconBg: "bg-sky-500/15 text-sky-400 border-sky-500/30",
    officialDocUrl: "https://developer.twitter.com/en/docs/twitter-api",
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    category: "Professional Network",
    description: "LinkedIn Posts API for publishing directly to your company / organization page.",
    scopes: ["w_member_social", "r_organization_social", "w_organization_social"],
    gradient: "from-blue-600/10 to-indigo-600/10 border-blue-500/20",
    iconBg: "bg-blue-600/15 text-blue-400 border-blue-500/30",
    officialDocUrl: "https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api",
  },
  {
    id: "instagram",
    name: "Instagram Business",
    category: "Visual Media",
    description: "Meta Graph API container publishing for carousels, single images, and Reels.",
    scopes: ["instagram_basic", "instagram_content_publish", "pages_show_list"],
    gradient: "from-pink-600/10 to-rose-600/10 border-pink-500/20",
    iconBg: "bg-pink-600/15 text-pink-400 border-pink-500/30",
    officialDocUrl: "https://developers.facebook.com/docs/instagram-api/guides/content-publishing",
  },
  {
    id: "facebook",
    name: "Facebook Page",
    category: "Social Network",
    description: "Facebook Graph API for publishing feed posts, links, and updates to your verified Page.",
    scopes: ["pages_manage_posts", "pages_read_engagement"],
    gradient: "from-indigo-600/10 to-blue-700/10 border-indigo-500/20",
    iconBg: "bg-indigo-600/15 text-indigo-400 border-indigo-500/30",
    officialDocUrl: "https://developers.facebook.com/docs/pages-api",
  },
  {
    id: "youtube",
    name: "YouTube",
    category: "Video Streaming",
    description: "Google Cloud YouTube Data API v3 for uploading private review videos and Shorts.",
    scopes: ["youtube.upload", "youtube.readonly"],
    gradient: "from-red-600/10 to-rose-700/10 border-red-500/20",
    iconBg: "bg-red-600/15 text-red-400 border-red-500/30",
    officialDocUrl: "https://developers.google.com/youtube/v3/docs/videos/insert",
  },
];

export default function ConnectionsPage() {
  const { data: accounts, isLoading, refetch } = useConnections();
  const connectMockMutation = useConnectMock();
  const disconnectMutation = useDisconnectAccount();

  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);

  const getAccountForPlatform = (platformId: string) => {
    return accounts?.find((a) => a.platform.toLowerCase() === platformId.toLowerCase());
  };

  const handleStartOAuth = async (platformId: string) => {
    setConnectingPlatform(platformId);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/connections/${platformId}/authorize`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("gr_access_token") || ""}`,
        },
      });
      if (!res.ok) throw new Error("Could not start OAuth flow");
      const data = await res.json();
      window.location.href = data.authorization_url;
    } catch (err: any) {
      toast.error(err.message || "OAuth initialization failed. Using Sandbox/Mock mode.");
      // Fallback to quick simulated connect
      handleMockConnect(platformId);
    } finally {
      setConnectingPlatform(null);
    }
  };

  const handleMockConnect = async (platformId: string) => {
    try {
      await connectMockMutation.mutateAsync({
        platform: platformId,
        handle: `@globalreach_${platformId}`,
      });
      toast.success(`Connected ${platformId.toUpperCase()} account successfully!`);
    } catch (err: any) {
      toast.error(`Connection failed: ${err.message}`);
    }
  };

  const handleDisconnect = async (accountId: string, platformName: string) => {
    if (!confirm(`Are you sure you want to disconnect ${platformName}?`)) return;
    try {
      await disconnectMutation.mutateAsync(accountId);
      toast.success(`Disconnected ${platformName}`);
    } catch (err: any) {
      toast.error(`Disconnect failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            Social & Video Connections
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
              Official APIs
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Connect verified social accounts to publish approved posts and video assets directly via official APIs.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="self-start sm:self-auto flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-all"
        >
          <RefreshCw className={clsx("w-3.5 h-3.5", isLoading && "animate-spin text-violet-400")} />
          Refresh Status
        </button>
      </div>

      {/* Security & Official API Notice */}
      <div className="p-4 rounded-2xl bg-violet-500/10 border border-violet-500/20 text-xs text-violet-200 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-violet-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-white">Official APIs & Human Approval Security Guardrails</p>
          <p className="text-violet-200/80 leading-relaxed">
            All posts and video uploads are transmitted strictly via official OAuth 2.0 endpoints (no headless browser bots, no automated DMs).
            OAuth credentials are encrypted at rest with Fernet and tokens are refreshed automatically by the hourly background worker.
          </p>
        </div>
      </div>

      {/* Grid of Platforms */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PLATFORMS.map((plat) => {
          const account = getAccountForPlatform(plat.id);
          const isConnected = !!account && account.status === "active";
          const isExpired = account?.status === "expired";

          return (
            <div
              key={plat.id}
              className={clsx(
                "p-5 rounded-2xl bg-white/[0.02] border transition-all flex flex-col justify-between",
                plat.gradient,
                isConnected ? "border-emerald-500/30" : "border-white/[0.08] hover:border-white/15"
              )}
            >
              <div>
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={clsx("w-10 h-10 rounded-xl border flex items-center justify-center font-bold text-base", plat.iconBg)}>
                      {plat.name[0]}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-white">{plat.name}</h3>
                      <p className="text-[11px] text-slate-500">{plat.category}</p>
                    </div>
                  </div>

                  {/* Status Badge */}
                  {isConnected ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Active
                    </span>
                  ) : isExpired ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      <AlertTriangle className="w-3 h-3" />
                      Token Expired
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-800 text-slate-400 border border-white/[0.06]">
                      Not Connected
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className="text-xs text-slate-400 mt-3.5 leading-relaxed">{plat.description}</p>

                {/* Scopes & Details */}
                <div className="mt-4 pt-3 border-t border-white/[0.04] space-y-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Connected Account:</span>
                    <span className="font-mono text-slate-300 font-medium">
                      {account?.handle || "—"}
                    </span>
                  </div>

                  {account?.expires_at && (
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">Token Status:</span>
                      <span className={clsx("font-mono text-[10px]", isExpired ? "text-amber-400 font-semibold" : "text-slate-400")}>
                        {isExpired
                          ? "Expired (Refresh required)"
                          : `Valid until ${new Date(account.expires_at).toLocaleDateString()}`}
                      </span>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1 pt-1">
                    {plat.scopes.map((s) => (
                      <span
                        key={s}
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-500 border border-white/[0.04]"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-5 pt-3 border-t border-white/[0.06] flex items-center justify-between gap-2">
                <a
                  href={plat.officialDocUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
                >
                  Docs <ExternalLink className="w-3 h-3" />
                </a>

                <div className="flex items-center gap-2">
                  {isConnected && account ? (
                    <button
                      onClick={() => handleDisconnect(account.id, plat.name)}
                      disabled={disconnectMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-all"
                    >
                      <Unlink className="w-3 h-3" />
                      Disconnect
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => handleMockConnect(plat.id)}
                        disabled={connectMockMutation.isPending}
                        className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] transition-all"
                        title="Connect instantly using sandbox mode without external API app configuration"
                      >
                        Sandbox
                      </button>
                      <button
                        onClick={() => handleStartOAuth(plat.id)}
                        disabled={connectingPlatform === plat.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 shadow-sm shadow-violet-600/30 transition-all"
                      >
                        <Link2 className="w-3 h-3" />
                        {connectingPlatform === plat.id ? "Connecting..." : "Connect"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
