"use client";

import React, { useState } from "react";
import {
  useCalendarFeed,
  usePosts,
  useApprovePost,
  useRejectPost,
  useReschedulePost,
  useRetryPost,
  usePublishPost,
  useUpdatePost,
} from "@/lib/hooks";
import {
  Calendar as CalendarIcon,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  RefreshCw,
  Send,
  AlertCircle,
  Eye,
  Edit3,
  CalendarDays,
  Sparkles,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";
import Link from "next/link";

const PLATFORMS = [
  { id: "all", name: "All Platforms" },
  { id: "x", name: "X (Twitter)", color: "#38bdf8", bg: "bg-sky-500/15 text-sky-400 border-sky-500/20" },
  { id: "linkedin", name: "LinkedIn", color: "#60a5fa", bg: "bg-blue-500/15 text-blue-400 border-blue-500/20" },
  { id: "instagram", name: "Instagram", color: "#f472b6", bg: "bg-pink-500/15 text-pink-400 border-pink-500/20" },
  { id: "facebook", name: "Facebook", color: "#818cf8", bg: "bg-indigo-500/15 text-indigo-400 border-indigo-500/20" },
  { id: "youtube", name: "YouTube", color: "#f87171", bg: "bg-red-500/15 text-red-400 border-red-500/20" },
];

function getLivePostUrl(platform: string, externalId?: string): string | null {
  if (!externalId || externalId.includes("mock") || externalId.includes("dryrun")) return null;
  const plat = platform.toLowerCase();
  if (plat === "linkedin") {
    return `https://www.linkedin.com/feed/update/${encodeURIComponent(externalId)}/`;
  }
  if (plat === "x") {
    return `https://x.com/i/status/${externalId}`;
  }
  if (plat === "facebook") {
    if (externalId.includes("_")) {
      const parts = externalId.split("_");
      return `https://www.facebook.com/${parts[0]}/posts/${parts[1]}`;
    }
    return `https://www.facebook.com/${externalId}`;
  }
  return null;
}

function PostMediaGallery({ mediaUrls, platform }: { mediaUrls?: string[]; platform: string }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!mediaUrls || mediaUrls.length === 0) return null;

  const validImages = mediaUrls.filter(
    (url) => url.endsWith(".png") || url.endsWith(".jpg") || url.startsWith("http") || url.startsWith("/")
  );

  if (validImages.length === 0) {
    return (
      <div className="p-3 rounded-lg bg-white/[0.04] border border-white/[0.06] text-[11px] text-slate-400">
        <span className="font-semibold text-slate-200">Image Prompt:</span> {mediaUrls[0]}
      </div>
    );
  }

  const currentImg = validImages[currentIndex] || validImages[0];
  const imageName = currentImg.split("/").pop()?.replace(".png", "").replace(".jpg", "") || "";

  return (
    <div className="space-y-2">
      {/* Main image viewer with carousel navigation */}
      <div className="rounded-xl overflow-hidden border border-white/[0.08] bg-black/70 shadow-xl group relative">
        <img
          src={currentImg}
          alt={`Slide ${currentIndex + 1} - ${imageName}`}
          className="w-full h-56 object-cover object-top hover:scale-[1.01] transition-transform duration-200"
        />

        {/* Top badges */}
        <div className="absolute top-2 left-2 right-2 flex items-center justify-between pointer-events-none">
          <span className="px-2 py-0.5 rounded-full bg-black/80 backdrop-blur-md text-[10px] font-mono text-white/90 border border-white/10 shadow-sm">
            {currentIndex + 1} / {validImages.length}
          </span>
          <span
            className={clsx(
              "px-2 py-0.5 rounded-full text-[10px] font-medium backdrop-blur-md border shadow-sm",
              platform === "instagram"
                ? "bg-pink-500/20 text-pink-300 border-pink-500/30"
                : "bg-blue-500/20 text-blue-300 border-blue-500/30"
            )}
          >
            {platform === "instagram" ? "Instagram Carousel" : "Facebook Gallery"} ({validImages.length} images)
          </span>
        </div>

        {/* Prev / Next controls */}
        {validImages.length > 1 && (
          <>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setCurrentIndex((prev) => (prev > 0 ? prev - 1 : validImages.length - 1));
              }}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/75 hover:bg-black text-white flex items-center justify-center transition-all opacity-80 hover:opacity-100 border border-white/10 text-sm font-bold shadow-md cursor-pointer"
              title="Previous image"
            >
              ‹
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setCurrentIndex((prev) => (prev < validImages.length - 1 ? prev + 1 : 0));
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/75 hover:bg-black text-white flex items-center justify-center transition-all opacity-80 hover:opacity-100 border border-white/10 text-sm font-bold shadow-md cursor-pointer"
              title="Next image"
            >
              ›
            </button>
          </>
        )}

        {/* Bottom bar with filename */}
        <div className="px-3 py-1.5 bg-black/90 flex items-center justify-between text-[10px] text-slate-400 border-t border-white/[0.06]">
          <span className="font-mono text-slate-200 capitalize font-medium">{imageName.replace(/-/g, " ")}.png</span>
          <span className="text-slate-400 text-[10px]">
            {validImages.length > 1 ? `${validImages.length} screenshots attached` : "1 screenshot"}
          </span>
        </div>
      </div>

      {/* Thumbnails row (showing all images inside the folder) */}
      {validImages.length > 1 && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-0.5 scrollbar-thin">
          {validImages.map((img, idx) => {
            const thumbName = img.split("/").pop()?.replace(".png", "") || "";
            return (
              <button
                key={img + idx}
                type="button"
                onClick={() => setCurrentIndex(idx)}
                className={clsx(
                  "relative shrink-0 rounded-lg overflow-hidden border transition-all cursor-pointer",
                  idx === currentIndex
                    ? "border-violet-500 ring-2 ring-violet-500/50 scale-105"
                    : "border-white/10 opacity-60 hover:opacity-100"
                )}
                title={thumbName}
              >
                <img
                  src={img}
                  alt={thumbName}
                  className="w-12 h-9 object-cover object-top"
                />
                <span className="absolute bottom-0 inset-x-0 bg-black/80 text-[8px] font-mono text-center text-white truncate px-0.5">
                  {idx + 1}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function CalendarPage() {
  const [activeTab, setActiveTab] = useState<"calendar" | "approval">("calendar");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"month" | "week">("week");
  const [selectedPostForPreview, setSelectedPostForPreview] = useState<any | null>(null);

  // Reschedule state
  const [reschedulingPost, setReschedulingPost] = useState<any | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState<string>("");

  // Queries & Mutations
  const { data: calendarData, isLoading: isCalendarLoading, refetch: refetchCalendar } = useCalendarFeed({
    platform: selectedPlatform === "all" ? undefined : selectedPlatform,
  });

  const { data: posts, isLoading: isPostsLoading, refetch: refetchPosts } = usePosts({
    platform: selectedPlatform === "all" ? undefined : selectedPlatform,
  });

  const approveMutation = useApprovePost();
  const rejectMutation = useRejectPost();
  const rescheduleMutation = useReschedulePost();
  const retryMutation = useRetryPost();
  const publishMutation = usePublishPost();

  const pendingPosts = posts?.filter((p) => p.status === "pending_approval") || [];
  const scheduledPosts = posts?.filter((p) => p.status === "scheduled") || [];

  const handlePublishNow = async (id: string) => {
    try {
      const res = await publishMutation.mutateAsync(id);
      if (res?.external_post_id?.includes("mock") || res?.external_post_id?.includes("dryrun")) {
        toast.info("Published in Sandbox / Test Mode. To publish live to your Facebook Page or Instagram feed, connect your real Meta Page Access Token in Connections.", { duration: 7000 });
      } else {
        toast.success("Post published live to platform!");
      }
      refetchCalendar();
      refetchPosts();
    } catch (err: any) {
      toast.error(`Publishing failed: ${err.message}`);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await approveMutation.mutateAsync({ id });
      toast.success("Post approved and scheduled for publishing!");
      refetchCalendar();
      refetchPosts();
    } catch (err: any) {
      toast.error(`Approval failed: ${err.message}`);
    }
  };

  const handleReject = async (id: string) => {
    const reason = prompt("Optional reason for rejection:", "Tone adjustment needed");
    try {
      await rejectMutation.mutateAsync({ id, reason: reason || undefined });
      toast.info("Post rejected");
      refetchCalendar();
      refetchPosts();
    } catch (err: any) {
      toast.error(`Rejection failed: ${err.message}`);
    }
  };

  const handleRescheduleSubmit = async () => {
    if (!reschedulingPost || !rescheduleDate) return;
    try {
      await rescheduleMutation.mutateAsync({
        id: reschedulingPost.id,
        scheduledAt: new Date(rescheduleDate).toISOString(),
      });
      toast.success("Post rescheduled successfully!");
      setReschedulingPost(null);
      refetchCalendar();
      refetchPosts();
    } catch (err: any) {
      toast.error(`Rescheduling failed: ${err.message}`);
    }
  };

  const handleRetry = async (id: string) => {
    try {
      await retryMutation.mutateAsync(id);
      toast.success("Retry queued! Publisher will execute within 1 minute.");
      refetchCalendar();
      refetchPosts();
    } catch (err: any) {
      toast.error(`Retry failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            Social Studio & Calendar
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20 font-mono">
              DRY_RUN Active
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Review drafts, approve in queue with side-by-side platform previews, and manage schedule times.
          </p>
        </div>

        {/* View and Tab toggles */}
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center gap-1">
            <button
              onClick={() => setActiveTab("calendar")}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5",
                activeTab === "calendar" ? "bg-violet-600 text-white shadow-sm" : "text-slate-400 hover:text-white"
              )}
            >
              <CalendarDays className="w-3.5 h-3.5" />
              Calendar
            </button>
            <button
              onClick={() => setActiveTab("approval")}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 relative",
                activeTab === "approval" ? "bg-violet-600 text-white shadow-sm" : "text-slate-400 hover:text-white"
              )}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Approval Queue
              {pendingPosts.length > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500 text-black font-bold">
                  {pendingPosts.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Filter Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPlatform(p.id)}
              className={clsx(
                "px-3 py-1.5 rounded-xl text-xs font-medium border transition-all whitespace-nowrap",
                selectedPlatform === p.id
                  ? "bg-white/[0.1] text-white border-white/20 font-semibold"
                  : "bg-white/[0.02] text-slate-400 border-white/[0.06] hover:bg-white/[0.05]"
              )}
            >
              {p.name}
            </button>
          ))}
        </div>

        {activeTab === "calendar" && (
          <div className="flex items-center gap-2">
            <div className="p-1 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center text-xs">
              <button
                onClick={() => setViewMode("week")}
                className={clsx("px-2.5 py-1 rounded-lg", viewMode === "week" ? "bg-white/[0.1] text-white" : "text-slate-400")}
              >
                Week
              </button>
              <button
                onClick={() => setViewMode("month")}
                className={clsx("px-2.5 py-1 rounded-lg", viewMode === "month" ? "bg-white/[0.1] text-white" : "text-slate-400")}
              >
                Month
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── TAB 1: CALENDAR VIEW ───────────────────────────────────────────── */}
      {activeTab === "calendar" && (
        <div className="space-y-4">
          {/* Best Time Heuristic Bar */}
          {calendarData?.best_time_suggestions && (
            <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 text-slate-300">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span className="font-semibold text-white">Suggested Posting Windows:</span>
                <span className="text-slate-500 hidden md:inline">
                  (Weekday mornings in target timezones)
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                {Object.entries(calendarData.best_time_suggestions).map(([plat, times]) => (
                  <div key={plat} className="flex items-center gap-1.5 text-[11px] font-mono">
                    <span className="capitalize text-slate-400">{plat}:</span>
                    <span className="text-violet-300 font-semibold">{times.join(", ")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Calendar Items List / Timeline */}
          {isCalendarLoading ? (
            <div className="p-12 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] animate-pulse">
              <RefreshCw className="w-6 h-6 text-violet-400 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading scheduled calendar feed...</p>
            </div>
          ) : !calendarData || calendarData.items.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-3">
              <CalendarIcon className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-sm font-semibold text-white">No scheduled posts on calendar</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Approve drafts from the Approval Queue or generate a new batch from Content Ideas to schedule posts.
              </p>
              <Link
                href="/admin/ideas"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 transition-all"
              >
                Go to Ideas Studio
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {calendarData.items.map((item) => {
                const platConf = PLATFORMS.find((p) => p.id === item.platform.toLowerCase()) || {
                  name: item.platform,
                  bg: "bg-slate-800 text-slate-400 border-white/[0.06]",
                };

                return (
                  <div
                    key={item.id}
                    className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:border-white/12 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-3">
                        <span className={clsx("text-[10px] font-semibold px-2 py-0.5 rounded-md border", platConf.bg)}>
                          {platConf.name}
                        </span>
                        <span
                          className={clsx(
                            "text-[10px] font-medium px-2 py-0.5 rounded-full",
                            item.status === "published"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : item.status === "failed"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          )}
                        >
                          {item.status}
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 line-clamp-4 leading-relaxed font-sans">
                        {item.body}
                      </p>
                      {item.error && (
                        <p className="text-[11px] text-rose-400 mt-2 bg-rose-500/10 p-2 rounded-lg border border-rose-500/20">
                          {item.error}
                        </p>
                      )}
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/[0.04] space-y-2.5">
                      <div className="flex items-center justify-between text-[11px] text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-400" />
                          {new Date(item.scheduled_at).toLocaleString([], {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>

                        <div className="flex items-center gap-1.5">
                          {item.status === "published" && item.external_post_id && getLivePostUrl(item.platform, item.external_post_id) && (
                            <a
                              href={getLivePostUrl(item.platform, item.external_post_id)!}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2 py-1 rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 text-[10px] font-semibold flex items-center gap-1 transition-all"
                              title="Open live post in new tab"
                            >
                              <ExternalLink className="w-2.5 h-2.5" />
                              View Live
                            </a>
                          )}
                          {item.status !== "published" && (
                            <button
                              onClick={() => handlePublishNow(item.id)}
                              disabled={publishMutation.isPending}
                              className="px-2 py-1 rounded bg-violet-600/20 text-violet-300 hover:bg-violet-600/30 text-[10px] font-semibold flex items-center gap-1 transition-all"
                              title="Publish now"
                            >
                              <Send className="w-2.5 h-2.5" />
                              Publish Now
                            </button>
                          )}
                          {item.status === "failed" && (
                            <button
                              onClick={() => handleRetry(item.id)}
                              className="px-2 py-1 rounded bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 text-[10px] font-semibold flex items-center gap-1"
                            >
                              <RotateCcw className="w-2.5 h-2.5" />
                              Retry
                            </button>
                          )}
                          <button
                            onClick={() => {
                              setReschedulingPost(item);
                              setRescheduleDate(item.scheduled_at.slice(0, 16));
                            }}
                            className="px-2 py-1 rounded bg-white/[0.04] text-slate-400 hover:text-white text-[10px] font-medium"
                          >
                            Reschedule
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─── TAB 2: APPROVAL QUEUE ─────────────────────────────────────────── */}
      {activeTab === "approval" && (
        <div className="space-y-4">
          {pendingPosts.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <h3 className="text-base font-semibold text-white">Approval Queue is Clear</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                No items are currently pending review. When new weekly batches are generated or converted from ideas, they will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingPosts.map((post) => (
                <div
                  key={post.id}
                  className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.08] hover:border-white/12 transition-all space-y-4"
                >
                  {/* Top card row */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/20">
                        {post.platform}
                      </span>
                      {post.link_url && (
                        <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                          UTM Link: <span className="text-slate-400">{post.link_url}</span>
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleReject(post.id)}
                        disabled={rejectMutation.isPending}
                        className="px-3 py-1.5 rounded-xl text-xs font-medium text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition-all flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Reject
                      </button>
                      <button
                        onClick={() => handlePublishNow(post.id)}
                        disabled={publishMutation.isPending}
                        className="px-3 py-1.5 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 shadow-sm shadow-violet-600/30 transition-all flex items-center gap-1.5"
                        title="Publish immediately"
                      >
                        <Send className="w-3.5 h-3.5" />
                        Publish Now
                      </button>
                      <button
                        onClick={() => handleApprove(post.id)}
                        disabled={approveMutation.isPending}
                        className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 shadow-sm shadow-emerald-600/30 transition-all flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Approve & Schedule
                      </button>
                    </div>
                  </div>

                  {/* Side-by-side platform preview mockup */}
                  <div className="p-4 rounded-xl bg-black/40 border border-white/[0.04]">
                    {post.platform === "x" && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-white">
                            GC
                          </div>
                          <div>
                            <div className="flex items-center gap-1">
                              <span className="text-xs font-bold text-white">GetyourclientsB2B</span>
                              <span className="text-[11px] text-slate-500">@getyourclientsb2b · Just now</span>
                            </div>
                          </div>
                        </div>
                        <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed pl-10">
                          {post.body}
                        </p>
                        <div className="pl-10">
                          <PostMediaGallery mediaUrls={post.media_urls} platform="x" />
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono pl-10 pt-1">
                          Character count: {post.body?.length || 0} / 280 (X v2 compliant)
                        </div>
                      </div>
                    )}

                    {post.platform === "linkedin" && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-xs font-bold text-white">
                            GC
                          </div>
                          <div>
                            <span className="text-xs font-bold text-white">GetyourclientsB2B</span>
                            <p className="text-[10px] text-slate-500">B2B Client Discovery & Cold Outreach CRM</p>
                          </div>
                        </div>
                        <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                          {post.body}
                        </p>
                        <PostMediaGallery mediaUrls={post.media_urls} platform="linkedin" />
                        <div className="text-[10px] text-slate-500 font-mono pt-1">
                          Length: {post.body?.length || 0} characters (Target 800 - 1,300)
                        </div>
                      </div>
                    )}

                    {post.platform === "instagram" && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-500 to-pink-500 p-0.5">
                            <div className="w-full h-full bg-black rounded-full flex items-center justify-center text-[10px] font-bold text-white">
                              GC
                            </div>
                          </div>
                          <span className="text-xs font-bold text-white">getyourclientsb2b</span>
                        </div>
                        <PostMediaGallery mediaUrls={post.media_urls} platform="instagram" />
                        <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                          {post.body}
                        </p>
                      </div>
                    )}

                    {post.platform === "facebook" && (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white">
                            f
                          </div>
                          <span className="text-xs font-bold text-white">GetyourclientsB2B</span>
                        </div>
                        <PostMediaGallery mediaUrls={post.media_urls} platform="facebook" />
                        <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                          {post.body}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reschedule Modal */}
      {reschedulingPost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm p-6 rounded-2xl bg-[#0e0e17] border border-white/[0.08] shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Reschedule Post</h3>
            <p className="text-xs text-slate-400">
              Select the new timestamp to publish to {reschedulingPost.platform.toUpperCase()}:
            </p>

            <input
              type="datetime-local"
              value={rescheduleDate}
              onChange={(e) => setRescheduleDate(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white text-xs focus:outline-none focus:border-violet-500"
            />

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setReschedulingPost(null)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRescheduleSubmit}
                disabled={rescheduleMutation.isPending}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 transition-all"
              >
                Confirm Reschedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
