import React from "react";
import multiavatar from "@multiavatar/multiavatar";
import {
  Plane,
  MessageSquare,
  Zap,
  ClipboardList,
  Search,
  TrendingUp,
  BarChart2,
  AlertTriangle,
  Grid3x3,
  Columns,
} from "lucide-react";
import { API_BASE } from "@/lib/api";
import { ResponseCardCompact } from "./ResponseCardCompact";
import { ResponseCardVertical } from "./ResponseCardVertical";
import { CollapsibleSection } from "./CollapsibleSection";

const API = API_BASE;

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SimRun {
  run_id: string;
  event_name: string;
  year: number;
  cycles: number;
  agent_count: number;
  status: "running" | "completed";
  started_at: string;
  completed_at?: string;
}

export interface AgentResponse {
  id: number;
  run_id: string;
  agent_id: string;
  agent_name: string;
  agent_role: string;
  agent_region: string;
  cycle: number;
  thoughts: string;
  emotional_state: string;
  action: string;
  plan: string;
  migration_intent: string;
  trust_shift: string;
  trust_change: "increase" | "decrease" | "none" | string;
  trust_target?: string;
  is_less_trusting: number;
  is_migrating: number;
  migration_destination?: string;
  raw_response: string;
  timestamp: string;
  _score?: number;
}

interface CycleEvolution {
  cycle: number;
  agent_count: number;
  migrating_count: number;
  less_trusting_count: number;
  emotions?: string;
  emotion_breakdown?: Record<string, number>;
  regions?: string;
}

