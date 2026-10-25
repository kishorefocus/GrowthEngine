"use client";

import React, { useState, useEffect } from "react";
import {
  useConnections,
  useConnectMock,
  useDirectConnect,
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
  KeyRound,
  Copy,
  Check,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  X,
  Share2,
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
  defaultId?: string;
  defaultHandle?: string;
}

const PLATFORMS: PlatformConfig[] = [
  {
    id: "facebook",
    name: "Facebook Page",
    category: "Social Network",
    description: "Meta Graph API for publishing feed posts, links, screenshots, and updates to your verified Page.",
    scopes: ["pages_manage_posts", "pages_read_engagement", "pages_show_list"],
    gradient: "from-indigo-600/10 to-blue-700/10 border-indigo-500/20",
    iconBg: "bg-indigo-600/15 text-indigo-400 border-indigo-500/30",
    officialDocUrl: "https://developers.facebook.com/docs/pages-api",
    defaultId: "",
    defaultHandle: "GetyourclientsB2B Facebook",
  },
  {
    id: "instagram",
    name: "Instagram Business",
    category: "Visual Media",
    description: "Meta Graph API container publishing for carousels, screenshots, single images, and Reels.",
    scopes: ["instagram_basic", "instagram_content_publish", "pages_show_list"],
    gradient: "from-pink-600/10 to-rose-600/10 border-pink-500/20",
    iconBg: "bg-pink-600/15 text-pink-400 border-pink-500/30",
    officialDocUrl: "https://developers.facebook.com/docs/instagram-api/guides/content-publishing",
    defaultId: "",
    defaultHandle: "@getyourclientsb2b",
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    category: "Professional Network",
    description: "LinkedIn Posts API for publishing directly to your company / organization page.",
    scopes: ["openid", "profile", "email", "w_member_social"],
    gradient: "from-blue-600/10 to-indigo-600/10 border-blue-500/20",
    iconBg: "bg-blue-600/15 text-blue-400 border-blue-500/30",
    officialDocUrl: "https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api",
    defaultId: "urn:li:organization:98765432",
    defaultHandle: "GetyourclientsB2B",
  },
  {
    id: "x",
    name: "X (Twitter)",
    category: "Microblogging",
    description: "Official API v2 integration with single tweets and multi-tweet thread support.",
    scopes: ["tweet.read", "tweet.write", "users.read", "offline.access"],
    gradient: "from-sky-500/10 to-blue-600/10 border-sky-500/20",
    iconBg: "bg-sky-500/15 text-sky-400 border-sky-500/30",
    officialDocUrl: "https://developer.twitter.com/en/docs/twitter-api",
    defaultId: "1654321987654321",
    defaultHandle: "@getyourclients",
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
    defaultId: "UCgetyourclientsb2b_mock",
    defaultHandle: "@getyourclientsb2b_youtube",
  },
];

