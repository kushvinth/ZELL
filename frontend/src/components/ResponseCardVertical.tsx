import React from "react";
import multiavatar from "@multiavatar/multiavatar";
import { MessageSquare, Zap, Plane, AlertTriangle } from "lucide-react";
import { AgentResponse } from "./EventDashboard";

const EMOTION_COLORS: Record<string, string> = {
  fearful: "#ef4444",
  afraid: "#ef4444",
  terrified: "#ef4444",
  anxious: "#f59e0b",
  worried: "#f59e0b",
  tense: "#f59e0b",
  angry: "#f97316",
  furious: "#f97316",
  outraged: "#f97316",
  sad: "#6366f1",
  grief: "#6366f1",
  devastated: "#6366f1",
  hopeful: "#22c55e",
  optimistic: "#22c55e",
  relieved: "#22c55e",
  neutral: "#6b7280",
  uncertain: "#9ca3af",
  confused: "#9ca3af",
  determined: "#3b82f6",
  resolute: "#3b82f6",
  steadfast: "#3b82f6",
  displaced: "#a855f7",
  homeless: "#a855f7",
};

function emotionColor(e: string) {
  const key = e?.toLowerCase().split(/[,\s]/)[0] ?? "";
  return EMOTION_COLORS[key] ?? "#FE6B36";
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

interface ResponseCardVerticalProps {
  r: AgentResponse;
  onClick: () => void;
}

export function ResponseCardVertical({
  r,
  onClick,
}: ResponseCardVerticalProps) {
  const color = emotionColor(r.emotional_state);
  const previewText = r.action || r.thoughts || "No content";

  return (
    <button
      onClick={onClick}
      className="group relative w-full cursor-pointer rounded-xl border bg-white/[0.03] hover:bg-white/[0.06] hover:border-[#FE6B36]/40 transition-all duration-200 p-4 space-y-3 overflow-hidden text-left"
      style={{ borderColor: `${color}25` }}
    >
      {/* Header: Icon + Info */}
      <div className="flex items-start gap-3">
        <img
          src={`data:image/svg+xml;utf8,${encodeURIComponent(
            multiavatar(r.agent_id),
          )}`}
          alt={r.agent_name}
          className="w-10 h-10 rounded-full border shrink-0"
          style={{ borderColor: `${color}60` }}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-bold text-sm text-white font-mono truncate flex-1">
              {r.agent_name}
            </span>
            <div className="text-[10px] text-white/45 min-w-0 max-w-[68%] flex items-center gap-1 ml-auto overflow-hidden">
              <span className="truncate max-w-[38%]">{r.agent_role}</span>
              <span className="text-white/30">·</span>
              <span className="truncate max-w-[30%]">{r.agent_region}</span>
              <span className="text-white/30">·</span>
              <span className="whitespace-nowrap">Cycle {r.cycle}</span>
              <span className="text-white/30">·</span>
              <span className="whitespace-nowrap">{timeAgo(r.timestamp)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {r.is_migrating === 1 && (
              <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-purple-500/20 text-purple-400">
                <Plane className="w-3 h-3 inline mr-1" /> Migrating
                {r.migration_destination ? ` → ${r.migration_destination}` : ""}
              </span>
            )}
            {r.is_less_trusting === 1 && (
              <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-red-500/20 text-red-400">
                <AlertTriangle className="w-3 h-3 inline mr-1" /> Trust ↓
                {r.trust_target ? ` ${r.trust_target}` : ""}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Content preview in rectangle */}
      <div className="space-y-2 max-w-full">
        <div className="flex items-center gap-2">
          {r.action ? (
            <Zap className="w-3 h-3 text-[#FE6B36]" />
          ) : (
            <MessageSquare className="w-3 h-3 text-indigo-400" />
          )}
          <span className="text-[10px] font-bold uppercase tracking-widest text-white/50">
            Preview
          </span>
        </div>
        <p className="text-[11px] text-white/70 bg-white/2 rounded-lg p-3 border border-white/5 leading-relaxed line-clamp-3 italic [overflow-wrap:anywhere]">
          {previewText}
        </p>
      </div>

      {/* Footer with timestamp and View More button */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/5">
        <button
          className="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded bg-[#FE6B36]/20 text-[#FE6B36] hover:bg-[#FE6B36]/30 transition-colors border border-[#FE6B36]/30"
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
        >
          View More
        </button>
      </div>
    </button>
  );
}
