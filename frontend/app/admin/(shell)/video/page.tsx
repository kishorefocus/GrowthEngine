"use client";

import React, { useState } from "react";
import {
  useVideos,
  usePlanVideo,
  useUploadVideoAsset,
  usePublishYouTube,
  useCrossPostCaptions,
} from "@/lib/hooks";
import {
  Video,
  Sparkles,
  FileText,
  ListOrdered,
  Tag,
  Image as ImageIcon,
  UploadCloud,
  Youtube,
  Share2,
  Copy,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Film,
} from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";

const SUGGESTED_KEYWORDS = [
  "how to find 50 real estate leads in 5 minutes",
  "Apollo.io alternative for small agencies",
  "How to set up DMARC and stop landing in spam",
  "B2B lead generation workflow for commercial insurance",
  "Scraping vs real-time email verification",
];

export default function VideoStudioPage() {
  const [keywordInput, setKeywordInput] = useState("");
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [activePlanTab, setActivePlanTab] = useState<"script" | "shots" | "metadata" | "thumbnail" | "crosspost">("script");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Queries & Mutations
  const { data: videos, isLoading, refetch } = useVideos();
  const planMutation = usePlanVideo();
  const uploadAssetMutation = useUploadVideoAsset();
  const publishYouTubeMutation = usePublishYouTube();
  const crossPostMutation = useCrossPostCaptions();

  const [crossPostData, setCrossPostData] = useState<{
    instagram_reels: string;
    facebook_reels: string;
    linkedin_video: string;
  } | null>(null);

  const activeVideo = videos?.find((v) => v.id === selectedVideoId) || videos?.[0];

  const handleCreatePlan = async (kw?: string) => {
    const kwToUse = kw || keywordInput.trim();
    if (!kwToUse) {
      toast.error("Please enter a target keyword or topic");
      return;
    }
    try {
      toast.info(`Generating complete video production plan for: "${kwToUse}"...`);
      const newProject = await planMutation.mutateAsync({
        targetKeyword: kwToUse,
      });
      setSelectedVideoId(newProject.id);
      setKeywordInput("");
      toast.success("Video plan generated successfully!");
      refetch();
    } catch (err: any) {
      toast.error(`Plan generation failed: ${err.message}`);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSimulateUpload = async (videoId: string) => {
    try {
      const res = await uploadAssetMutation.mutateAsync({
        id: videoId,
        filename: "demo_walkthrough.mp4",
      });
      toast.success("Asset uploaded successfully! Signed URL generated.");
      refetch();
    } catch (err: any) {
      toast.error(`Upload error: ${err.message}`);
    }
  };

  const handlePublishYouTube = async (videoId: string) => {
    if (!confirm("Publish this video to YouTube as PRIVATE?")) return;
    try {
      const res = await publishYouTubeMutation.mutateAsync(videoId);
      toast.success(`Published to YouTube! Video ID: ${res.youtube_video_id} (Privacy: Private)`);
      refetch();
    } catch (err: any) {
      toast.error(`YouTube publish failed: ${err.message}`);
    }
  };

  const handleLoadCrossPost = async (videoId: string) => {
    try {
      const res = await crossPostMutation.mutateAsync(videoId);
      setCrossPostData(res);
      setActivePlanTab("crosspost");
      toast.success("Generated cross-post caption variants!");
    } catch (err: any) {
      toast.error(`Could not generate cross-post captions: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          Video Content Studio
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 font-mono">
            YouTube Data API v3
          </span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Turn search keywords into full scripts, step-by-step shot lists, YouTube metadata with UTM links, and cross-post captions.
        </p>
      </div>

      {/* Target Keyword Input Bar */}
      <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.08] space-y-3">
        <label className="block text-xs font-semibold text-slate-300">Target Keyword / Video Topic</label>
        <div className="flex flex-col sm:flex-row gap-2.5">
          <input
            type="text"
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            placeholder="e.g. how to find 50 real estate leads in 5 minutes"
            className="flex-1 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white text-xs placeholder-slate-600 focus:outline-none focus:border-violet-500"
            onKeyDown={(e) => e.key === "Enter" && handleCreatePlan()}
          />
          <button
            onClick={() => handleCreatePlan()}
            disabled={planMutation.isPending}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500 shadow-sm shadow-violet-600/30 transition-all flex items-center justify-center gap-2 shrink-0 disabled:opacity-50"
          >
            <Sparkles className={clsx("w-3.5 h-3.5", planMutation.isPending && "animate-spin")} />
            {planMutation.isPending ? "Generating Plan..." : "Generate Video Plan"}
          </button>
        </div>

        {/* Suggested Keywords Chips */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] text-slate-500">Suggestions:</span>
          {SUGGESTED_KEYWORDS.map((kw) => (
            <button
              key={kw}
              onClick={() => handleCreatePlan(kw)}
              className="text-[10px] px-2.5 py-1 rounded-lg bg-white/[0.03] text-slate-400 hover:text-slate-200 border border-white/[0.05] hover:border-white/10 transition-all"
            >
              {kw}
            </button>
          ))}
        </div>
      </div>

      {/* Main Studio Body: Project List (Left) + Detail Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Projects list */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Video Projects</h3>
            <button
              onClick={() => refetch()}
              className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
            >
              <RefreshCw className={clsx("w-3 h-3", isLoading && "animate-spin")} />
            </button>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded-xl bg-white/[0.02] border border-white/[0.06] animate-pulse" />
              ))}
            </div>
          ) : !videos || videos.length === 0 ? (
            <div className="p-8 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] text-xs text-slate-500">
              No video projects planned yet. Enter a target keyword above to create one.
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {videos.map((vid) => {
                const isSelected = activeVideo?.id === vid.id;
                return (
                  <div
                    key={vid.id}
                    onClick={() => {
                      setSelectedVideoId(vid.id);
                      setCrossPostData(null);
                    }}
                    className={clsx(
                      "p-3.5 rounded-xl border cursor-pointer transition-all space-y-1.5",
                      isSelected
                        ? "bg-violet-500/10 border-violet-500/30 text-white"
                        : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04] text-slate-300"
                    )}
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-mono text-violet-400 font-semibold truncate max-w-[180px]">
                        {vid.target_keyword || "Keyword"}
                      </span>
                      <span
                        className={clsx(
                          "text-[9px] font-bold uppercase px-1.5 py-0.5 rounded",
                          vid.status === "published"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        )}
                      >
                        {vid.status}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-slate-200 line-clamp-2">
                      {vid.title}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Active Video Plan Details */}
        <div className="lg:col-span-8 space-y-4">
          {activeVideo ? (
            <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08] space-y-6">
              {/* Active Video Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-white/[0.05] text-slate-400">
                    Keyword: {activeVideo.target_keyword}
                  </span>
                  <h3 className="text-lg font-bold text-white leading-snug">
                    {activeVideo.youtube_title || activeVideo.title}
                  </h3>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => handleLoadCrossPost(activeVideo.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-pink-300 bg-pink-500/10 hover:bg-pink-500/20 border border-pink-500/20 transition-all"
                  >
                    <Share2 className="w-3.5 h-3.5" />
                    Cross-Post Captions
                  </button>

                  {activeVideo.youtube_video_id ? (
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      YouTube: {activeVideo.youtube_video_id}
                    </span>
                  ) : (
                    <button
                      onClick={() => handlePublishYouTube(activeVideo.id)}
                      disabled={publishYouTubeMutation.isPending}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white bg-red-600 hover:bg-red-500 shadow-sm shadow-red-600/30 transition-all"
                    >
                      <Youtube className="w-3.5 h-3.5" />
                      Publish YouTube (Private)
                    </button>
                  )}
                </div>
              </div>

              {/* Tabs Selector */}
              <div className="border-b border-white/[0.06] flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
                {[
                  { id: "script", label: "Script (Shorts + YT)", icon: FileText },
                  { id: "shots", label: "Shot List", icon: ListOrdered },
                  { id: "metadata", label: "Metadata & Chapters", icon: Tag },
                  { id: "thumbnail", label: "Thumbnail Prompt", icon: ImageIcon },
                  { id: "crosspost", label: "Cross-Post Cut-Downs", icon: Share2 },
                ].map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActivePlanTab(tab.id as any)}
                      className={clsx(
                        "flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap",
                        activePlanTab === tab.id
                          ? "bg-violet-600 text-white shadow-sm"
                          : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                      )}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Tab Content Panes */}
              {activePlanTab === "script" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Verbatim Script & Outline
                    </span>
                    <button
                      onClick={() => handleCopy(activeVideo.script || "", "script")}
                      className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                    >
                      {copiedKey === "script" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      Copy Script
                    </button>
                  </div>
                  <pre className="p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-200 font-sans whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto">
                    {activeVideo.script}
                  </pre>
                </div>
              )}

              {activePlanTab === "shots" && (
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Screen-Recording Shot List for GlobalReach
                  </h4>
                  <div className="space-y-3">
                    {activeVideo.shot_list && activeVideo.shot_list.length > 0 ? (
                      activeVideo.shot_list.map((shot, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-start gap-3"
                        >
                          <span className="w-6 h-6 rounded-lg bg-violet-500/15 text-violet-400 font-bold text-xs flex items-center justify-center shrink-0">
                            {shot.step_number || idx + 1}
                          </span>
                          <div className="space-y-1">
                            <p className="text-xs font-semibold text-white">
                              {shot.screen} — <span className="text-slate-400 font-normal">{shot.action}</span>
                            </p>
                            <p className="text-[11px] text-slate-500 italic">
                              Cue: &quot;{shot.voiceover_cue}&quot;
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500">No shot list generated.</p>
                    )}
                  </div>
                </div>
              )}

              {activePlanTab === "metadata" && (
                <div className="space-y-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400 uppercase">Recommended Title</label>
                    <p className="p-3 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-white font-medium">
                      {activeVideo.youtube_title || activeVideo.title}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-slate-400 uppercase">Description & Chapters (UTM Link)</label>
                      <button
                        onClick={() => handleCopy(activeVideo.youtube_description || "", "desc")}
                        className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                      >
                        {copiedKey === "desc" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        Copy Description
                      </button>
                    </div>
                    <pre className="p-3.5 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-300 whitespace-pre-wrap font-sans max-h-[200px] overflow-y-auto">
                      {activeVideo.youtube_description}
                    </pre>
                  </div>

                  {activeVideo.tags && (
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-400 uppercase">Tags</label>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {activeVideo.tags.map((t) => (
                          <span key={t} className="text-[11px] px-2.5 py-1 rounded-lg bg-white/[0.04] text-slate-300 border border-white/[0.06]">
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activePlanTab === "thumbnail" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      AI Thumbnail Generation Prompt
                    </h4>
                    <button
                      onClick={() => handleCopy(activeVideo.thumbnail_prompt || "", "thumb")}
                      className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                    >
                      {copiedKey === "thumb" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      Copy Prompt
                    </button>
                  </div>
                  <p className="p-4 rounded-xl bg-black/40 border border-white/[0.06] text-xs text-slate-300 leading-relaxed font-mono">
                    {activeVideo.thumbnail_prompt}
                  </p>
                </div>
              )}

              {activePlanTab === "crosspost" && (
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Cross-Post Caption Cut-Downs (Instagram, Facebook & LinkedIn)
                  </h4>
                  {crossPostData ? (
                    <div className="space-y-3">
                      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1.5">
                        <div className="flex items-center justify-between text-xs font-semibold text-pink-400">
                          <span>Instagram Reels</span>
                          <button onClick={() => handleCopy(crossPostData.instagram_reels, "ig")} className="text-slate-400 hover:text-white">
                            <Copy className="w-3 h-3" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-300">{crossPostData.instagram_reels}</p>
                      </div>

                      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1.5">
                        <div className="flex items-center justify-between text-xs font-semibold text-indigo-400">
                          <span>Facebook Reels</span>
                          <button onClick={() => handleCopy(crossPostData.facebook_reels, "fb")} className="text-slate-400 hover:text-white">
                            <Copy className="w-3 h-3" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-300">{crossPostData.facebook_reels}</p>
                      </div>

                      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1.5">
                        <div className="flex items-center justify-between text-xs font-semibold text-blue-400">
                          <span>LinkedIn Video</span>
                          <button onClick={() => handleCopy(crossPostData.linkedin_video, "li")} className="text-slate-400 hover:text-white">
                            <Copy className="w-3 h-3" />
                          </button>
                        </div>
                        <p className="text-xs text-slate-300 whitespace-pre-wrap">{crossPostData.linkedin_video}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="p-6 text-center rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                      <p className="text-xs text-slate-400">Click below to generate platform-tailored caption variants.</p>
                      <button
                        onClick={() => handleLoadCrossPost(activeVideo.id)}
                        className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-violet-600 hover:bg-violet-500"
                      >
                        Generate Cut-Down Captions
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Asset Upload Bar */}
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-violet-500/10 text-violet-400 flex items-center justify-center">
                    <UploadCloud className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-white">Video Asset Upload (Cloudflare R2 / S3)</p>
                    <p className="text-[11px] text-slate-500">
                      {activeVideo.asset_url ? activeVideo.asset_url : "No file attached yet (Signed PUT URL ready)"}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => handleSimulateUpload(activeVideo.id)}
                  disabled={uploadAssetMutation.isPending}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-200 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-all"
                >
                  {uploadAssetMutation.isPending ? "Generating..." : "Upload Asset"}
                </button>
              </div>
            </div>
          ) : (
            <div className="p-16 text-center rounded-2xl bg-white/[0.02] border border-white/[0.06] text-slate-500">
              Select or generate a video project to inspect its production plan.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
