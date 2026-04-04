import React from "react";
import multiavatar from "@multiavatar/multiavatar";
import { Plane, AlertTriangle } from "lucide-react";
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

interface ResponseCardCompactProps {
  r: AgentResponse;
  onClick: () => void;
}

export function ResponseCardCompact({ r, onClick }: ResponseCardCompactProps) {
  const color = emotionColor(r.emotional_state);
  const previewText = r.action || r.thoughts || "No content";

  return (
    <button
      onClick={onClick}
      className="group relative cursor-pointer rounded-lg border bg-white/[0.03] hover:bg-white/[0.06] hover:border-[#FE6B36]/40 transition-all duration-200 p-2.5 space-y-2 overflow-hidden h-full flex flex-col text-left"
      style={{ borderColor: `${color}25` }}
    >
      {/* Icon + Name */}
      <div className="flex items-center gap-2 min-w-0">
        <img
          src={`data:image/svg+xml;utf8,${encodeURIComponent(
            multiavatar(r.agent_id),
          )}`}
          alt={r.agent_name}
          className="w-6 h-6 rounded-full border shrink-0"
          style={{ borderColor: `${color}60` }}
        />
        <div className="min-w-0 flex-1 flex items-center gap-1">
          <p className="font-bold text-[10px] text-white truncate flex-1">
            {r.agent_name}
          </p>
          <div className="ml-auto min-w-0 flex items-center gap-1 overflow-hidden">
            {r.is_migrating === 1 && (
              <span className="text-[8px] px-1 py-0.5 rounded bg-purple-500/20 text-purple-400 shrink-0 border border-purple-500/30">
                <Plane className="w-2 h-2 inline" />
              </span>
            )}
            {r.is_less_trusting === 1 && (
              <span className="text-[8px] px-1 py-0.5 rounded bg-red-500/20 text-red-400 shrink-0 border border-red-500/30">
                <AlertTriangle className="w-2 h-2 inline" />
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Text preview in rectangle */}
      <div className="flex-1 min-h-0">
        <p className="text-[9px] text-white/60 line-clamp-2 italic bg-white/2 rounded-md p-1.5 border border-white/5 [overflow-wrap:anywhere]">
          {previewText}
        </p>
      </div>

      {/* View More button */}
      <button
        className="w-full text-[8px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-[#FE6B36]/20 text-[#FE6B36] hover:bg-[#FE6B36]/30 transition-colors border border-[#FE6B36]/30"
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        View More
      </button>
    </button>
  );
}