export default function ConnectionsPage() {
  const { data: accounts, isLoading, refetch } = useConnections();
  const connectMockMutation = useConnectMock();
  const directConnectMutation = useDirectConnect();
  const disconnectMutation = useDisconnectAccount();

  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
  const [showMetaGuide, setShowMetaGuide] = useState<boolean>(false);
  const [copiedUri, setCopiedUri] = useState<string | null>(null);

  // Direct connect modal state
  const [modalPlatform, setModalPlatform] = useState<PlatformConfig | null>(null);
  const [directExternalId, setDirectExternalId] = useState("");
  const [directHandle, setDirectHandle] = useState("");
  const [directToken, setDirectToken] = useState("");
  const [isSubmittingDirect, setIsSubmittingDirect] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const error = params.get("error");
    if (connected) {
      toast.success(`Connected ${connected.toUpperCase()} account successfully!`);
      refetch();
      window.history.replaceState({}, "", window.location.pathname);
    }
    if (error) {
      toast.error(`Connection notice: ${error}`, { duration: 6000 });
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [refetch]);

  const getAccountForPlatform = (platformId: string) => {
    return accounts?.find((a) => a.platform.toLowerCase() === platformId.toLowerCase());
  };

  const handleCopyUri = (uri: string) => {
    navigator.clipboard.writeText(uri);
    setCopiedUri(uri);
    toast.success("Redirect URI copied to clipboard!");
    setTimeout(() => setCopiedUri(null), 2500);
  };

  const handleStartOAuth = async (platformId: string) => {
    setConnectingPlatform(platformId);

    // If connecting Instagram and Facebook is already connected, try direct sync
    if (platformId === "instagram") {
      const fbConnected = accounts?.some((a) => a.platform.toLowerCase() === "facebook" && a.status === "active");
      if (fbConnected) {
        try {
          const syncRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/connections/instagram/sync-from-facebook`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${localStorage.getItem("gr_access_token") || ""}`,
            },
          });
          if (syncRes.ok) {
            const data = await syncRes.json();
            toast.success(`Connected Instagram (${data.handle}) from Facebook Page!`);
            refetch();
            setConnectingPlatform(null);
            return;
          } else {
            const errData = await syncRes.json().catch(() => ({}));
            const errMsg = errData.detail || "Could not sync Instagram account from Facebook.";
            toast.error(errMsg, { duration: 7000 });
            refetch();
            setConnectingPlatform(null);
            return;
          }
        } catch (err: any) {
          toast.error(err.message || "Failed to connect to server for Instagram sync.");
          setConnectingPlatform(null);
          return;
        }
      }
    }

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
      handleQuickConnect(platformId);
    } finally {
      setConnectingPlatform(null);
    }
  };

  const handleQuickConnect = async (platformId: string) => {
    const config = PLATFORMS.find((p) => p.id === platformId);
    try {
      await connectMockMutation.mutateAsync({
        platform: platformId,
        handle: config?.defaultHandle || `@getyourclientsb2b_${platformId}`,
      });
      toast.success(`Connected ${config?.name || platformId.toUpperCase()} successfully!`);
    } catch (err: any) {
      toast.error(`Connection failed: ${err.message}`);
    }
  };

  const openDirectModal = (config: PlatformConfig) => {
    setModalPlatform(config);
    const existing = getAccountForPlatform(config.id);
    const existingId = existing?.external_id && !existing.external_id.startsWith("mock_") && existing.external_id !== "108923481729012"
      ? existing.external_id
      : "";
    setDirectExternalId(existingId);
    setDirectHandle(existing?.handle || config.defaultHandle || "");
    setDirectToken("");
  };

  const handleDirectConnectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalPlatform) return;

    if (!directToken.trim()) {
      toast.error("Please enter an Access Token or Page Token");
      return;
    }

    setIsSubmittingDirect(true);
    try {
      await directConnectMutation.mutateAsync({
        platform: modalPlatform.id,
        handle: directHandle.trim() || undefined,
        external_id: directExternalId.trim() || undefined,
        access_token: directToken.trim(),
      });
      toast.success(`Connected ${modalPlatform.name} successfully!`);

      // If Facebook was connected with a real token, attempt to auto-sync linked Instagram Business account
      if (modalPlatform.id === "facebook" && !directToken.trim().startsWith("mock_")) {
        try {
          const syncRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/connections/instagram/sync-from-facebook`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${localStorage.getItem("gr_access_token") || ""}`,
            },
          });
          if (syncRes.ok) {
            const data = await syncRes.json();
            toast.success(`Also linked Instagram Business account (${data.handle})!`);
          } else {
            const errData = await syncRes.json().catch(() => ({}));
            if (errData.detail) {
              toast.info(errData.detail, { duration: 6000 });
            }
          }
        } catch {
          // Instagram might not be linked to this Page
        }
      }

      refetch();
      setModalPlatform(null);
    } catch (err: any) {
      toast.error(`Direct connection failed: ${err.message}`);
    } finally {
      setIsSubmittingDirect(false);
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

  const fbAccount = getAccountForPlatform("facebook");
  const isFbConnected = !!fbAccount && fbAccount.status === "active";

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
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-all"
          >
            <RefreshCw className={clsx("w-3.5 h-3.5", isLoading && "animate-spin text-violet-400")} />
            Refresh Status
          </button>
        </div>
      </div>

      {/* Meta OAuth Setup / Troubleshooting Guide */}
      <div className="rounded-2xl border border-violet-500/20 bg-violet-500/[0.04] p-4 text-xs">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-violet-500/20 text-violet-300 flex items-center justify-center font-bold">
              M
            </div>
            <div>
              <p className="font-semibold text-white text-sm">Meta (Facebook & Instagram) Connection Guide</p>
              <p className="text-slate-400 text-[11px]">
                Configured App ID: <span className="font-mono text-violet-300">1125229983597930</span> (GetYourClientsB2B)
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowMetaGuide(!showMetaGuide)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/20 transition-all"
          >
            {showMetaGuide ? "Hide Details" : "Setup & Whitelist URLs"}
            {showMetaGuide ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {showMetaGuide && (
          <div className="mt-4 pt-3 border-t border-violet-500/15 space-y-3 text-slate-300 leading-relaxed">
            <p>
              To connect Facebook & Instagram via the official Meta dialog, ensure these settings in your{" "}
              <a
                href="https://developers.facebook.com/apps/1125229983597930/fb-login/settings/"
                target="_blank"
                rel="noreferrer"
                className="text-violet-400 underline hover:text-violet-300 inline-flex items-center gap-0.5"
              >
                Meta Developer Console <ExternalLink className="w-3 h-3" />
              </a>:
            </p>

            <div className="space-y-2 bg-black/40 p-3 rounded-xl border border-white/[0.06]">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400">Facebook Redirect URI:</span>
                <div className="flex items-center gap-2">
                  <code className="text-[11px] text-emerald-400 font-mono bg-white/[0.03] px-2 py-0.5 rounded border border-white/[0.06]">
                    http://localhost:8000/api/v1/connections/facebook/callback
                  </code>
                  <button
                    onClick={() => handleCopyUri("http://localhost:8000/api/v1/connections/facebook/callback")}
                    className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/10"
                    title="Copy URI"
                  >
                    {copiedUri === "http://localhost:8000/api/v1/connections/facebook/callback" ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400">Instagram Redirect URI:</span>
                <div className="flex items-center gap-2">
                  <code className="text-[11px] text-pink-400 font-mono bg-white/[0.03] px-2 py-0.5 rounded border border-white/[0.06]">
                    http://localhost:8000/api/v1/connections/instagram/callback
                  </code>
                  <button
                    onClick={() => handleCopyUri("http://localhost:8000/api/v1/connections/instagram/callback")}
                    className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/10"
                    title="Copy URI"
                  >
                    {copiedUri === "http://localhost:8000/api/v1/connections/instagram/callback" ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1 text-[11px]">
              <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <p className="font-semibold text-white mb-1">1. Facebook Page Requirement</p>
                <p className="text-slate-400">
                  Meta only allows automated posting to Facebook Pages, not personal profiles. Make sure you have created a Page under your Facebook account.
                </p>
              </div>
              <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <p className="font-semibold text-white mb-1">2. Instagram Business Requirement</p>
                <p className="text-slate-400">
                  Instagram accounts must be a Professional/Business account linked to your Facebook Page in Meta Business Suite.
                </p>
              </div>
            </div>
          </div>
        )}
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
                    <div className="flex items-center gap-1.5">
                      {account?.external_id?.startsWith("mock_") || account?.external_id === plat.defaultId ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20" title="Connected in Sandbox / Test Mode. Posts are simulated. Connect a real Page Token to publish to your live feed.">
                          Sandbox Mode
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Live API
                        </span>
                      )}
                    </div>
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

                  {account?.external_id && (
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">Account / Page ID:</span>
                      <span className="font-mono text-[10px] text-slate-400">
                        {account.external_id}
                      </span>
                    </div>
                  )}

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

                  {isExpired && (
                    <div className="mt-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[11px] leading-relaxed flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-amber-200">Session Expired on Meta:</span> Click <span className="underline font-medium">Reconnect (OAuth)</span> below to refresh, or click <span className="underline font-medium">Token / ID</span> to paste a new token.
                      </div>
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
              <div className="mt-5 pt-3 border-t border-white/[0.06] flex items-center justify-between gap-2 flex-wrap">
                <a
                  href={plat.officialDocUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
                >
                  Docs <ExternalLink className="w-3 h-3" />
                </a>

                <div className="flex items-center gap-2 flex-wrap">
                  {isConnected && account ? (
                    <>
                      {(account?.external_id?.startsWith("mock_") || account?.external_id === plat.defaultId) && (
                        <button
                          onClick={() => openDirectModal(plat)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-violet-200 bg-violet-600/30 hover:bg-violet-600/50 border border-violet-500/30 transition-all"
                          title="Replace sandbox credentials with real live Meta Page Access Token"
                        >
                          <KeyRound className="w-3 h-3 text-violet-300" />
                          Enter Live Token
                        </button>
                      )}
                      <button
                        onClick={() => handleDisconnect(account.id, plat.name)}
                        disabled={disconnectMutation.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-all"
                      >
                        <Unlink className="w-3 h-3" />
                        Disconnect
                      </button>
                    </>
                  ) : (
                    <>
                      {/* Direct Page ID / Token Modal trigger */}
                      <button
                        onClick={() => openDirectModal(plat)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-all"
                        title="Connect directly with Page ID & Access Token"
                      >
                        <KeyRound className="w-3 h-3 text-slate-400" />
                        Token / ID
                      </button>

                      {/* Disconnect button for expired account */}
                      {account && (
                        <button
                          onClick={() => handleDisconnect(account.id, plat.name)}
                          disabled={disconnectMutation.isPending}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-all"
                          title="Remove expired connection"
                        >
                          <Unlink className="w-3 h-3" />
                          Disconnect
                        </button>
                      )}

                      {/* 1-Click Quick Connect */}
                      <button
                        onClick={() => handleQuickConnect(plat.id)}
                        disabled={connectMockMutation.isPending}
                        className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/25 transition-all"
                        title="1-click connect with verified GetyourclientsB2B test account"
                      >
                        1-Click Connect
                      </button>

                      {/* Primary OAuth Connect Button */}
                      <button
                        onClick={() => handleStartOAuth(plat.id)}
                        disabled={connectingPlatform === plat.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 shadow-sm shadow-violet-600/30 transition-all"
                      >
                        <Link2 className="w-3 h-3" />
                        {connectingPlatform === plat.id
                          ? "Connecting..."
                          : isExpired
                          ? "Reconnect (OAuth)"
                          : plat.id === "instagram" && isFbConnected
                          ? "Sync from FB"
                          : "Connect (OAuth)"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Direct Connect / Token Modal */}
      {modalPlatform && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-white/10 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm", modalPlatform.iconBg)}>
                  {modalPlatform.name[0]}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">
                    Direct Connect: {modalPlatform.name}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Connect immediately using a Page ID / Access Token or 1-click test mode.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setModalPlatform(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick 1-click fill button */}
            <div className="p-3 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-white">Testing / Sandbox Mode</p>
                <p className="text-[11px] text-violet-200/80">Connect immediately with verified @getyourclientsb2b credentials.</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setDirectExternalId(modalPlatform.defaultId || "108923481729012");
                  setDirectHandle(modalPlatform.defaultHandle || `@getyourclientsb2b_${modalPlatform.id}`);
                  setDirectToken(`mock_token_${modalPlatform.id}_live_ready`);
                }}
                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-violet-200 bg-violet-500/20 hover:bg-violet-500/30 border border-violet-500/30 transition-all shrink-0"
              >
                Autofill Test Data
              </button>
            </div>

            <form onSubmit={handleDirectConnectSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  {modalPlatform.id === "facebook" ? "Facebook Page ID (Numeric)" : modalPlatform.id === "instagram" ? "Instagram Business Account ID (Numeric)" : "Account / Page ID"}
                </label>
                <input
                  type="text"
                  value={directExternalId}
                  onChange={(e) => setDirectExternalId(e.target.value)}
                  placeholder={modalPlatform.id === "facebook" ? "Leave blank to auto-detect from token" : "e.g. numeric ID"}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-white/[0.04] border border-white/[0.08] text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  {modalPlatform.id === "facebook" && "Must be a Facebook Page ID (not personal profile). Leave blank to auto-detect from your token."}
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Display Handle / Page Name
                </label>
                <input
                  type="text"
                  value={directHandle}
                  onChange={(e) => setDirectHandle(e.target.value)}
                  placeholder={modalPlatform.defaultHandle || "e.g. @getyourclientsb2b"}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-white/[0.04] border border-white/[0.08] text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Access Token / Page Token <span className="text-rose-400">*</span>
                </label>
                <textarea
                  value={directToken}
                  onChange={(e) => setDirectToken(e.target.value)}
                  placeholder="Paste Meta Page Access Token (from Graph API Explorer or Meta Business Suite) or test token..."
                  rows={3}
                  required
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-white/[0.04] border border-white/[0.08] text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Tokens are encrypted at rest with Fernet. Real tokens are auto-verified against Meta Graph API.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalPlatform(null)}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingDirect}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 shadow-md shadow-violet-600/30 transition-all flex items-center gap-1.5"
                >
                  {isSubmittingDirect ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Save & Connect
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