interface DashboardStats {
  total_runs: number;
  completed_runs: number;
  total_responses_estimate: number;
  search_index_size: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

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

function emotionTagLabel(e: string) {
  const cleaned = (e ?? "").replace(/\*\*/g, "").trim();
  const explicit = cleaned.match(/emotion\s*:\s*([^\n.!?]+)/i)?.[1]?.trim();
  if (explicit) return explicit;
  const firstLine = cleaned.split("\n")[0]?.trim() ?? "";
  const firstSentence = firstLine.split(/[.!?]/)[0]?.trim() ?? "";
  return firstSentence || "unknown";
}

function sanitizeResponseText(value?: string | null) {
  if (!value) return "";

  let cleaned = value.trim();

  // Strip leading/trailing quote marks that commonly appear in model output.
  cleaned = cleaned.replace(/^["'`“”‘’]+/, "");
  cleaned = cleaned.replace(/["'`“”‘’]+$/, "");

  // Strip dangling markdown markers from string edges.
  cleaned = cleaned.replace(/^[*_~`]+/, "");
  cleaned = cleaned.replace(/[*_~`]+$/, "");

  // Remove common markdown artifacts while preserving readable text.
  cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, "$1");
  cleaned = cleaned.replace(/__(.*?)__/g, "$1");
  cleaned = cleaned.replace(/\*(.*?)\*/g, "$1");
  cleaned = cleaned.replace(/_(.*?)_/g, "$1");
  cleaned = cleaned.replace(/`{1,3}([^`]+)`{1,3}/g, "$1");
  cleaned = cleaned.replace(/\[(.*?)\]\((.*?)\)/g, "$1");
  cleaned = cleaned.replace(/^\s*>\s?/gm, "");
  cleaned = cleaned.replace(/^\s*#{1,6}\s+/gm, "");
  cleaned = cleaned.replace(/^\s*[-*+]\s+/gm, "");

  return cleaned.trim();
}

function compactLabel(value?: string | null, maxLength = 24) {
  const cleaned = sanitizeResponseText(value).replace(/\s+/g, " ").trim();
  if (!cleaned) return "unknown";
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength - 1)}…`;
}

function sanitizeTrustTarget(value?: string | null): string | undefined {
  const cleaned = sanitizeResponseText(value);
  if (!cleaned) return undefined;

  const normalized = cleaned
    .replace(/^[\s:;,.\-]+/, "")
    .replace(/[\s:;,.\-]+$/, "")
    .trim();

  if (!normalized) return undefined;
  if (/^(none|n\/a|unknown|null)$/i.test(normalized)) return undefined;
  return normalized;
}

function sanitizeAgentResponse(response: AgentResponse): AgentResponse {
  return {
    ...response,
    thoughts: sanitizeResponseText(response.thoughts),
    emotional_state: sanitizeResponseText(response.emotional_state),
    action: sanitizeResponseText(response.action),
    plan: sanitizeResponseText(response.plan),
    migration_intent: sanitizeResponseText(response.migration_intent),
    trust_shift: sanitizeResponseText(response.trust_shift),
    trust_target: sanitizeTrustTarget(response.trust_target),
  };
}

// ─── Response Card ────────────────────────────────────────────────────────────

function ResponseCard({
  r,
  onClick,
}: {
  r: AgentResponse;
  onClick: () => void;
}) {
  const color = emotionColor(r.emotional_state);
  return (
    <div
      onClick={onClick}
      className="group relative cursor-pointer rounded-xl border bg-white/[0.03] hover:bg-white/[0.06] hover:border-[#FE6B36]/40 transition-all duration-200 p-4 space-y-3 overflow-hidden"
      style={{ borderColor: `${color}25` }}
    >
      {/* Score badge */}
      {r._score !== undefined && (
        <div className="absolute top-3 right-3 text-[9px] font-mono text-white/30">
          {(r._score * 100).toFixed(0)}% match
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3">
        <img
          src={`data:image/svg+xml;utf8,${encodeURIComponent(
            multiavatar(r.agent_id),
          )}`}
          alt={r.agent_name}
          className="w-8 h-8 rounded-full border shrink-0"
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
              <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-md bg-purple-500/20 text-purple-400">
                <Plane className="w-3 h-3 inline mr-1" /> MIGRATING
                {r.migration_destination ? ` → ${r.migration_destination}` : ""}
              </span>
            )}
            {r.is_less_trusting === 1 && (
              <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-md bg-red-500/20 text-red-400">
                <AlertTriangle className="w-3 h-3 inline mr-1" /> TRUST ↓
                {r.trust_target ? ` ${r.trust_target}` : ""}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Thoughts */}
      {r.thoughts && (
        <div className="space-y-1">
          <p className="text-[9px] uppercase tracking-widest text-white/30">
            <MessageSquare className="w-2.5 h-2.5 inline mr-1" /> Thoughts
          </p>
          <p className="text-[11px] text-white/70 leading-relaxed line-clamp-3 italic [overflow-wrap:anywhere]">
            {r.thoughts}
          </p>
        </div>
      )}

      {/* Action */}
      {r.action && (
        <div className="space-y-0.5">
          <p className="text-[9px] uppercase tracking-widest text-white/30">
            <Zap className="w-2.5 h-2.5 inline mr-1" /> Action
          </p>
          <p className="text-[11px] text-[#FE6B36]/90 leading-relaxed line-clamp-2 [overflow-wrap:anywhere]">
            {r.action}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Agent Detail Modal ────────────────────────────────────────────────────────

function AgentDetailModal({
  response,
  onClose,
}: {
  response: AgentResponse;
  onClose: () => void;
}) {
  const color = emotionColor(response.emotional_state);

  return (
    <div
      className="absolute inset-0 z-[80] bg-black/80 backdrop-blur-md flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-card border rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6 space-y-5"
        style={{ borderColor: `${color}40` }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src={`data:image/svg+xml;utf8,${encodeURIComponent(
                multiavatar(response.agent_id),
              )}`}
              alt={response.agent_name}
              className="w-12 h-12 rounded-full border-2"
              style={{ borderColor: color }}
            />
            <div>
              <p className="font-black text-lg text-white font-mono">
                {response.agent_name}
              </p>
              <p className="text-[11px] text-white/50">
                {response.agent_role} · {response.agent_region}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Minimal Status Summary - Only essential info */}
        <div className="flex flex-wrap gap-2 items-center">
          {/* Trust info if applicable */}
          {response.is_less_trusting === 1 && (
            <span className="text-[10px] px-3 py-1.5 rounded-lg font-bold bg-red-500/20 text-red-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Trust Decrease
              {response.trust_target ? ` · ${response.trust_target}` : ""}
            </span>
          )}

          {/* Migrating info if applicable */}
          {response.is_migrating === 1 && (
            <span className="text-[10px] px-3 py-1.5 rounded-lg font-bold bg-purple-500/20 text-purple-400 flex items-center gap-1">
              <Plane className="w-3 h-3" />
              Migrating
              {response.migration_destination
                ? ` → ${response.migration_destination}`
                : ""}
            </span>
          )}

          {/* Emotion badge */}
          <span
            className="text-[10px] px-3 py-1.5 rounded-lg font-bold"
            style={{ backgroundColor: `${color}20`, color }}
          >
            {emotionTagLabel(response.emotional_state)}
          </span>

          {/* Cycle badge - colored block */}
          <span className="text-[10px] px-3 py-1.5 rounded-lg bg-[#FE6B36]/30 text-[#FE6B36] font-bold font-mono">
            Cycle {response.cycle}
          </span>
        </div>

        {/* Collapsible Sections for detailed content */}
        <div className="space-y-2 pt-2">
          <p className="text-[9px] uppercase tracking-widest text-white/30">
            Detailed Response — Click to expand
          </p>
          <div className="space-y-3">
            <CollapsibleSection
              id="emotion"
              label={
                <>
                  <AlertTriangle className="w-3 h-3 inline mr-1" /> Emotional
                  State
                </>
              }
              value={response.emotional_state}
              color="#fb923c"
              defaultOpen={false}
            />
            <CollapsibleSection
              id="thoughts"
              label={
                <>
                  <MessageSquare className="w-3 h-3 inline mr-1" /> Inner
                  Thoughts
                </>
              }
              value={response.thoughts}
              color="#a5b4fc"
              defaultOpen={false}
            />
            <CollapsibleSection
              id="action"
              label={
                <>
                  <Zap className="w-3 h-3 inline mr-1" /> Immediate Action
                </>
              }
              value={response.action}
              color="#FE6B36"
              defaultOpen={false}
            />
            <CollapsibleSection
              id="plan"
              label={
                <>
                  <ClipboardList className="w-3 h-3 inline mr-1" /> Plan
                </>
              }
              value={response.plan}
              color="#22c55e"
              defaultOpen={false}
            />
            <CollapsibleSection
              id="migration"
              label={
                <>
                  <Plane className="w-3 h-3 inline mr-1" /> Migration Intent
                </>
              }
              value={response.migration_intent}
              color="#a855f7"
              defaultOpen={false}
            />
            <CollapsibleSection
              id="trust"
              label={
                <>
                  <AlertTriangle className="w-3 h-3 inline mr-1" /> Trust Shift
                </>
              }
              value={response.trust_shift}
              color="#f87171"
              defaultOpen={false}
            />
          </div>
        </div>

        <p className="text-[9px] text-white/20 font-mono border-t border-white/5 pt-3">
          {new Date(response.timestamp).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

// ─── Evolution Timeline ───────────────────────────────────────────────────────

function EvolutionTimeline({
  cycles,
  totalAgents,
}: {
  cycles: CycleEvolution[];
  totalAgents: number;
}) {
  if (!cycles.length) return null;
  const cycleWord = cycles.length === 1 ? "Cycle" : "Cycles";

  return (
    <div className="space-y-3">
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-white/40">
        <TrendingUp className="w-3 h-3 inline mr-1" /> Event Evolution —{" "}
        {cycles.length} {cycleWord}
      </h3>
      <div className="overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex gap-3 min-w-max">
          {cycles.map((c) => {
            const migPct =
              totalAgents > 0 ? (c.migrating_count / totalAgents) * 100 : 0;
            const trustDropPct =
              totalAgents > 0 ? (c.less_trusting_count / totalAgents) * 100 : 0;
            const topEmotions = Object.entries(c.emotion_breakdown ?? {}).slice(
              0,
              3,
            );

            return (
              <div
                key={c.cycle}
                className="w-[18rem] shrink-0 bg-white/[0.03] rounded-xl border border-white/10 p-3 space-y-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div
                      className="w-7 h-7 rounded-full border-2 flex items-center justify-center text-[10px] font-black"
                      style={{
                        borderColor: "#FE6B36",
                        color: "#FE6B36",
                        backgroundColor: "#FE6B361A",
                      }}
                    >
                      {c.cycle}
                    </div>
                    <p className="text-[10px] font-bold text-white/60 uppercase tracking-widest whitespace-nowrap">
                      Cycle {c.cycle}
                    </p>
                  </div>
                  <span className="text-[9px] text-white/45 font-mono whitespace-nowrap shrink-0">
                    {c.agent_count} agents
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-1.5 text-[9px] font-mono leading-tight">
                  {c.migrating_count > 0 && (
                    <div
                      className="text-purple-400 truncate"
                      title={`${c.migrating_count} migrating (${migPct.toFixed(0)}%)`}
                    >
                      <Plane className="w-2 h-2 inline mr-1.5" />
                      {c.migrating_count} migrating ({migPct.toFixed(0)}%)
                    </div>
                  )}
                  {c.less_trusting_count > 0 && (
                    <div
                      className="text-red-400 truncate"
                      title={`${
                        c.less_trusting_count
                      } trust decrease (${trustDropPct.toFixed(0)}%)`}
                    >
                      <AlertTriangle className="w-2 h-2 inline mr-1.5" />
                      {c.less_trusting_count} trust drop (
                      {trustDropPct.toFixed(0)}%)
                    </div>
                  )}
                </div>

                {/* Emotion bars */}
                {topEmotions.length > 0 && (
                  <div className="space-y-1.5">
                    {topEmotions.map(([emotion, count]) => {
                      const pct =
                        c.agent_count > 0 ? (count / c.agent_count) * 100 : 0;
                      const col = emotionColor(emotion);
                      const fullLabel = sanitizeResponseText(emotion);
                      const shortLabel = compactLabel(fullLabel, 18);
                      return (
                        <div
                          key={emotion}
                          className="grid grid-cols-[5.25rem,1fr,2rem] gap-2 items-center min-w-0"
                        >
                          <span
                            className="block text-[9px] truncate whitespace-nowrap overflow-hidden"
                            style={{ color: col }}
                            title={fullLabel}
                          >
                            {shortLabel}
                          </span>
                          <div className="min-w-0 h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-700"
                              style={{ width: `${pct}%`, backgroundColor: col }}
                            />
                          </div>
                          <span className="text-[9px] text-white/25 w-8 text-right font-mono justify-self-end">
                            {pct.toFixed(0)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard Component ─────────────────────────────────────────────────

interface EventDashboardProps {
  onClose: () => void;
}

export function EventDashboard({ onClose }: EventDashboardProps) {
  const [stats, setStats] = React.useState<DashboardStats | null>(null);
  const [runs, setRuns] = React.useState<SimRun[]>([]);
  const [selectedRun, setSelectedRun] = React.useState<SimRun | null>(null);
  const [responses, setResponses] = React.useState<AgentResponse[]>([]);
  const [evolution, setEvolution] = React.useState<CycleEvolution[]>([]);
  const [selectedResponse, setSelectedResponse] =
    React.useState<AgentResponse | null>(null);

  // Layout mode state - persisted to localStorage
  const [layoutMode, setLayoutModeState] = React.useState<
    "default" | "compact" | "vertical"
  >("default");

  // Setter with localStorage persistence
  const setLayoutMode = (mode: "default" | "compact" | "vertical") => {
    setLayoutModeState(mode);
    localStorage.setItem("dashboardLayoutMode", mode);
  };

  // Load layout mode from localStorage on mount
  React.useEffect(() => {
    const saved = localStorage.getItem("dashboardLayoutMode") as
      | "default"
      | "compact"
      | "vertical"
      | null;
    if (saved && ["default", "compact", "vertical"].includes(saved)) {
      setLayoutModeState(saved);
    }
  }, []);

  // Search / filter state
  const [searchQuery, setSearchQuery] = React.useState("");
  const [searchMode, setSearchMode] = React.useState<
    "semantic" | "fuzzy" | "hybrid"
  >("hybrid");
  const [filterCycle, setFilterCycle] = React.useState<number | null>(null);
  const [filterRegion, setFilterRegion] = React.useState("");
  const [migratingOnly, setMigratingOnly] = React.useState(false);
  const [lessTrustingOnly, setLessTrustingOnly] = React.useState(false);

  const [loadingRuns, setLoadingRuns] = React.useState(true);
  const [loadingResponses, setLoadingResponses] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [totalPages, setTotalPages] = React.useState(1);
  const [totalResponses, setTotalResponses] = React.useState(0);

  const searchTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // Load stats + runs on mount
  React.useEffect(() => {
    Promise.all([
      fetch(`${API}/api/dashboard/stats`).then((r) => r.json()),
      fetch(`${API}/api/dashboard/runs`).then((r) => r.json()),
    ])
      .then(([s, r]) => {
        setStats(s);
        const runList: SimRun[] = r.runs ?? [];
        setRuns(runList);
        if (runList.length > 0) setSelectedRun(runList[0]);
      })
      .catch(console.error)
      .finally(() => setLoadingRuns(false));
  }, []);

  // Load responses + evolution when run or filters change
  React.useEffect(() => {
    if (!selectedRun) return;
    loadResponses(1);
    loadEvolution();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRun, filterCycle, filterRegion, migratingOnly, lessTrustingOnly]);

  // Debounced search
  React.useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      if (selectedRun) loadResponses(1);
    }, 400);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, searchMode]);

  async function loadResponses(p: number) {
    if (!selectedRun) return;
    setLoadingResponses(true);
    setPage(p);
    try {
      const params = new URLSearchParams({
        page: String(p),
        per_page: "50",
        ...(filterCycle !== null ? { cycle: String(filterCycle) } : {}),
        ...(filterRegion ? { region: filterRegion } : {}),
        ...(migratingOnly ? { migrating_only: "true" } : {}),
        ...(lessTrustingOnly ? { less_trusting_only: "true" } : {}),
        ...(searchQuery.trim() ? { q: searchQuery.trim() } : {}),
      });
      const res = await fetch(
        `${API}/api/dashboard/runs/${selectedRun.run_id}/responses?${params}`,
      );
      const data = await res.json();
      const cleanedResponses: AgentResponse[] = (data.responses ?? []).map(
        (response: AgentResponse) => sanitizeAgentResponse(response),
      );
      setResponses(cleanedResponses);
      setTotalPages(data.pages ?? 1);
      setTotalResponses(data.total ?? 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingResponses(false);
    }
  }

  async function loadEvolution() {
    if (!selectedRun) return;
    try {
      const res = await fetch(
        `${API}/api/dashboard/runs/${selectedRun.run_id}/evolution`,
      );
      const data = await res.json();
      setEvolution(data.cycles ?? []);
    } catch (e) {
      console.error(e);
    }
  }

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="w-full h-full bg-background flex flex-col font-mono overflow-hidden relative">
      {/* ── Body ── */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* ── Sidebar: Run List ── */}
        <aside className="w-48 sm:w-56 md:w-64 border-r border-white/[0.07] flex flex-col overflow-hidden bg-black/30 shrink-0">
          <div className="px-4 py-3 border-b border-white/[0.07]">
            <p className="text-[9px] uppercase tracking-widest text-white/30">
              Simulation Runs
            </p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loadingRuns ? (
              <div className="flex items-center justify-center h-32">
                <div className="w-5 h-5 border-2 border-[#FE6B36] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : runs.length === 0 ? (
              <div className="p-4 text-center">
                <p className="text-[10px] text-white/30">
                  No simulation runs yet.
                </p>
                <p className="text-[9px] text-white/20 mt-1">
                  Trigger a God Mode event to start.
                </p>
              </div>
            ) : (
              runs.map((run) => (
                <button
                  key={run.run_id}
                  onClick={() => {
                    setSelectedRun(run);
                    setSearchQuery("");
                    setFilterCycle(null);
                    setFilterRegion("");
                    setMigratingOnly(false);
                    setLessTrustingOnly(false);
                  }}
                  className={`w-full text-left p-4 border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors ${
                    selectedRun?.run_id === run.run_id
                      ? "bg-[#FE6B36]/10 border-l-2 border-l-[#FE6B36]"
                      : ""
                  }`}
                >
                  <p className="text-[11px] font-bold text-white truncate">
                    {run.event_name}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-[8px] uppercase tracking-widest px-1 py-0.5 rounded ${
                        run.status === "completed"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }`}
                    >
                      {run.status}
                    </span>
                    <span className="text-[9px] text-white/30">{run.year}</span>
                  </div>
                  <div className="flex items-center justify-between mt-1.5 text-[9px] text-white/25">
                    <span>
                      {run.agent_count} agents · {run.cycles} cycles
                    </span>
                    <span>{timeAgo(run.started_at)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* ── Main Content ── */}
        {selectedRun ? (
          <div className="flex-1 min-h-0 overflow-y-auto [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-[#FE6B36]/80 [&::-webkit-scrollbar-thumb]:rounded-full">
            {/* Run header */}
            <div className="px-6 py-4 border-b border-white/[0.07] bg-black/20">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-black text-white">
                    {selectedRun.event_name}
                  </h2>
                  <p className="text-[10px] text-white/40 mt-0.5">
                    Year {selectedRun.year} · {selectedRun.cycles} cycles ·{" "}
                    {selectedRun.agent_count} agents
                    {selectedRun.started_at &&
                      ` · Started ${timeAgo(selectedRun.started_at)}`}
                  </p>
                </div>
                <span
                  className={`text-[9px] px-2 py-1 rounded-full uppercase tracking-widest font-bold ${
                    selectedRun.status === "completed"
                      ? "bg-green-500/20 text-green-400"
                      : "bg-yellow-500/20 text-yellow-400 animate-pulse"
                  }`}
                >
                  {selectedRun.status}
                </span>
              </div>

              {evolution.length > 0 && (
                <div className="mt-4">
                  <EvolutionTimeline
                    cycles={evolution}
                    totalAgents={selectedRun.agent_count}
                  />
                </div>
              )}

              <div className="sticky top-0 z-20 mt-4 -mx-6 px-6 py-3 bg-black/90 backdrop-blur-md border-y border-white/[0.07]">
                {/* Search + Filters + Layout Toggle */}
                <div className="flex gap-3 flex-wrap items-center">
                  {/* Search input */}
                  <div className="flex-1 min-w-[200px] relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 flex items-center justify-center">
                      <Search className="w-3.5 h-3.5" />
                    </span>
                    <input
                      type="text"
                      placeholder="Search responses... (e.g. 'afraid', 'flee', 'bomb')"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-4 py-2 bg-white/[0.04] border border-white/10 focus:border-[#FE6B36]/50 rounded-lg text-[11px] text-white placeholder:text-white/25 outline-none transition-colors"
                    />
                  </div>

                  {/* Search mode */}
                  <div className="flex rounded-lg overflow-hidden border border-white/10">
                    {(["hybrid", "semantic", "fuzzy"] as const).map((m) => (
                      <button
                        key={m}
                        onClick={() => setSearchMode(m)}
                        className={`px-3 py-2 text-[9px] uppercase tracking-widest transition-colors ${
                          searchMode === m
                            ? "bg-[#FE6B36] text-white"
                            : "text-white/40 hover:text-white hover:bg-white/5"
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>

                  {/* Layout Mode Toggle */}
                  <div className="flex rounded-lg overflow-hidden border border-white/10">
                    <button
                      onClick={() => setLayoutMode("default")}
                      className={`px-3 py-2 text-[9px] uppercase tracking-widest transition-colors flex items-center gap-1 ${
                        layoutMode === "default"
                          ? "bg-[#FE6B36] text-white"
                          : "text-white/40 hover:text-white hover:bg-white/5"
                      }`}
                      title="Default layout"
                    >
                      ◻◻ Default
                    </button>
                    <button
                      onClick={() => setLayoutMode("compact")}
                      className={`px-3 py-2 text-[9px] uppercase tracking-widest transition-colors flex items-center gap-1 border-l ${
                        layoutMode === "compact"
                          ? "bg-[#FE6B36] text-white border-l-[#FE6B36]"
                          : "text-white/40 border-l-white/10 hover:text-white hover:bg-white/5"
                      }`}
                      title="Compact grid layout"
                    >
                      <Grid3x3 className="w-3 h-3" /> Compact
                    </button>
                    <button
                      onClick={() => setLayoutMode("vertical")}
                      className={`px-3 py-2 text-[9px] uppercase tracking-widest transition-colors flex items-center gap-1 border-l ${
                        layoutMode === "vertical"
                          ? "bg-[#FE6B36] text-white border-l-[#FE6B36]"
                          : "text-white/40 border-l-white/10 hover:text-white hover:bg-white/5"
                      }`}
                      title="Vertical layout"
                    >
                      <Columns className="w-3 h-3" /> Vertical
                    </button>
                  </div>
                </div>

                {/* Cycle filter + other filters - next line with top spacing */}
                <div className="flex gap-3 flex-wrap mt-3">
                  {/* Cycle filter */}
                  <select
                    value={filterCycle ?? ""}
                    onChange={(e) =>
                      setFilterCycle(
                        e.target.value ? Number(e.target.value) : null,
                      )
                    }
                    className="px-3 py-2 bg-white/[0.04] border border-white/10 rounded-lg text-[11px] text-white/60 outline-none"
                  >
                    <option value="">All Cycles</option>
                    {Array.from(
                      { length: selectedRun.cycles },
                      (_, i) => i + 1,
                    ).map((c) => (
                      <option key={c} value={c}>
                        Cycle {c}
                      </option>
                    ))}
                  </select>

                  {/* Migrating filter */}
                  <button
                    onClick={() => setMigratingOnly((p) => !p)}
                    className={`px-3 py-2 rounded-lg text-[9px] uppercase tracking-widest border transition-colors flex items-center ${
                      migratingOnly
                        ? "bg-purple-500/20 border-purple-500/50 text-purple-400"
                        : "border-white/10 text-white/40 hover:border-white/20"
                    }`}
                  >
                    <Plane className="w-3 h-3 mr-1.5" /> Migrating Only
                  </button>

                  <button
                    onClick={() => setLessTrustingOnly((p) => !p)}
                    className={`px-3 py-2 rounded-lg text-[9px] uppercase tracking-widest border transition-colors flex items-center ${
                      lessTrustingOnly
                        ? "bg-red-500/20 border-red-500/50 text-red-400"
                        : "border-white/10 text-white/40 hover:border-white/20"
                    }`}
                  >
                    <AlertTriangle className="w-3 h-3 mr-1.5" /> Trust Drop Only
                  </button>
                </div>

                {/* Result count */}
                {!loadingResponses && (
                  <p className="text-[9px] text-white/25 mt-2">
                    {searchQuery
                      ? `${totalResponses} results for "${searchQuery}" · `
                      : `${totalResponses} responses · `}
                    Page {page} of {totalPages}
                  </p>
                )}
              </div>
            </div>

            {/* ── Content Area ── */}
            <div className="p-4 space-y-3">
              {loadingResponses ? (
                <div className="flex items-center justify-center h-32">
                  <div className="w-5 h-5 border-2 border-[#FE6B36] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : responses.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 gap-2">
                  <p className="text-[10px] text-white/30">
                    No responses found
                  </p>
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="text-[9px] text-[#FE6B36]/60 hover:text-[#FE6B36] underline"
                    >
                      Clear search
                    </button>
                  )}
                </div>
              ) : (
                <>
                  {/* Render grid based on layout mode */}
                  {layoutMode === "default" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {responses.map((r) => (
                        <ResponseCard
                          key={r.id}
                          r={r}
                          onClick={() => setSelectedResponse(r)}
                        />
                      ))}
                    </div>
                  )}

                  {layoutMode === "compact" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {responses.map((r) => (
                        <ResponseCardCompact
                          key={r.id}
                          r={r}
                          onClick={() => setSelectedResponse(r)}
                        />
                      ))}
                    </div>
                  )}

                  {layoutMode === "vertical" && (
                    <div className="grid grid-cols-1 gap-3">
                      {responses.map((r) => (
                        <ResponseCardVertical
                          key={r.id}
                          r={r}
                          onClick={() => setSelectedResponse(r)}
                        />
                      ))}
                    </div>
                  )}

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-3 pt-4">
                      <button
                        disabled={page <= 1}
                        onClick={() => loadResponses(page - 1)}
                        className="px-4 py-2 text-[10px] border border-white/10 rounded-lg text-white/40 hover:text-white hover:border-white/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        ← Prev
                      </button>
                      <span className="text-[10px] text-white/40 font-mono">
                        {page} / {totalPages}
                      </span>
                      <button
                        disabled={page >= totalPages}
                        onClick={() => loadResponses(page + 1)}
                        className="px-4 py-2 text-[10px] border border-white/10 rounded-lg text-white/40 hover:text-white hover:border-white/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        Next →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <BarChart2 className="w-12 h-12 text-white/20 mx-auto" />
              <p className="text-[12px] text-white/40">
                Select a simulation run from the sidebar
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Agent Detail Modal */}
      {selectedResponse && (
        <AgentDetailModal
          response={selectedResponse}
          onClose={() => setSelectedResponse(null)}
        />
      )}
    </div>
  );
}
