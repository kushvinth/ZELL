import React from "react";
import multiavatar from "@multiavatar/multiavatar";
import {
  Orbit,
  Contact,
  MessageSquare,
  Brain,
  Briefcase,
  Flame,
  CheckCircle2,
  BarChart2,
  Zap,
  ScrollText,
  Activity,
  MapPin,
  Network,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
} from "lucide-react";
import { WorldMap } from "./components/WorldMap";
import { ControlPanel } from "./components/ControlPanel";
import { EventDashboard } from "./components/EventDashboard";
import { AtlasView } from "./components/AtlasView";
import {
  fetchBootstrap,
  fetchAgents,
  spawnAgentsBatch,
  getBatchStatus,
  fetchSystemStats,
  getAgentPersona,
  API_BASE,
} from "./lib/api";

interface Agent {
  id: string;
  name: string;
  age: number;
  race: string;
  soul_type: "aggressive" | "altruistic" | "technocratic" | "hedonistic";
  traits: Record<string, number>;
  bio?: string;
  location: [number, number];
  city: string;
  roleLabel?: string;
  roleValue?: string;
}

const SOUL_COLORS: Record<string, string> = {
  aggressive: "#ef4444", // Red-Orange
  altruistic: "#06b6d4", // Cyan (Kindness)
  technocratic: "#a855f7", // Purple (Intelligence)
  hedonistic: "#f59e0b", // Amber (Pleasure)
};

const SOUL_TYPES = [
  "aggressive",
  "altruistic",
  "technocratic",
  "hedonistic",
] as const;

const SOUL_CONFIG_PANEL: Record<
  string,
  { color: string; icon: React.ReactNode }
> = {
  SOUL: { color: "#a855f7", icon: <Orbit className="w-3 h-3 inline mr-1" /> },
  IDENTITY: {
    color: "#06b6d4",
    icon: <Contact className="w-3 h-3 inline mr-1" />,
  },
  VOICE: {
    color: "#f59e0b",
    icon: <MessageSquare className="w-3 h-3 inline mr-1" />,
  },
  BRAIN: { color: "#3b82f6", icon: <Brain className="w-3 h-3 inline mr-1" /> },
  WORK: {
    color: "#22c55e",
    icon: <Briefcase className="w-3 h-3 inline mr-1" />,
  },
  DRIVES: { color: "#FE6B36", icon: <Flame className="w-3 h-3 inline mr-1" /> },
};

/** Lightweight inline markdown renderer — no external deps */
function renderMarkdown(text: string): React.ReactNode[] {
  return text.split("\n").map((line, i) => {
    // Strip leading/trailing whitespace
    const trimmed = line.trim();
    if (!trimmed) return <div key={i} className="h-2" />;

    // ### Heading 3
    if (trimmed.startsWith("### ")) {
      return (
        <p
          key={i}
          className="text-[11px] font-bold text-white/80 uppercase tracking-widest mt-3 mb-1"
        >
          {trimmed.slice(4)}
        </p>
      );
    }
    // ## Heading 2
    if (trimmed.startsWith("## ")) {
      return (
        <p
          key={i}
          className="text-[12px] font-bold text-[#FE6B36] uppercase tracking-wider mt-3 mb-1 border-b border-[#FE6B36]/20 pb-1"
        >
          {trimmed.slice(3)}
        </p>
      );
    }
    // # Heading 1
    if (trimmed.startsWith("# ")) {
      return (
        <p
          key={i}
          className="text-[13px] font-black text-[#FE6B36] uppercase tracking-widest mt-2 mb-2"
        >
          {trimmed.slice(2)}
        </p>
      );
    }
    // Bullet points
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      return (
        <div key={i} className="flex gap-2 ml-2">
          <span className="text-[#FE6B36]/60 mt-0.5 shrink-0">▸</span>
          <p className="text-[11px] text-white/60 leading-relaxed">
            {inlineMarkdown(trimmed.slice(2))}
          </p>
        </div>
      );
    }
    // Normal paragraph line
    return (
      <p key={i} className="text-[11px] text-white/60 leading-relaxed">
        {inlineMarkdown(trimmed)}
      </p>
    );
  });
}

