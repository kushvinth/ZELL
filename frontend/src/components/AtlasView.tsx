import React from "react";
import {
  MapPin,
  Network,
  MessagesSquare,
  RefreshCcw,
  GitBranch,
} from "lucide-react";
import { WorldMap } from "./WorldMap";
import { GraphPanel } from "./GraphPanel";
import { ChatWorkbench } from "./ChatWorkbench";
import {
  buildGraphRelationships,
  fetchGraphRelationships,
  type GraphRelationshipsResponse,
} from "@/lib/api";

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

interface AtlasViewProps {
  agents: Agent[];
  selectedAgent: Agent | null;
  onAgentSelect: (agent: Agent) => void;
  theme?: "light" | "dark";
  activeView?: "map" | "graph" | "workbench";
  onViewChange?: (view: "map" | "graph" | "workbench") => void;
  showTopNav?: boolean;
}

export function AtlasView({
  agents,
  selectedAgent,
  onAgentSelect,
  theme,
  activeView,
  onViewChange,
  showTopNav = true,
}: AtlasViewProps) {
  const [graph, setGraph] = React.useState<GraphRelationshipsResponse | null>(
    null,
  );
  const [loadingGraph, setLoadingGraph] = React.useState(false);
  const [internalView, setInternalView] = React.useState<
    "map" | "graph" | "workbench"
  >("map");
  const [jiggleGraph, setJiggleGraph] = React.useState(false);
  const prevView = React.useRef<string>("map");

  const resolvedView = activeView ?? internalView;

  const changeView = React.useCallback(
    (view: "map" | "graph" | "workbench") => {
      if (activeView === undefined) setInternalView(view);
      onViewChange?.(view);
    },
    [activeView, onViewChange],
  );

  // Jiggle when switching TO the graph view
  React.useEffect(() => {
    if (resolvedView === "graph" && prevView.current !== "graph") {
      setJiggleGraph(true);
      const t = setTimeout(() => setJiggleGraph(false), 50);
      return () => clearTimeout(t);
    }
    prevView.current = resolvedView;
  }, [resolvedView]);

  const refreshGraph = React.useCallback(async () => {
    setLoadingGraph(true);
    try {
      try {
        await buildGraphRelationships();
      } catch (err) {
        console.warn("Graph build skipped/fallback", err);
      }
      const payload = await fetchGraphRelationships();
      setGraph(payload);
    } catch (err) {
      console.error("Graph refresh failed", err);
    } finally {
      setLoadingGraph(false);
    }
  }, []);

  React.useEffect(() => {
    refreshGraph();
  }, [refreshGraph]);

  const selectedFromGraph = React.useMemo(() => {
    if (!selectedAgent || !graph) return null;
    return graph.nodes.find((n) => n.agent_id === selectedAgent.id) || null;
  }, [graph, selectedAgent]);

  return (
    <div className="w-full h-full flex flex-col overflow-hidden bg-card">
      {showTopNav && (
        <div className="h-11 border-b border-border flex items-center justify-between px-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => changeView("map")}
              className={`px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-widest border transition-colors flex items-center gap-1.5 ${
                resolvedView === "map"
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/12 text-[#FE6B36]"
                  : "border-white/10 bg-white/[0.03] text-white/60 hover:text-white"
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              Map
            </button>

            <button
              onClick={() => changeView("graph")}
              className={`px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-widest border transition-colors flex items-center gap-1.5 ${
                resolvedView === "graph"
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/12 text-[#FE6B36]"
                  : "border-white/10 bg-white/[0.03] text-white/60 hover:text-white"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Graph Relationship Visualization
            </button>

            <button
              onClick={() => changeView("workbench")}
              className={`px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-widest border transition-colors flex items-center gap-1.5 ${
                resolvedView === "workbench"
                  ? "border-[#FE6B36]/40 bg-[#FE6B36]/12 text-[#FE6B36]"
                  : "border-white/10 bg-white/[0.03] text-white/60 hover:text-white"
              }`}
            >
              <MessagesSquare className="w-3.5 h-3.5" />
              Workbench
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={refreshGraph}
              className="px-2.5 py-1.5 rounded border border-white/10 text-white/60 hover:text-white text-[10px] uppercase tracking-widest flex items-center gap-1"
            >
              <RefreshCcw className="w-3.5 h-3.5" />
              Refresh Graph
            </button>
            <div className="text-[10px] text-white/45 flex items-center gap-1.5">
              <GitBranch className="w-3.5 h-3.5" />
              <span>
                {graph?.stats.node_count ?? 0} agents ·{" "}
                {graph?.stats.edge_count ?? 0} edges
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 min-h-0 relative">
        {resolvedView === "map" && (
          <div className="w-full h-full">
            <WorldMap
              agents={agents}
              selectedAgent={selectedAgent}
              onAgentSelect={onAgentSelect}
              theme={theme}
            />
          </div>
        )}

        {resolvedView === "graph" && (
          <div className="w-full h-full">
            <GraphPanel
              data={graph}
              theme={theme}
              loading={loadingGraph}
              selectedAgentId={selectedAgent?.id || null}
              onSelectAgent={(agentId: string) => {
                const mapped = agents.find((a) => a.id === agentId);
                if (mapped) onAgentSelect(mapped);
              }}
              onRefresh={refreshGraph}
              jiggle={jiggleGraph}
            />
          </div>
        )}

        {resolvedView === "workbench" && (
          <div className="w-full h-full">
            <ChatWorkbench
              theme={theme}
              runId={graph?.run_id}
              selectedAgent={
                selectedFromGraph
                  ? {
                      id: selectedFromGraph.agent_id,
                      name: selectedFromGraph.agent_name,
                    }
                  : null
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
