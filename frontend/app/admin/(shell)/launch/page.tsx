"use client";

import React, { useState } from "react";
import {
  useLaunchTasks,
  useCreateLaunchTask,
  useUpdateLaunchTask,
  useDeleteLaunchTask,
  useGenerateLaunchAssets,
  useReviewRequests,
  useSendReviewRequest,
} from "@/lib/hooks";
import { LaunchTaskItem } from "@/lib/api-client";

const PLATFORMS = [
  { id: "all", label: "All Platforms", icon: "🚀" },
  { id: "product_hunt", label: "Product Hunt", icon: "😸" },
  { id: "g2", label: "G2", icon: "⭐" },
  { id: "capterra", label: "Capterra", icon: "🔷" },
  { id: "reddit", label: "Reddit", icon: "🤖" },
  { id: "indiehackers", label: "IndieHackers", icon: "🛠️" },
];

export default function LaunchHubAdminPage() {
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const platformQuery = selectedPlatform === "all" ? undefined : selectedPlatform;

  const { data: tasks, isLoading: loadingTasks } = useLaunchTasks(platformQuery);
  const { data: reviewRequests, isLoading: loadingReviews } = useReviewRequests();

  const updateTaskMutation = useUpdateLaunchTask();
  const createTaskMutation = useCreateLaunchTask();
  const deleteTaskMutation = useDeleteLaunchTask();
  const generateAssetsMutation = useGenerateLaunchAssets();
  const sendReviewMutation = useSendReviewRequest();

  // Modals
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);
  const [activeAssetTask, setActiveAssetTask] = useState<LaunchTaskItem | null>(null);
  const [generatedAssets, setGeneratedAssets] = useState<any>(null);

  // Review request form
  const [reviewEmail, setReviewEmail] = useState("");
  const [reviewPlatform, setReviewPlatform] = useState<"g2" | "capterra">("g2");
  const [reviewMsg, setReviewMsg] = useState<string | null>(null);

  // New task form
  const [newTaskPlatform, setNewTaskPlatform] = useState("product_hunt");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskDesc, setNewTaskDesc] = useState("");

  const totalTasks = tasks?.length || 0;
  const completedTasks = tasks?.filter((t) => t.status === "done").length || 0;
  const inProgressTasks = tasks?.filter((t) => t.status === "in_progress").length || 0;
  const pendingTasks = tasks?.filter((t) => t.status === "pending").length || 0;
  const completionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  const handleStatusChange = async (task: LaunchTaskItem, newStatus: string) => {
    await updateTaskMutation.mutateAsync({
      id: task.id,
      data: { status: newStatus as any },
    });
  };

  const handleOpenAssetGenerator = async (task: LaunchTaskItem) => {
    setActiveAssetTask(task);
    try {
      const res = await generateAssetsMutation.mutateAsync({
        platform: task.platform,
        taskType: task.platform === "reddit" ? "build_journey" : "launch_copy",
      });
      setGeneratedAssets(res.assets);
    } catch {
      setGeneratedAssets(task.assets || null);
    }
  };

  const handleSendReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setReviewMsg(null);
    try {
      await sendReviewMutation.mutateAsync({
        userEmail: reviewEmail,
        platform: reviewPlatform,
      });
      setReviewMsg(`Review request sent to ${reviewEmail}!`);
      setReviewEmail("");
      setTimeout(() => setShowReviewModal(false), 1500);
    } catch (err: any) {
      setReviewMsg(err?.message || "Failed to send review request.");
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    await createTaskMutation.mutateAsync({
      platform: newTaskPlatform as any,
      title: newTaskTitle.trim(),
      description: newTaskDesc.trim() || undefined,
      status: "pending",
    });
    setNewTaskTitle("");
    setNewTaskDesc("");
    setShowNewTaskModal(false);
  };

  const filterTasksByStatus = (status: string) => {
    return (tasks || []).filter((t) => t.status === status);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Launch Hub & Reviews</h1>
          <p className="text-xs text-slate-400 mt-1">
            Track launch checklists for Product Hunt, G2, Capterra, Reddit, and IndieHackers with AI-assisted copy.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowReviewModal(true)}
            className="px-3.5 py-2 rounded-lg border border-slate-700 bg-slate-800 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition-colors"
          >
            ⭐ Send Review Request
          </button>
          <button
            onClick={() => setShowNewTaskModal(true)}
            className="px-4 py-2 rounded-lg font-bold text-xs text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110 shadow-md shadow-cyan-500/20 transition-all"
          >
            + New Task
          </button>
        </div>
      </div>

      {/* Progress & Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-slate-400 font-medium">Launch Progress</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">{completionRate}%</div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-cyan-500 to-teal-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${completionRate}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-emerald-400 font-medium">Done</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{completedTasks}</div>
          <div className="text-[10px] text-slate-500 mt-1">Verified & submitted</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-amber-400 font-medium">In Progress</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{inProgressTasks}</div>
          <div className="text-[10px] text-slate-500 mt-1">Copy & assets ready</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs text-slate-400 font-medium">Review Requests Sent</div>
          <div className="text-2xl font-bold text-white mt-1">{reviewRequests?.length || 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">G2 & Capterra campaigns</div>
        </div>
      </div>

      {/* Platform Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800/80 pb-3">
        {PLATFORMS.map((p) => {
          const isActive = selectedPlatform === p.id;
          return (
            <button
              key={p.id}
              onClick={() => setSelectedPlatform(p.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          );
        })}
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Column: Pending */}
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-500" />
              Pending ({filterTasksByStatus("pending").length})
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[600px] pr-1">
            {filterTasksByStatus("pending").map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onStatusChange={handleStatusChange}
                onOpenAsset={handleOpenAssetGenerator}
                onDelete={() => deleteTaskMutation.mutate(task.id)}
              />
            ))}
            {filterTasksByStatus("pending").length === 0 && (
              <div className="p-4 text-center text-slate-600 text-xs italic">No pending tasks</div>
            )}
          </div>
        </div>

        {/* Column: In Progress */}
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-amber-500/20 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              In Progress ({filterTasksByStatus("in_progress").length})
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[600px] pr-1">
            {filterTasksByStatus("in_progress").map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onStatusChange={handleStatusChange}
                onOpenAsset={handleOpenAssetGenerator}
                onDelete={() => deleteTaskMutation.mutate(task.id)}
              />
            ))}
            {filterTasksByStatus("in_progress").length === 0 && (
              <div className="p-4 text-center text-slate-600 text-xs italic">No tasks in progress</div>
            )}
          </div>
        </div>

        {/* Column: Completed */}
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-500/20 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Completed ({filterTasksByStatus("done").length})
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[600px] pr-1">
            {filterTasksByStatus("done").map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onStatusChange={handleStatusChange}
                onOpenAsset={handleOpenAssetGenerator}
                onDelete={() => deleteTaskMutation.mutate(task.id)}
              />
            ))}
            {filterTasksByStatus("done").length === 0 && (
              <div className="p-4 text-center text-slate-600 text-xs italic">No completed tasks yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Send Review Request Modal */}
      {showReviewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">⭐ Send Review Request Email</h3>
            <p className="text-xs text-slate-400 mb-4">
              Sends an honest review invitation email to an active customer with direct links to G2 or Capterra.
            </p>

            <form onSubmit={handleSendReview} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Customer Email
                </label>
                <input
                  type="email"
                  value={reviewEmail}
                  onChange={(e) => setReviewEmail(e.target.value)}
                  placeholder="client@agency.com"
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Review Platform
                </label>
                <select
                  value={reviewPlatform}
                  onChange={(e) => setReviewPlatform(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                >
                  <option value="g2">G2 Crowd</option>
                  <option value="capterra">Capterra / Gartner</option>
                </select>
              </div>

              {reviewMsg && (
                <div className="text-xs p-2 rounded bg-slate-800 text-cyan-300">
                  {reviewMsg}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowReviewModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sendReviewMutation.isPending}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-gradient-to-r from-cyan-400 to-teal-300 hover:brightness-110"
                >
                  {sendReviewMutation.isPending ? "Sending..." : "Send Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Asset Generator Modal */}
      {activeAssetTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div>
                <span className="text-[10px] uppercase font-bold text-cyan-400 tracking-wider">
                  {activeAssetTask.platform.replace("_", " ")} Assets
                </span>
                <h3 className="text-base font-bold text-white">{activeAssetTask.title}</h3>
              </div>
              <button
                onClick={() => {
                  setActiveAssetTask(null);
                  setGeneratedAssets(null);
                }}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {generatedAssets ? (
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60 space-y-3">
                  {Object.entries(generatedAssets).map(([key, val]) => (
                    <div key={key}>
                      <div className="font-bold text-slate-300 uppercase tracking-wider text-[10px] mb-1">
                        {key.replace(/_/g, " ")}:
                      </div>
                      {typeof val === "string" ? (
                        <div className="p-2.5 rounded bg-slate-900 border border-slate-800 text-slate-200 whitespace-pre-line font-mono text-[11px]">
                          {val}
                        </div>
                      ) : (
                        <pre className="p-2.5 rounded bg-slate-900 border border-slate-800 text-slate-200 overflow-x-auto text-[11px]">
                          {JSON.stringify(val, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-400">Loading AI assets...</div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-slate-800 mt-6">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(generatedAssets, null, 2));
                  alert("Copied assets to clipboard!");
                }}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700"
              >
                Copy All Assets
              </button>
              <button
                onClick={() => {
                  setActiveAssetTask(null);
                  setGeneratedAssets(null);
                }}
                className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-cyan-400 hover:brightness-110"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Task Modal */}
      {showNewTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-2">Create Custom Launch Task</h3>
            <form onSubmit={handleCreateTask} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Platform</label>
                <select
                  value={newTaskPlatform}
                  onChange={(e) => setNewTaskPlatform(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                >
                  <option value="product_hunt">Product Hunt</option>
                  <option value="g2">G2 Crowd</option>
                  <option value="capterra">Capterra</option>
                  <option value="reddit">Reddit</option>
                  <option value="indiehackers">IndieHackers</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Title</label>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="e.g. Schedule launch morning AMA"
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                <textarea
                  value={newTaskDesc}
                  onChange={(e) => setNewTaskDesc(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-xs text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowNewTaskModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTaskMutation.isPending}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-950 bg-cyan-400 hover:brightness-110"
                >
                  Add Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function TaskCard({
  task,
  onStatusChange,
  onOpenAsset,
  onDelete,
}: {
  task: LaunchTaskItem;
  onStatusChange: (task: LaunchTaskItem, newStatus: string) => void;
  onOpenAsset: (task: LaunchTaskItem) => void;
  onDelete: () => void;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm hover:border-slate-700 transition-colors space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-cyan-300">
          {task.platform.replace("_", " ")}
        </span>
        <select
          value={task.status}
          onChange={(e) => onStatusChange(task, e.target.value)}
          className="text-[10px] font-semibold bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-slate-300"
        >
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="done">Done</option>
        </select>
      </div>

      <h4 className="text-xs font-bold text-white leading-snug">{task.title}</h4>

      {task.description && (
        <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
          {task.description}
        </p>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
        <button
          onClick={() => onOpenAsset(task)}
          className="text-[11px] text-cyan-400 hover:underline font-medium flex items-center gap-1"
        >
          ✨ View / Generate Assets
        </button>
        <button
          onClick={onDelete}
          className="text-[10px] text-slate-600 hover:text-rose-400 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