/** Handle **bold** and *italic* inline */
function inlineMarkdown(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[2])
      parts.push(
        <strong key={match.index} className="text-white/90 font-bold">
          {match[2]}
        </strong>,
      );
    else if (match[3])
      parts.push(
        <em key={match.index} className="text-white/70 italic">
          {match[3]}
        </em>,
      );
    else if (match[4])
      parts.push(
        <code
          key={match.index}
          className="text-[#FE6B36] font-mono text-[10px] bg-[#FE6B36]/10 px-1 rounded"
        >
          {match[4]}
        </code>,
      );
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function PersonaSection({
  section,
  content,
}: {
  section: string;
  content: string;
}) {
  const [open, setOpen] = React.useState(true);
  const cfg = SOUL_CONFIG_PANEL[section] ?? {
    color: "#FE6B36",
    icon: <Flame className="w-3 h-3 inline mr-1" />,
  };
  return (
    <div
      className="rounded-lg border bg-white/[0.03] overflow-hidden"
      style={{ borderColor: cfg.color + "30" }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm flex items-center justify-center">
            {cfg.icon}
          </span>
          <span
            className="text-[10px] font-bold uppercase tracking-widest font-mono"
            style={{ color: cfg.color }}
          >
            {section}
          </span>
        </div>
        <span className="text-[10px] text-white/30">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div
          className="px-3 pb-3 space-y-0.5 border-t"
          style={{ borderColor: cfg.color + "20" }}
        >
          {renderMarkdown(content)}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = React.useState<"light" | "dark">(() => {
    const stored = window.localStorage.getItem("zell-theme");
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });
  const [agents, setAgents] = React.useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = React.useState<Agent | null>(null);
  const [selectedAgentPersona, setSelectedAgentPersona] = React.useState<
    Record<string, string>
  >({});
  const [selectedAgentPersonaLoading, setSelectedAgentPersonaLoading] =
    React.useState(false);
  const [currentYear, setCurrentYear] = React.useState(2026);
  const [loading, setLoading] = React.useState(true);
  const [isSpawning, setIsSpawning] = React.useState(false);
  const [batchLoading, setBatchLoading] = React.useState(false);
  const [batchProgress, setBatchProgress] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [systemStats, setSystemStats] = React.useState<any>(null);
  const [logs, setLogs] = React.useState<string[]>(["System initialized..."]);
  const [isDeciding, setIsDeciding] = React.useState(false);
  const [agentActionLogs, setAgentActionLogs] = React.useState<
    Record<string, any[]>
  >({});
  const [showDashboard, setShowDashboard] = React.useState(() => {
    return window.localStorage.getItem("zell-view-dashboard") === "true";
  });
  const [simCompleteToast, setSimCompleteToast] = React.useState<string | null>(
    null,
  );
  const [atlasView, setAtlasView] = React.useState<
    "map" | "graph" | "workbench"
  >(() => {
    const val = window.localStorage.getItem("zell-view-atlas");
    if (val === "map" || val === "graph" || val === "workbench") return val;
    return "map";
  });
  const [rightPanelCollapsed, setRightPanelCollapsed] = React.useState(false);

  React.useEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
    window.localStorage.setItem("zell-theme", theme);
  }, [theme]);

  React.useEffect(() => {
    window.localStorage.setItem("zell-view-dashboard", String(showDashboard));
  }, [showDashboard]);

  React.useEffect(() => {
    window.localStorage.setItem("zell-view-atlas", atlasView);
  }, [atlasView]);

  const addLog = (message: string) => {
    setLogs((prev) => {
      const updated = [
        ...prev,
        `[${new Date().toLocaleTimeString()}] ${message}`,
      ];
      return updated.slice(-50);
    });
  };

  const handleDecide = async () => {
    if (!selectedAgent) return;
    setIsDeciding(true);
    addLog(
      `Requesting thought process from ${selectedAgent.name} (Year ${currentYear})...`,
    );
    try {
      const response = await fetch(
        `${API_BASE}/api/agent/${encodeURIComponent(selectedAgent.id)}/decide`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            world_state: {
              time: "morning",
              season: "spring",
              year: currentYear,
              region: selectedAgent.city,
            },
            scenario: `You are in the year ${currentYear}. Consider your persona, current age, and the global era. What are your immediate thoughts and planned actions for today?`,
          }),
        },
      );
      const data = await response.json();
      const decisionData = data.decision.decision || {};

      addLog(
        `[${selectedAgent.name}]: ${decisionData.action || "Decided to wait."}`,
      );

      const newActionLog = {
        time: new Date().toLocaleTimeString(),
        action: decisionData.action || "Unknown action",
        reasoning: decisionData.reasoning || "No reasoning provided.",
      };
      setAgentActionLogs((prev) => ({
        ...prev,
        [selectedAgent.id]: [newActionLog, ...(prev[selectedAgent.id] || [])],
      }));
    } catch (e) {
      addLog(`Failed to trigger decision for ${selectedAgent.name}`);
    } finally {
      setIsDeciding(false);
    }
  };

  React.useEffect(() => {
    const initApp = async () => {
      try {
        setLoading(true);
        addLog("Connecting to neural network...");

        // 1. Fetch persistent agents from DB if they exist
        const agentsData = await fetchAgents();

        if (agentsData.agents && agentsData.agents.length > 0) {
          const jitter = () => (Math.random() - 0.5) * 0.25;
          const mapped: Agent[] = agentsData.agents.map(
            (a: any, idx: number) => ({
              id: a.id,
              name: a.name,
              age: a.age ?? 30,
              race: a.ethnicity ?? a.race ?? "Unknown",
              soul_type: SOUL_TYPES[idx % 4],
              traits: {},
              bio: `${a.age ?? 30}-year-old ${a.region ?? ""} — ${
                a.role ?? ""
              }`,
              location: [
                (a.location?.[0] ?? 0) + jitter(),
                (a.location?.[1] ?? 0) + jitter(),
              ] as [number, number],
              city: a.location_name ?? a.region ?? "Unknown",
              roleLabel: "Profession",
              roleValue: a.role,
            }),
          );
          setAgents(mapped);
          addLog(`Restored ${mapped.length} persistent agents from cache`);
        } else {
          // Simulating the connection phase for a fresh world
          await new Promise((resolve) => setTimeout(resolve, 800));
          addLog("Neural link established. World is empty and ready.");
        }

        setLoading(false);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        addLog(`Neural link failure: ${message}`);
        setLoading(false);
      }
    };

    initApp();

    // Poll system stats every 2 seconds
    const statsInterval = setInterval(async () => {
      try {
        const stats = await fetchSystemStats();
        setSystemStats(stats);
      } catch (err) {
        console.error("Failed to fetch system stats:", err);
      }
    }, 2000);

    return () => clearInterval(statsInterval);
  }, []);

  // Fetch persona when an agent is selected
  React.useEffect(() => {
    if (!selectedAgent) {
      setSelectedAgentPersona({});
      return;
    }
    const fetchPersona = async () => {
      setSelectedAgentPersonaLoading(true);
      try {
        const data = await getAgentPersona(selectedAgent.id);
        if (data.sections) setSelectedAgentPersona(data.sections);
        else setSelectedAgentPersona({});
      } catch {
        setSelectedAgentPersona({});
      } finally {
        setSelectedAgentPersonaLoading(false);
      }
    };
    fetchPersona();
  }, [selectedAgent?.id]);

  const handleSpawn = async (count: number) => {
    try {
      setIsSpawning(true);
      addLog(`Spawning ${count.toLocaleString()} new agents...`);
      const result = await fetchBootstrap();

      if (!result.data) {
        addLog(`Spawn failed: Backend returned no data`);
        return;
      }

      if (result.data?.profiles && result.data?.cities) {
        const cities = result.data.cities as any[];
        const profiles = result.data.profiles as any[];
        const selectedProfiles = profiles.slice(
          0,
          Math.min(count, profiles.length),
        );

        if (selectedProfiles.length === 0) {
          addLog(`No profiles returned from bootstrap`);
          return;
        }

        addLog(
          `Cities: ${cities.length} • Profiles: ${selectedProfiles.length}`,
        );

        const timestamp = Date.now();
        const newAgents: Agent[] = selectedProfiles.map(
          (profile: any, idx: number) => {
            const city = cities[idx % cities.length];
            const jitter = () => (Math.random() - 0.5) * 0.25;
            return {
              id: `agent-spawn-${timestamp}-${idx}`,
              name: profile.name,
              age: profile.age,
              race: profile.race,
              soul_type: SOUL_TYPES[idx % 4],
              traits: {},
              bio: `${profile.age}-year-old ${profile.race} — ${profile.roleValue}`,
              location: [city.lon + jitter(), city.lat + jitter()] as [
                number,
                number,
              ],
              city: city.name,
              roleLabel: profile.roleLabel,
              roleValue: profile.roleValue,
            };
          },
        );

        const oldCount = agents.length;
        setAgents((prev) => [...prev, ...newAgents]);
        addLog(
          `${newAgents.length} agents placed. Starting brain synthesis...`,
        );

        // Kick off batch persona generation via real endpoint
        setBatchLoading(true);
        try {
          await spawnAgentsBatch(
            newAgents.map((a) => ({
              id: a.id,
              name: a.name,
              age: a.age,
              ethnicity: a.race,
              role: a.roleValue ?? "",
              role_label: a.roleLabel,
              personality_archetype: a.soul_type,
            })),
          );

          // Poll /api/agents/generation-status
          let lastLoggedCount = 0;
          const pollInterval = setInterval(async () => {
            try {
              const statusData = await getBatchStatus();
              const stats = statusData.stats;
              setBatchProgress(stats);

              // Log progress for newly completed agents
              if (stats.completed > lastLoggedCount) {
                for (let i = lastLoggedCount + 1; i <= stats.completed; i++) {
                  addLog(`Agent ${i} synthesized successfully`);
                }
                lastLoggedCount = stats.completed;
              }

              if (
                stats.total > 0 &&
                stats.pending === 0 &&
                stats.in_progress === 0
              ) {
                clearInterval(pollInterval);
                setBatchLoading(false);
                addLog(
                  `All ${stats.completed} agent brains synthesized! (${stats.failed} failed)`,
                );
              }
            } catch {
              clearInterval(pollInterval);
              setBatchLoading(false);
            }
          }, 2000);
        } catch (err) {
          console.error("Spawn batch error:", err);
          setBatchLoading(false);
        } finally {
          setIsSpawning(false);
        }

        addLog(`Total: ${oldCount} → ${oldCount + newAgents.length} agents`);
      } else {
        addLog(`Spawn failed: Backend data missing profiles/cities`);
        setIsSpawning(false);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      addLog(`Exception in spawn: ${message}`);
      setIsSpawning(false);
    }
  };

  const handleReset = () => {
    setAgents([]);
    setSelectedAgent(null);
    setBatchLoading(false);
    setBatchProgress(null);
    addLog("Simulation reset");
  };

  const [isSimulating, setIsSimulating] = React.useState(false);
  const [simStatus, setSimStatus] = React.useState<any>(null);

  const handleTriggerEvent = async (eventName: string) => {
    addLog(`GOD MODE TRIGGERED: ${eventName}`);
    setIsSimulating(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulation/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event: eventName,
          cycles: 3, // default N-cyle
          year: currentYear,
        }),
      });
      await response.json();
      addLog(
        `[ORCHESTRATOR] 3-cycle mesh simulation started for global event on all agents.`,
      );
    } catch (e) {
      addLog(`Failed to trigger global event: ${eventName}`);
      setIsSimulating(false);
    }
  };

  // Poll for simulation status
  React.useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isSimulating) {
      interval = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/api/simulation/status`);
          const data = await response.json();
          setSimStatus(data);
          if (
            !data.is_running &&
            data.total_cycles > 0 &&
            data.current_cycle === data.total_cycles &&
            data.completed_agents === data.total_agents
          ) {
            setIsSimulating(false);
            setShowDashboard(true);
            addLog(
              `God Mode Simulation Complete — responses stored in dashboard`,
            );
            setSimCompleteToast(
              `Simulation complete: "${data.current_event}" — ${data.total_agents} agents responded.`,
            );
            setTimeout(() => setSimCompleteToast(null), 8000);
          }
        } catch (e) {
          console.error(e);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isSimulating]);

  return (
    <div className="force-theme-adapt h-screen w-screen flex flex-col bg-background text-foreground">
      {/* Simulation Complete Toast */}
      {simCompleteToast && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-[140] flex items-center gap-3 bg-card border border-[#FE6B36]/50 rounded-xl px-4 py-3 shadow-[0_0_30px_rgba(254,107,54,0.3)] animate-in fade-in slide-in-from-bottom-4">
          <CheckCircle2 className="text-[#FE6B36] w-5 h-5 flex-shrink-0" />
          <div>
            <p className="text-[11px] text-white font-bold">
              {simCompleteToast}
            </p>
            <button
              onClick={() => {
                setShowDashboard(true);
                setSimCompleteToast(null);
              }}
              className="text-[10px] text-[#FE6B36] hover:underline mt-0.5"
            >
              View in Dashboard →
            </button>
          </div>
          <button
            onClick={() => setSimCompleteToast(null)}
            className="text-white/30 hover:text-white ml-2 text-lg leading-none"
          >
            ✕
          </button>
        </div>
      )}
      {/* Initial Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black">
          <div className="w-full max-w-md px-8 space-y-8 text-center">
            <div className="space-y-2">
              <h1 className="text-6xl font-black italic tracking-tighter text-[#FE6B36] animate-pulse">
                ZELL
              </h1>
              <p className="text-[#FE6B36]/60 font-mono text-[10px] tracking-[0.5em] uppercase">
                Human Agent Swarm Simulator
              </p>
            </div>

            <div className="space-y-4">
              <div className="h-1 w-full bg-[#FE6B36]/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#FE6B36] animate-shimmer shadow-[0_0_15px_rgba(254,107,54,0.5)]"
                  style={{ width: "40%" }}
                />
              </div>
              <p className="text-[10px] text-[#FE6B36] font-mono animate-pulse uppercase tracking-widest">
                Fetching civilization data...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* God Mode Simulating Overlay */}
      {isSimulating && (
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-black/90 backdrop-blur-sm">
          <div className="w-full max-w-md px-8 space-y-8 text-center">
            <div className="space-y-2">
              <h1 className="text-4xl font-black italic tracking-tighter text-[#FE6B36] animate-pulse mb-4">
                SIMULATING GLOBAL MESH
              </h1>
              <div className="bg-[#FE6B36]/10 border border-[#FE6B36] p-4 font-mono text-xs text-[#FE6B36]">
                <div>
                  GLOBAL EVENT: {simStatus?.current_event || "Loading..."}
                </div>
                <div className="my-2">
                  [ CYCLE {simStatus?.current_cycle || 0} /{" "}
                  {simStatus?.total_cycles || 0} ]
                </div>
                <div>
                  AGENTS PROCESSED: {simStatus?.completed_agents || 0} /{" "}
                  {simStatus?.total_agents || agents.length}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="h-1 w-full bg-[#FE6B36]/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#FE6B36] shadow-[0_0_15px_rgba(254,107,54,0.5)] transition-all duration-300"
                  style={{
                    width:
                      simStatus?.total_agents > 0
                        ? `${
                            (simStatus?.completed_agents /
                              simStatus?.total_agents) *
                            100
                          }%`
                        : "0%",
                  }}
                />
              </div>
              <p className="text-[10px] text-[#FE6B36] font-mono animate-pulse uppercase tracking-widest">
                Computing synchronous multi-agent intra/inter node state
                transitions...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Global Batch Loading Overlay */}
      {batchLoading && (
        <div className="fixed inset-0 z-[130] flex items-center justify-center bg-background/95 backdrop-blur-xl font-mono">
          <div className="w-full max-w-2xl px-10 text-center space-y-10">
            {/* Title */}
            <div className="space-y-3">
              <h1 className="text-5xl font-black italic tracking-tighter text-[#FE6B36] animate-pulse uppercase">
                Synthesizing Civilizations
              </h1>
              <p className="text-[#FE6B36]/60 text-xs tracking-[0.3em] uppercase">
                Neural Link Established | Constructing Digital Souls
              </p>
            </div>

            {/* Progress bar */}
            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <p className="text-[10px] text-[#FE6B36]/80 uppercase tracking-widest">
                  Brain Synthesis Progress
                </p>
                <p className="text-2xl font-black text-white">
                  {batchProgress
                    ? `${batchProgress.completed} / ${batchProgress.total}`
                    : "0 / ?"}
                </p>
              </div>
              <div className="h-3 w-full bg-[#FE6B36]/10 rounded-full overflow-hidden border border-[#FE6B36]/20 p-0.5">
                <div
                  className="h-full bg-gradient-to-r from-[#FE6B36] to-[#ff8c61] shadow-[0_0_30px_rgba(254,107,54,0.8)] transition-all duration-700 ease-out rounded-full"
                  style={{
                    width: `${batchProgress?.completion_percent ?? 0}%`,
                  }}
                />
              </div>
            </div>

            {/* Stat cards */}
            <div className="grid grid-cols-4 gap-3">
              <div className="border border-[#FE6B36]/20 p-4 rounded-lg bg-[#FE6B36]/5">
                <p className="text-[9px] text-[#FE6B36]/60 uppercase mb-2 tracking-widest">
                  Generated
                </p>
                <p className="text-2xl font-bold text-[#FE6B36]">
                  {batchProgress?.completed ?? 0}
                </p>
              </div>
              <div className="border border-[#FE6B36]/20 p-4 rounded-lg bg-[#FE6B36]/5">
                <p className="text-[9px] text-[#FE6B36]/60 uppercase mb-2 tracking-widest">
                  Queue
                </p>
                <p className="text-2xl font-bold text-[#FE6B36]/50">
                  {(batchProgress?.pending ?? 0) +
                    (batchProgress?.in_progress ?? 0)}
                </p>
              </div>
              <div className="border border-[#FE6B36]/20 p-4 rounded-lg bg-[#FE6B36]/5">
                <p className="text-[9px] text-[#FE6B36]/60 uppercase mb-2 tracking-widest">
                  Failed
                </p>
                <p className="text-2xl font-bold text-red-500/70">
                  {batchProgress?.failed ?? 0}
                </p>
              </div>
              <div className="border border-[#FE6B36]/20 p-4 rounded-lg bg-[#FE6B36]/5">
                <p className="text-[9px] text-[#FE6B36]/60 uppercase mb-2 tracking-widest">
                  Est. Time
                </p>
                <p className="text-xl font-bold text-white">
                  {Math.floor(
                    (batchProgress?.estimated_time_remaining ?? 0) / 60,
                  )}
                  m{" "}
                  {Math.round(
                    (batchProgress?.estimated_time_remaining ?? 0) % 60,
                  )}
                  s
                </p>
              </div>
            </div>

            {/* Live activity feed */}
            <div className="border border-[#FE6B36]/15 rounded-lg bg-[#FE6B36]/5 p-4 text-left space-y-3">
              {batchProgress?.current_agents?.length > 0 && (
                <div>
                  <p className="text-[9px] text-[#FE6B36]/50 uppercase tracking-widest mb-1.5 flex items-center">
                    <Zap className="w-3 h-3 mr-1" /> Active Workers (
                    {batchProgress.workers ?? "—"})
                  </p>
                  <div className="space-y-1">
                    {batchProgress.current_agents.map(
                      (name: string, i: number) => (
                        <div key={i} className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-[#FE6B36] animate-ping shrink-0" />
                          <span className="text-[11px] text-[#FE6B36]">
                            {name}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              )}

              {batchProgress?.recently_completed?.length > 0 && (
                <div>
                  <p className="text-[9px] text-[#FE6B36]/50 uppercase tracking-widest mb-1.5 flex items-center">
                    <CheckCircle2 className="w-3 h-3 mr-1" /> Recently
                    Synthesized
                  </p>
                  <div className="space-y-1">
                    {batchProgress.recently_completed.map(
                      (name: string, i: number) => (
                        <div key={i} className="flex items-center gap-2">
                          <CheckCircle2 className="w-3 h-3 text-green-400/70 shrink-0" />
                          <span className="text-[11px] text-white/60">
                            {name}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              )}

              {systemStats && (
                <div className="pt-2 border-t border-[#FE6B36]/10">
                  <p className="text-[9px] text-[#FE6B36]/50 uppercase tracking-widest mb-1.5 flex justify-between">
                    <span className="flex items-center gap-1.5">
                      <Activity className="w-3 h-3" /> System Diagnostics
                    </span>
                    <span>
                      {systemStats.timestamp.split("T")[1].split(".")[0]}
                    </span>
                  </p>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-white/40">CPU Load</span>
                      <span className="text-[#FE6B36]">
                        {systemStats.hardware.cpu_usage}%
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-white/40">Memory</span>
                      <span className="text-[#FE6B36]">
                        {systemStats.hardware.ram_usage}%
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-white/40">Model</span>
                      <span className="text-[#FE6B36]">
                        {systemStats.llm.model}
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-white/40">Provider</span>
                      <span className="text-white/60 lowercase">
                        {systemStats.llm.provider}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center pt-1 border-t border-[#FE6B36]/10">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#FE6B36] animate-ping" />
                  <span className="text-[10px] text-[#FE6B36] uppercase tracking-widest">
                    LLM is thinking...
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[10px] text-[#FE6B36]/40 uppercase">
                    {(batchProgress?.avg_time_per_agent ?? 0).toFixed(1)}s /
                    agent
                  </span>
                  {batchProgress?.elapsed_seconds != null && (
                    <span className="text-[10px] text-[#FE6B36]/40 uppercase">
                      Elapsed: {Math.floor(batchProgress.elapsed_seconds / 60)}m{" "}
                      {Math.round(batchProgress.elapsed_seconds % 60)}s
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="opacity-20 hover:opacity-100 transition-opacity">
              <button
                onClick={() => setBatchLoading(false)}
                className="text-[10px] text-red-500 uppercase tracking-widest border border-red-500 px-4 py-2 rounded hover:bg-red-500 hover:text-white"
              >
                Abort Synthesis
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-card border-b border-border px-3 py-2 flex items-center justify-between z-50 gap-2 min-w-0">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div className="text-xl font-bold text-[#FE6B36] tracking-tighter italic shrink-0">
            ZELL
          </div>

          <nav
            className="flex items-center gap-1 min-w-0 overflow-x-auto scrollbar-none"
            style={{ scrollbarWidth: "none" }}
          >
            <button
              onClick={() => {
                setShowDashboard(false);
                setAtlasView("map");
              }}
              className={`flex items-center gap-1 px-2 py-1.5 rounded-md border text-[10px] font-bold uppercase tracking-widest transition-colors whitespace-nowrap shrink-0 ${
                atlasView === "map" && !showDashboard
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/10 text-[#FE6B36]"
                  : "border-white/15 bg-white/[0.03] text-white/65 hover:text-white"
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Map</span>
            </button>

            <button
              onClick={() => {
                setShowDashboard(false);
                setAtlasView("graph");
              }}
              className={`flex items-center gap-1 px-2 py-1.5 rounded-md border text-[10px] font-bold uppercase tracking-widest transition-colors whitespace-nowrap shrink-0 ${
                atlasView === "graph" && !showDashboard
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/10 text-[#FE6B36]"
                  : "border-white/15 bg-white/[0.03] text-white/65 hover:text-white"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Graph</span>
            </button>

            <button
              onClick={() => {
                setShowDashboard(false);
                setAtlasView("workbench");
              }}
              className={`flex items-center gap-1 px-2 py-1.5 rounded-md border text-[10px] font-bold uppercase tracking-widest transition-colors whitespace-nowrap shrink-0 ${
                atlasView === "workbench" && !showDashboard
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/10 text-[#FE6B36]"
                  : "border-white/15 bg-white/[0.03] text-white/65 hover:text-white"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Workbench</span>
            </button>

            <button
              onClick={() => setShowDashboard((v) => !v)}
              className={`flex items-center gap-1 px-2 py-1.5 rounded-md border text-[10px] font-bold uppercase tracking-widest transition-colors whitespace-nowrap shrink-0 ${
                showDashboard
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/10 text-[#FE6B36]"
                  : "border-white/15 bg-white/[0.03] hover:text-white text-white/65"
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="hidden sm:inline">Dashboard</span>
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-1.5 text-[10px] font-mono border border-white/10 rounded-md px-2 py-1.5 bg-black/25 shrink-0">
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              systemStats?.status === "online"
                ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)] animate-pulse"
                : "bg-red-500"
            }`}
          />
          <span className="text-white/85 hidden xs:inline">
            {loading ? "..." : agents.length.toLocaleString()} agents
          </span>
          <span className="text-white/85 xs:hidden">
            {loading ? "..." : agents.length.toLocaleString()}
          </span>
          <span className="text-white/35 hidden md:inline">|</span>
          <span className="text-white/75 hidden md:inline">
            CPU{" "}
            {typeof systemStats?.hardware?.cpu_usage === "number"
              ? `${systemStats.hardware.cpu_usage.toFixed(1)}%`
              : "--"}
          </span>
          <span className="text-white/35 hidden lg:inline">
            RAM{" "}
            {typeof systemStats?.hardware?.ram_usage === "number"
              ? `${systemStats.hardware.ram_usage.toFixed(1)}%`
              : "--"}
          </span>
          <span className="text-white/35 hidden lg:inline">
            LLM {systemStats?.llm?.model ?? "--"}
          </span>
        </div>

        <button
          onClick={() =>
            setTheme((prev) => (prev === "dark" ? "light" : "dark"))
          }
          className="ml-2 flex items-center gap-1.5 text-[10px] font-mono border border-white/10 rounded-md px-2 py-1.5 bg-black/25 text-white/80 hover:text-white transition-colors shrink-0"
          title={
            theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
          }
        >
          {theme === "dark" ? (
            <Sun className="w-3.5 h-3.5" />
          ) : (
            <Moon className="w-3.5 h-3.5" />
          )}
          <span className="hidden sm:inline">
            {theme === "dark" ? "Light" : "Dark"}
          </span>
        </button>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Control Panel */}
        <ControlPanel
          agentCount={agents.length}
          onSpawn={handleSpawn}
          onReset={handleReset}
          isLoading={isSpawning}
          onTriggerEvent={handleTriggerEvent}
          currentYear={currentYear}
          onYearChange={setCurrentYear}
        />

        {showDashboard ? (
          <main className="flex-1 relative overflow-hidden">
            <EventDashboard onClose={() => setShowDashboard(false)} />
          </main>
        ) : (
          <main className="flex-1 relative overflow-hidden">
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-50">
                <div className="bg-card border border-red-500 rounded-lg p-6 text-center max-w-sm">
                  <p className="text-red-400 mb-2 font-semibold">
                    Connection Error
                  </p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                  <p className="text-xs text-muted-foreground mt-4">
                    Make sure backend is running on port 8000
                  </p>
                </div>
              </div>
            )}
            <AtlasView
              agents={agents}
              selectedAgent={selectedAgent}
              onAgentSelect={setSelectedAgent}
              activeView={atlasView}
              theme={theme}
              onViewChange={setAtlasView}
              showTopNav={false}
            />
          </main>
        )}

        {/* Right Panel — Intelligence Feed + Selected Agent */}
        {(selectedAgent || atlasView === "map") && (
          <div
            className="relative flex h-full shrink-0"
            style={{
              width: rightPanelCollapsed ? 0 : "auto",
              transition: "width 0.2s ease",
              overflow: "visible",
            }}
          >
            <aside className="w-72 lg:w-80 bg-card border-l border-border flex flex-col overflow-hidden shrink-0">
              {selectedAgent ? (
                /* ── SELECTED AGENT PERSONA PANEL ── */
                <div className="flex flex-col h-full">
                  {/* Header */}
                  <div className="p-4 border-b border-border shrink-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
                        Selected Agent
                      </p>
                      <button
                        onClick={() => {
                          setSelectedAgent(null);
                          setSelectedAgentPersona({});
                        }}
                        className="text-[10px] text-red-400 hover:text-red-300 transition-colors"
                      >
                        ✕ Close
                      </button>
                    </div>
                    <div className="flex items-center gap-3 mt-2">
                      <img
                        src={`data:image/svg+xml;utf8,${encodeURIComponent(
                          multiavatar(selectedAgent.id),
                        )}`}
                        alt={selectedAgent.name}
                        className="w-10 h-10 rounded-full border-2 border-[#FE6B36]/50 shrink-0"
                      />
                      <div className="min-w-0">
                        <p className="font-bold text-[#FE6B36] font-mono text-sm truncate">
                          {selectedAgent.name}
                        </p>
                        <p className="text-[10px] text-muted-foreground truncate">
                          {selectedAgent.city} · Age {selectedAgent.age}
                        </p>
                        <p className="text-[10px] text-muted-foreground truncate">
                          {selectedAgent.roleValue}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#FE6B36] animate-pulse shrink-0" />
                      <span className="text-[9px] uppercase tracking-widest text-[#FE6B36] font-mono">
                        {selectedAgent.soul_type} archetype
                      </span>
                    </div>
                    <button
                      onClick={handleDecide}
                      disabled={isDeciding || selectedAgentPersonaLoading}
                      className="mt-4 w-full bg-[#FE6B36]/10 hover:bg-[#FE6B36]/20 text-[#FE6B36] border border-[#FE6B36]/30 transition-colors rounded-lg py-2 text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isDeciding ? (
                        <>
                          <span className="w-3 h-3 border-2 border-[#FE6B36]/30 border-t-[#FE6B36] rounded-full animate-spin" />
                          <span>Thinking...</span>
                        </>
                      ) : (
                        <>
                          <Brain className="w-4 h-4" /> Check Thoughts
                        </>
                      )}
                    </button>
                  </div>

                  {/* Persona sections and Action Logs */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-6">
                    {/* Agent Action Thoughts Tracker */}
                    {agentActionLogs[selectedAgent.id] &&
                      agentActionLogs[selectedAgent.id].length > 0 && (
                        <div className="space-y-3">
                          <h3 className="text-[10px] font-bold uppercase tracking-widest text-[#FE6B36] flex items-center">
                            <MessageSquare className="w-3 h-3 mr-1" /> Recent
                            Thoughts
                          </h3>
                          <div className="space-y-3">
                            {agentActionLogs[selectedAgent.id].map(
                              (
                                log: {
                                  time: string;
                                  action: string;
                                  reasoning: string;
                                },
                                i: number,
                              ) => (
                                <div
                                  key={i}
                                  className="bg-black/20 border border-white/5 p-3 rounded space-y-2"
                                >
                                  <div className="text-[10px] text-[#FE6B36]/60 flex items-center justify-between">
                                    <span className="font-mono">
                                      {log.time}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-white/90 leading-relaxed font-semibold">
                                    "{log.action}"
                                  </p>
                                  <p className="text-[10px] text-white/50 italic leading-relaxed">
                                    {log.reasoning}
                                  </p>
                                </div>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                    <div className="border-t border-border pt-4">
                      <h3 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-4">
                        Psycho-Social Profile
                      </h3>
                      {selectedAgentPersonaLoading && (
                        <div className="flex flex-col items-center justify-center py-10 gap-3">
                          <div className="w-5 h-5 border-2 border-[#FE6B36] border-t-transparent rounded-full animate-spin" />
                          <p className="text-[10px] text-[#FE6B36] uppercase tracking-widest animate-pulse">
                            Loading persona...
                          </p>
                        </div>
                      )}

                      {!selectedAgentPersonaLoading &&
                        Object.keys(selectedAgentPersona).length === 0 && (
                          <div className="text-center py-10">
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
                              No persona generated yet
                            </p>
                            <p className="text-[9px] text-muted-foreground mt-1">
                              Spawn agents to generate personas
                            </p>
                          </div>
                        )}

                      {Object.entries(selectedAgentPersona).map(
                        ([section, content]) => (
                          <PersonaSection
                            key={section}
                            section={section}
                            content={content}
                          />
                        ),
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                /* ── INTELLIGENCE FEED ── */
                <div className="flex flex-col h-full p-4">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-4 shrink-0 flex items-center">
                    <ScrollText className="w-4 h-4 mr-2" /> Intelligence Feed
                  </h2>
                  <div className="flex-1 space-y-1 text-xs font-mono text-muted-foreground overflow-y-auto">
                    {logs.map((log, idx) => (
                      <div
                        key={idx}
                        className="text-[#FE6B36]/70 hover:text-[#FE6B36] transition-colors py-0.5"
                      >
                        {log}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </aside>

            {/* Collapse toggle — centred bulge tab, always visible */}
            <button
              onClick={() => setRightPanelCollapsed((v) => !v)}
              style={{ left: -16 }}
              className="absolute top-1/2 -translate-y-1/2 z-[30] flex items-center justify-center w-4 h-10 bg-card border border-r-0 border-border rounded-l-md hover:bg-[#FE6B36]/10 hover:border-[#FE6B36]/40 transition-colors shadow-[-2px_0_8px_rgba(0,0,0,0.4)]"
              title={rightPanelCollapsed ? "Expand panel" : "Collapse panel"}
            >
              {rightPanelCollapsed ? (
                <ChevronLeft className="w-3 h-3 text-white/50" />
              ) : (
                <ChevronRight className="w-3 h-3 text-white/50" />
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
