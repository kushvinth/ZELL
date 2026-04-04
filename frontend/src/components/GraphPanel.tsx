/**
 * GraphPanel — exact Logseq graph, ported to React + pixi.js
 *
 * Color scheme, force params, node sizing — all copied from:
 *   logseq/src/main/frontend/extensions/graph/pixi.cljs
 *   logseq/src/main/frontend/common/graph_view.cljs
 *
 * Agents  = Pages/Notes  → colored circles (D3 categorical palette, size by cbrt(degree))
 * Country = Property tag → orange tinted circle
 * Occupation = Tag page  → same palette, tagged with "orange" in dark mode
 * Edges: width 1, color #094b5a (dark mode)
 * Hover: node #6366F1, edges #A5B4FC
 * Labels: fontSize 12, rgba(255,255,255,0.8)
 */

import React from "react";
import { Application, Container, Graphics, Text } from "pixi.js";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
} from "d3-force";
import type { GraphRelationshipsResponse, GraphNode } from "@/lib/api";
import {
  RefreshCcw,
  X,
  Globe2,
  Hash,
  User,
  Link2,
  Network,
  Tag,
  ZoomIn,
  ZoomOut,
  LocateFixed,
  SlidersHorizontal,
  RotateCcw,
} from "lucide-react";

// ─── Logseq exact constants ──────────────────────────────────────────────────

/** Pick color based on node kind */
function getNodeColor(
  kind: NodeKind,
  id: string,
  theme: "light" | "dark" = "dark",
): number {
  if (kind === "agent") return theme === "light" ? 0x1f2937 : 0xffffff;
  return 0xfe6b36;
}

function getNodeColorHex(
  kind: NodeKind,
  id: string,
  theme: "light" | "dark" = "dark",
): string {
  if (kind === "agent") return theme === "light" ? "#1f2937" : "#ffffff";
  return "#fe6b36";
}

// Node sizing — small for agents, big for metadata (based on degree)
function getNodeSize(kind: NodeKind, _degree: number): number {
  if (kind === "agent") return 5;
  return 12; // large metadata hubs
}

const DEFAULT_FORCES = {
  linkDist: 300, // spread out clusters significantly
  chargeStrength: -2000, // very strong repulsion
  chargeRange: 1000, // affect nodes at long range
};

// ─── Types ───────────────────────────────────────────────────────────────────

type NodeKind =
  | "agent"
  | "country"
  | "occupation"
  | "image_job_tag"
  | "archetype"
  | "ethnicity"
  | "age_group"
  | "other";
type EdgeKind = "property" | "tag" | "peer" | "interaction";

interface ZNode {
  id: string;
  label: string;
  kind: NodeKind;
  raw: GraphNode;
}
interface ZEdge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind;
  weight: number;
}
interface SimNode extends ZNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
}

// ─── Data helpers ─────────────────────────────────────────────────────────────

function inferKind(n: GraphNode): NodeKind {
  if (n.node_type === "agent") return "agent";
  const cat = (n.meta_category ?? "").toLowerCase();
  if (cat.includes("country")) return "country";
  if (cat.includes("occupation")) return "occupation";
  if (cat.includes("archetype")) return "archetype";
  if (cat.includes("ethnicity")) return "ethnicity";
  if (cat.includes("age_group")) return "age_group";
  if (cat.includes("image_job") || cat.includes("tag")) return "image_job_tag";
  return "other";
}
function inferEdgeKind(rel: string): EdgeKind {
  const r = rel.toLowerCase();
  if (r.startsWith("property_") || r.includes("country")) return "property";
  if (r.startsWith("tag_") || r.includes("occupation")) return "tag";
  if (r.includes("peer")) return "peer";
  return "interaction";
}

// Is this a "tag" node (non-agent meta) — gets orange color like logseq tags
function isTagNode(kind: NodeKind) {
  return kind !== "agent" && kind !== "other";
}

// ─── Draw dot grid ────────────────────────────────────────────────────────────

function drawDotGrid(
  g: Graphics,
  w: number,
  h: number,
  color = 0x1a1a1a,
  alpha = 0.6,
) {
  g.clear();
  g.beginFill(color, alpha);
  for (let x = 20; x < w; x += 20)
    for (let y = 20; y < h; y += 20) g.drawCircle(x, y, 0.7);
  g.endFill();
}

// ─── Force controls panel ─────────────────────────────────────────────────────

interface ForcePanelProps {
  linkDist: number;
  chargeStrength: number;
  chargeRange: number;
  onChange: (
    k: "linkDist" | "chargeStrength" | "chargeRange",
    v: number,
  ) => void;
  onReset: () => void;
  sidebarOpen?: boolean;
  theme: "light" | "dark";
}
function ForcePanel({
  linkDist,
  chargeStrength,
  chargeRange,
  onChange,
  onReset,
  sidebarOpen,
  theme,
}: ForcePanelProps) {
  const [open, setOpen] = React.useState(true);
  const slider = (
    label: string,
    key: "linkDist" | "chargeStrength" | "chargeRange",
    min: number,
    max: number,
    step: number,
    val: number,
  ) => (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span
          className={`text-[9px] uppercase tracking-wider font-mono ${
            theme === "light" ? "text-slate-600" : "text-white/45"
          }`}
        >
          {label}
        </span>
        <span className="text-[9px] text-[#6366f1] font-mono">{val}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={val}
        onChange={(e) => onChange(key, Number(e.target.value))}
        className={`w-full h-1 rounded-full appearance-none accent-[#6366f1] cursor-pointer ${
          theme === "light" ? "bg-slate-300" : "bg-white/10"
        }`}
      />
    </div>
  );
  return (
    <div
      className="absolute bottom-3 z-20"
      style={{
        right: sidebarOpen ? "300px" : "12px",
        transition: "right 0.2s",
      }}
      onPointerDown={(e) => e.stopPropagation()}
      onPointerMove={(e) => e.stopPropagation()}
      onPointerUp={(e) => e.stopPropagation()}
      onWheel={(e) => e.stopPropagation()}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[9px] font-bold uppercase tracking-widest transition-colors ${
          open
            ? "bg-[#6366f1]/15 border-[#6366f1]/40 text-[#6366f1]"
            : "bg-black/60 border-white/10 text-white/50 hover:text-white"
        }`}
      >
        <SlidersHorizontal className="w-3 h-3" />
        Forces
      </button>
      {open && (
        <div
          className={`absolute bottom-8 right-0 w-52 rounded-xl p-3 space-y-3 backdrop-blur-xl shadow-2xl ${
            theme === "light"
              ? "bg-white/95 border border-slate-300"
              : "bg-[#0a0a0a]/95 border border-white/10"
          }`}
        >
          <p className="text-[8px] text-muted-foreground uppercase tracking-widest font-mono">
            D3 Force Settings
          </p>
          {slider("Link Distance", "linkDist", 10, 300, 5, linkDist)}
          {slider(
            "Charge Strength",
            "chargeStrength",
            -2000,
            -10,
            10,
            chargeStrength,
          )}
          {slider("Charge Range", "chargeRange", 50, 1000, 10, chargeRange)}
          <button
            onClick={() => {
              onReset();
              setOpen(false);
            }}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg border border-border text-[9px] text-muted-foreground hover:text-foreground hover:border-foreground/30 uppercase tracking-wider font-mono transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Reset Forces
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({
  node,
  nodes,
  edges,
  onClose,
  onSelect,
  theme,
}: {
  node: ZNode | null;
  nodes: ZNode[];
  edges: ZEdge[];
  onClose: () => void;
  onSelect: (id: string) => void;
  theme: "light" | "dark";
}) {
  if (!node) return null;
  const byId = React.useMemo(() => {
    const m = new Map<string, ZNode>();
    nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [nodes]);
  const myEdges = edges.filter(
    (e) => e.source === node.id || e.target === node.id,
  );
  const props: Array<{ label: string; tid: string; tkind: NodeKind }> = [];
  const peers: Array<{ id: string; label: string }> = [];
  const linked: Array<{ id: string; label: string }> = [];

  for (const e of myEdges) {
    const oid = e.source === node.id ? e.target : e.source;
    const o = byId.get(oid);
    if (!o) continue;
    if (node.kind === "agent") {
      if (o.kind !== "agent")
        props.push({ label: o.label, tid: o.id, tkind: o.kind });
      else peers.push({ id: o.id, label: o.label });
    } else if (o.kind === "agent") {
      linked.push({ id: o.id, label: o.label });
    }
  }

  const kindLabel: Record<NodeKind, string> = {
    agent: "Person · Note",
    country: "Country · Property",
    occupation: "Occupation · Tag",
    image_job_tag: "Job Tag · Tag",
    archetype: "Archetype · Property",
    ethnicity: "Ethnicity · Property",
    age_group: "Age Group · Property",
    other: "Entity",
  };
  const dot = (id: string, kind: NodeKind) => (
    <span
      className="inline-block w-2 h-2 rounded-full mr-1.5 flex-shrink-0"
      style={{ background: getNodeColorHex(kind, id, theme) }}
    />
  );

  return (
    <div
      className={`absolute top-0 right-0 h-full w-72 flex flex-col z-30 backdrop-blur-md ${
        theme === "light"
          ? "bg-white/95 border-l border-slate-300"
          : "bg-black/95 border-l border-white/10"
      }`}
      onPointerDown={(e) => e.stopPropagation()}
      onPointerMove={(e) => e.stopPropagation()}
      onPointerUp={(e) => e.stopPropagation()}
      onWheel={(e) => e.stopPropagation()}
    >
      <div className="flex items-start gap-2 px-4 py-3 border-b border-border">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            {dot(node.id, node.kind)}
            <span className="text-[9px] text-white/35 uppercase tracking-widest font-mono">
              {kindLabel[node.kind]}
            </span>
          </div>
          <p className="text-sm font-bold text-white truncate leading-tight">
            {node.label}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-white/25 hover:text-white/70 mt-0.5 transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-[11px]">
        {node.kind === "agent" && props.length > 0 && (
          <div>
            <p className="text-[9px] text-white/30 uppercase tracking-widest font-mono mb-2">
              Properties
            </p>
            <div className="space-y-1.5">
              {props.map((p, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-white/30 font-mono text-right w-24 shrink-0 text-[10px]">
                    {p.tkind === "image_job_tag" ? "image_job" : p.tkind}::
                  </span>
                  <button
                    onClick={() => onSelect(p.tid)}
                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-medium hover:opacity-80 transition-opacity ${
                      ["country", "ethnicity", "age_group"].includes(p.tkind)
                        ? "bg-orange-500/10 text-orange-300 border-orange-400/20"
                        : "bg-violet-500/10 text-violet-300 border-violet-400/20"
                    }`}
                  >
                    {["country", "ethnicity", "age_group"].includes(p.tkind) ? (
                      <Link2 className="w-2.5 h-2.5" />
                    ) : (
                      <Hash className="w-2.5 h-2.5" />
                    )}
                    {p.label}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
        {node.kind === "agent" && peers.length > 0 && (
          <div>
            <p className="text-[9px] text-white/30 uppercase tracking-widest font-mono mb-1.5">
              Linked people ({peers.length})
            </p>
            <div className="space-y-0.5">
              {peers.slice(0, 22).map((p) => (
                <button
                  key={p.id}
                  onClick={() => onSelect(p.id)}
                  className="w-full text-left flex items-center gap-2 px-2 py-1 rounded hover:bg-white/5 text-white/50 hover:text-white transition-colors"
                >
                  {dot(p.id, "agent")}
                  {p.label}
                </button>
              ))}
              {peers.length > 22 && (
                <p className="text-white/20 text-center py-1">
                  +{peers.length - 22} more
                </p>
              )}
            </div>
          </div>
        )}
        {node.kind !== "agent" && (
          <div>
            <p className="text-[9px] text-white/30 uppercase tracking-widest font-mono mb-1.5">
              {node.kind === "country"
                ? "People from here"
                : "People with this tag"}{" "}
              ({linked.length})
            </p>
            {linked.length === 0 && (
              <p className="text-white/20 italic">No agents in current view</p>
            )}
            <div className="space-y-0.5">
              {linked.slice(0, 15).map((p) => (
                <button
                  key={p.id}
                  onClick={() => onSelect(p.id)}
                  className="w-full text-left flex items-center gap-2 px-2 py-1 rounded hover:bg-white/5 text-white/50 hover:text-white transition-colors"
                >
                  {dot(p.id, "agent")}
                  {p.label}
                </button>
              ))}
              {linked.length > 30 && (
                <p className="text-white/20 text-center py-1">
                  +{linked.length - 30} more
                </p>
              )}
            </div>
          </div>
        )}
        {node.kind === "agent" &&
          (node.raw.agent_role || node.raw.agent_region) && (
            <div>
              <p className="text-[9px] text-white/30 uppercase tracking-widest font-mono mb-1.5">
                Details
              </p>
              <div className="space-y-1 font-mono text-[10px]">
                {node.raw.agent_role && (
                  <div className="flex gap-2">
                    <span className="text-white/25 w-14">role</span>
                    <span className="text-white/50">{node.raw.agent_role}</span>
                  </div>
                )}
                {node.raw.agent_region && (
                  <div className="flex gap-2">
                    <span className="text-white/25 w-14">region</span>
                    <span className="text-white/50">
                      {node.raw.agent_region}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
      </div>
    </div>
  );
}

// ─── Legend ───────────────────────────────────────────────────────────────────

function Legend({ theme }: { theme: "light" | "dark" }) {
  return (
    <div
      className={`absolute bottom-3 left-3 z-20 rounded-lg px-3 py-2.5 space-y-1.5 pointer-events-none ${
        theme === "light"
          ? "bg-white/90 border border-slate-300"
          : "bg-black/75 border border-white/10"
      }`}
    >
      {[
        {
          c: theme === "light" ? "#1f2937" : "#ffffff",
          label: "Agent (person)",
        },
        { c: "#fe6b36", label: "Country / Occupation (tag)" },
        {
          c: theme === "light" ? "#1f2937" : "#ffffff",
          label: "Hovered / focused",
        },
        { c: theme === "light" ? "#1f2937" : "#ffffff", label: "Selected" },
      ].map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ background: item.c }}
          />
          <span className="text-[9px] text-white/40 font-mono">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

interface GraphPanelProps {
  data: GraphRelationshipsResponse | null;
  theme?: "light" | "dark";
  loading?: boolean;
  selectedAgentId?: string | null;
  onSelectAgent?: (id: string) => void;
  onRefresh?: () => void;
  jiggle?: boolean;
}

export function GraphPanel({
  data,
  theme,
  loading = false,
  selectedAgentId,
  onSelectAgent,
  onRefresh,
  jiggle,
}: GraphPanelProps) {
  const resolvedTheme =
    theme ??
    (document.documentElement.classList.contains("light") ? "light" : "dark");
  const palette = React.useMemo(() => {
    if (resolvedTheme === "light") {
      return {
        nodeSelected: 0xfe6b36,
        edgeColor: 0xfe6b36,
        hoverNode: 0x111827,
        hoverEdge: 0x111827,
        labelColor: "rgba(17,24,39,0.82)",
        bgColor: 0xf5f5f4,
        gridColor: 0xd6d3d1,
        gridAlpha: 0.75,
      };
    }
    return {
      nodeSelected: 0xffffff,
      edgeColor: 0xfe6b36,
      hoverNode: 0xffffff,
      hoverEdge: 0xffffff,
      labelColor: "rgba(255,255,255,0.8)",
      bgColor: 0x000000,
      gridColor: 0x1a1a1a,
      gridAlpha: 0.6,
    };
  }, [resolvedTheme]);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const appRef = React.useRef<Application | null>(null);
  const worldRef = React.useRef<Container | null>(null);
  const bgGfxRef = React.useRef<Graphics | null>(null);
  const edgesGfxRef = React.useRef<Graphics | null>(null);
  const labelsGfxRef = React.useRef<Container | null>(null);
  const nodesGfxRef = React.useRef<Container | null>(null);
  const nodesMapRef = React.useRef<
    Map<string, { circle: Graphics; label: Text }>
  >(new Map());
  const simRef = React.useRef<ReturnType<typeof forceSimulation> | null>(null);
  const simNodesRef = React.useRef<SimNode[]>([]);
  const rafRef = React.useRef<number | null>(null);

  // Refs read by animation loop
  const zellEdgesRef = React.useRef<ZEdge[]>([]);
  const degreeRef = React.useRef<Map<string, number>>(new Map());
  const neighborRef = React.useRef<Map<string, Set<string>>>(new Map());
  const vpRef = React.useRef({ x: 0, y: 0, scale: 1 });
  const selectedRef = React.useRef<string | null>(null);
  const hoveredRef = React.useRef<string | null>(null);
  const sizeRef = React.useRef({ w: 800, h: 600 });
  const forcesRef = React.useRef({ ...DEFAULT_FORCES });
  const lastFocusedRef = React.useRef<string | null>(null);
  const focusIntensityRef = React.useRef(0);

  // React state (only for UI re-renders)
  const [selectedId, _setSelected] = React.useState<string | null>(null);
  const [hoveredId, setHovered] = React.useState<string | null>(null);
  const [stats, setStats] = React.useState({ nodes: 0, agents: 0, edges: 0 });
  const [forces, setForces] = React.useState({ ...DEFAULT_FORCES });

  const setSelected = (id: string | null) => {
    selectedRef.current = id;
    _setSelected(id);
  };

  // ── Derived graph data ─────────────────────────────────────────────────────
  const { zellNodes, zellEdges } = React.useMemo(() => {
    if (!data) return { zellNodes: [] as ZNode[], zellEdges: [] as ZEdge[] };
    const nodes: ZNode[] = data.nodes.map((n) => ({
      id: n.agent_id,
      label: n.agent_name,
      kind: inferKind(n),
      raw: n,
    }));
    const nodeIds = new Set(nodes.map((n) => n.id));
    const deg = new Map<string, number>();
    for (const e of data.edges) {
      deg.set(e.source, (deg.get(e.source) ?? 0) + 1);
      deg.set(e.target, (deg.get(e.target) ?? 0) + 1);
    }
    const kept = new Set(
      [...nodes]
        .sort((a, b) => (deg.get(b.id) ?? 0) - (deg.get(a.id) ?? 0))
        .slice(0, 400)
        .map((n) => n.id),
    );
    const edges: ZEdge[] = data.edges
      .filter(
        (e) =>
          kept.has(e.source) &&
          kept.has(e.target) &&
          e.source !== e.target &&
          nodeIds.has(e.source) &&
          nodeIds.has(e.target),
      )
      .map((e, i) => ({
        id: `e${i}`,
        source: e.source,
        target: e.target,
        kind: inferEdgeKind(e.relation_type),
        weight: e.weight ?? 1,
      }));
    return { zellNodes: nodes.filter((n) => kept.has(n.id)), zellEdges: edges };
  }, [data]);

  const nodeById = React.useMemo(() => {
    const m = new Map<string, ZNode>();
    zellNodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [zellNodes]);

  React.useEffect(() => {
    if (selectedAgentId !== undefined) setSelected(selectedAgentId ?? null);
  }, [selectedAgentId]);

  // Clear selection on Escape key
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelected(null);
        hoveredRef.current = null;
        setHovered(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Jiggle on open — brief alpha burst that decays naturally
  React.useEffect(() => {
    if (!jiggle) return;
    const sim = simRef.current;
    if (!sim) return;
    sim.alpha(0.22).alphaDecay(0.04).restart();
    const t = setTimeout(() => sim.stop(), 900);
    return () => clearTimeout(t);
  }, [jiggle]);

  // ── INIT PIXI — once on mount ──────────────────────────────────────────────
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const w = Math.max(300, container.clientWidth);
    const h = Math.max(200, container.clientHeight);
    sizeRef.current = { w, h };

    const app = new Application({
      width: w,
      height: h,
      backgroundColor: palette.bgColor,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
    });
    appRef.current = app;
    container.appendChild(app.view as HTMLCanvasElement);
    (app.view as HTMLCanvasElement).style.position = "absolute";
    (app.view as HTMLCanvasElement).style.inset = "0";

    const bgGfx = new Graphics();
    bgGfxRef.current = bgGfx;
    app.stage.addChild(bgGfx);
    drawDotGrid(bgGfx, w, h, palette.gridColor, palette.gridAlpha);

    const world = new Container();
    worldRef.current = world;
    app.stage.addChild(world);

    const edgesGfx = new Graphics();
    edgesGfxRef.current = edgesGfx;
    world.addChild(edgesGfx);
    const nodesGfx = new Container();
    nodesGfxRef.current = nodesGfx;
    world.addChild(nodesGfx);
    const labelsC = new Container();
    labelsGfxRef.current = labelsC;
    world.addChild(labelsC);

    const obs = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (!r || r.width === 0 || r.height === 0) return;
      const nw = Math.floor(r.width),
        nh = Math.floor(r.height);
      sizeRef.current = { w: nw, h: nh };
      app.renderer.resize(nw, nh);
      if (bgGfxRef.current)
        drawDotGrid(
          bgGfxRef.current,
          nw,
          nh,
          palette.gridColor,
          palette.gridAlpha,
        );
    });
    obs.observe(container);

    // ── Single persistent animation loop ──────────────────────────────────
    function tick() {
      simRef.current?.tick();

      const world = worldRef.current;
      const edgesGfx = edgesGfxRef.current;
      const nodesMap = nodesMapRef.current;
      const simNodes = simNodesRef.current;
      const edges = zellEdgesRef.current;
      const deg = degreeRef.current;
      const nbrs = neighborRef.current;
      const vp = vpRef.current;
      const selId = selectedRef.current;
      const hovId = hoveredRef.current;

      if (!world || !edgesGfx) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }

      world.position.set(vp.x, vp.y);
      world.scale.set(vp.scale);

      const currentFocus = selId ?? hovId;
      if (currentFocus) {
        lastFocusedRef.current = currentFocus;
        focusIntensityRef.current = Math.min(
          1,
          focusIntensityRef.current + 0.1,
        );
      } else {
        focusIntensityRef.current = Math.max(
          0,
          focusIntensityRef.current - 0.05,
        );
      }

      const focusNode = currentFocus ?? lastFocusedRef.current;
      const intensity = focusIntensityRef.current;
      const fNbrs = focusNode ? nbrs.get(focusNode) : null;

      // Build pos lookup
      const pos = new Map<string, SimNode>();
      for (const n of simNodes) pos.set(n.id, n);

      // ── Draw edges ───────────────────────────────────────────────────
      edgesGfx.clear();
      for (const e of edges) {
        const s = pos.get(e.source),
          t = pos.get(e.target);
        if (!s || !t) continue;
        const inFocus = focusNode
          ? fNbrs?.has(e.source) && fNbrs?.has(e.target)
          : true;
        const isHovEdge =
          focusNode && (e.source === focusNode || e.target === focusNode);

        const color = isHovEdge ? palette.hoverEdge : palette.edgeColor;

        // Neutral = 0.15, Focused = 0.8, Dimmed = 0.05
        const baseAlpha = 0.15;
        let targetAlpha = baseAlpha;
        if (intensity > 0 && focusNode) {
          if (isHovEdge) targetAlpha = 0.8;
          else if (inFocus) targetAlpha = 0.15;
          else targetAlpha = 0.05;
        }
        const alpha = baseAlpha + (targetAlpha - baseAlpha) * intensity;

        const thickness = isHovEdge ? 3 : 2;
        edgesGfx.lineStyle(thickness, color, alpha);
        edgesGfx.moveTo(s.x, s.y);
        edgesGfx.lineTo(t.x, t.y);
      }
      edgesGfx.lineStyle(0);

      // ── Draw nodes + labels ──────────────────────────────────────────
      for (const n of simNodes) {
        const entry = nodesMap.get(n.id);
        if (!entry) continue;
        const { circle, label } = entry;

        const d = deg.get(n.id) ?? 0;
        const r = getNodeSize(n.kind, d);
        const isSel = n.id === selId;
        const isHov = n.id === hovId;
        const isNbr = focusNode ? (fNbrs?.has(n.id) ?? false) : true;

        let color: number;
        if (isSel) color = palette.nodeSelected;
        else if (isHov) color = palette.hoverNode;
        else color = getNodeColor(n.kind, n.id, resolvedTheme);

        // Neutral alpha = 1, Dimmed = 0.1
        const targetNodeAlpha =
          intensity > 0 && focusNode && !isSel && !isHov && !isNbr ? 0.1 : 1;
        const nodeAlpha = 1 + (targetNodeAlpha - 1) * intensity;

        circle.clear();
        circle.position.set(n.x, n.y);

        // Glow ring for selected
        if (isSel) {
          circle.beginFill(0xffffff, 0.15 * nodeAlpha);
          circle.drawCircle(0, 0, r + 10);
          circle.beginFill(0xffffff, 0.3 * nodeAlpha);
          circle.drawCircle(0, 0, r + 5);
          circle.endFill();

          circle.lineStyle(2, palette.nodeSelected, 0.9 * nodeAlpha);
          circle.drawCircle(0, 0, r + 2);
          circle.lineStyle(0);
        } else if (isHov) {
          circle.lineStyle(1.5, palette.hoverNode, 0.7 * nodeAlpha);
          circle.drawCircle(0, 0, r + 3);
          circle.lineStyle(0);
        }
        circle.beginFill(color, nodeAlpha);
        circle.drawCircle(0, 0, r);
        circle.endFill();

        // Labels
        label.position.set(n.x, n.y + r + 4);
        label.visible = true;
        const targetLabelAlpha =
          intensity > 0 && focusNode
            ? isSel || isHov
              ? 1
              : isNbr
                ? 0.7
                : 0
            : 0.8;
        label.alpha = 0.8 + (targetLabelAlpha - 0.8) * intensity;
      }

      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      obs.disconnect();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      app.destroy(true, { children: true });
      appRef.current = null;
      worldRef.current = null;
    };
  }, [
    palette.bgColor,
    palette.gridAlpha,
    palette.gridColor,
    palette.edgeColor,
    palette.hoverEdge,
    palette.hoverNode,
    palette.nodeSelected,
    resolvedTheme,
  ]);

  // ── Rebuild simulation when data or forces change ──────────────────────────
  const rebuildSim = React.useCallback(
    (nodes: ZNode[], edges: ZEdge[], f: typeof DEFAULT_FORCES) => {
      const world = worldRef.current;
      const nodesGfx = nodesGfxRef.current;
      const labelsC = labelsGfxRef.current;
      if (!world || !nodesGfx || !labelsC) return;

      zellEdgesRef.current = edges;

      const deg = new Map<string, number>();
      for (const e of edges) {
        deg.set(e.source, (deg.get(e.source) ?? 0) + 1);
        deg.set(e.target, (deg.get(e.target) ?? 0) + 1);
      }
      degreeRef.current = deg;

      const nbr = new Map<string, Set<string>>();
      for (const n of nodes) nbr.set(n.id, new Set([n.id]));
      for (const e of edges) {
        nbr.get(e.source)?.add(e.target);
        nbr.get(e.target)?.add(e.source);
      }
      neighborRef.current = nbr;

      // Clear old sprites
      nodesMapRef.current.forEach(({ circle, label }) => {
        try {
          nodesGfx.removeChild(circle);
          circle.destroy();
        } catch {}
        try {
          labelsC.removeChild(label);
          label.destroy();
        } catch {}
      });
      nodesMapRef.current.clear();
      simRef.current?.stop();

      if (nodes.length === 0) {
        simNodesRef.current = [];
        setStats({ nodes: 0, agents: 0, edges: 0 });
        return;
      }

      setStats({
        nodes: nodes.length,
        agents: nodes.filter((n) => n.kind === "agent").length,
        edges: edges.length,
      });

      const { w, h } = sizeRef.current;
      const radius = Math.min(w, h) * 0.34;

      const simNodes: SimNode[] = nodes.map((n, i) => ({
        ...n,
        x:
          w / 2 +
          Math.cos((i / nodes.length) * Math.PI * 2) * radius +
          (Math.random() - 0.5) * 30,
        y:
          h / 2 +
          Math.sin((i / nodes.length) * Math.PI * 2) * radius +
          (Math.random() - 0.5) * 30,
        vx: 0,
        vy: 0,
      }));
      simNodesRef.current = simNodes;

      const links = edges.map((e) => ({ source: e.source, target: e.target }));

      // Build simulation — exact logseq layout! params from pixi.cljs
      const sim = forceSimulation(simNodes as any)
        .force(
          "link",
          forceLink(links as any)
            .id((d: any) => d.id)
            .distance(f.linkDist)
            .links(links as any),
        )
        .force(
          "charge",
          forceManyBody()
            .distanceMin(1)
            .distanceMax(f.chargeRange)
            .theta(0.5)
            .strength((d: any) =>
              d.kind === "agent" ? f.chargeStrength * 0.1 : f.chargeStrength,
            ),
        )
        .force(
          "collision",
          forceCollide()
            .radius((d: any) => {
              const degStr = degreeRef.current.get(d.id) ?? 0;
              return getNodeSize(d.kind, degStr) + 4;
            })
            .iterations(2),
        )
        .force("x", forceX(0).strength(0.02))
        .force("y", forceY(0).strength(0.02))
        .force("center", forceCenter(w / 2, h / 2))
        .velocityDecay(0.5);

      sim.stop();
      for (let i = 0; i < 300; i++) sim.tick(); // warm up
      simRef.current = sim;

      // Create sprites after warm-up
      for (const n of simNodes) {
        const circle = new Graphics();
        nodesGfx.addChild(circle);

        const label = new Text(n.label, {
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: 12, // exact logseq font size
          fill: palette.labelColor,
          align: "center",
        });
        label.anchor.set(0.5, 0);
        labelsC.addChild(label);
        nodesMapRef.current.set(n.id, { circle, label });
      }

      // Fit viewport
      let mnX = Infinity,
        mxX = -Infinity,
        mnY = Infinity,
        mxY = -Infinity;
      for (const n of simNodes) {
        mnX = Math.min(mnX, n.x);
        mxX = Math.max(mxX, n.x);
        mnY = Math.min(mnY, n.y);
        mxY = Math.max(mxY, n.y);
      }
      const pad = 80,
        cw = Math.max(1, mxX - mnX + pad * 2),
        ch = Math.max(1, mxY - mnY + pad * 2);
      const s = Math.max(0.06, Math.min(2.5, Math.min(w / cw, h / ch)));
      const cx = (mnX + mxX) / 2,
        cy = (mnY + mxY) / 2;
      vpRef.current = { scale: s, x: w / 2 - cx * s, y: h / 2 - cy * s };
    },
    [palette.labelColor, resolvedTheme],
  );

  React.useEffect(() => {
    rebuildSim(zellNodes, zellEdges, forces);
  }, [zellNodes, zellEdges, rebuildSim]);

  // Forces change — just restart simulation with new params (don't rebuild sprites)
  const applyForces = React.useCallback((newF: typeof DEFAULT_FORCES) => {
    forcesRef.current = newF;
    const sim = simRef.current;
    if (!sim) return;
    const { w, h } = sizeRef.current;
    sim.force(
      "link",
      forceLink(
        zellEdgesRef.current.map((e) => ({
          source: e.source,
          target: e.target,
        })) as any,
      )
        .id((d: any) => d.id)
        .distance(newF.linkDist),
    );
    sim.force(
      "charge",
      forceManyBody()
        .distanceMin(1)
        .distanceMax(newF.chargeRange)
        .theta(0.5)
        .strength(newF.chargeStrength),
    );
    sim.force("center", forceCenter(w / 2, h / 2));
    sim.alpha(0.5).restart();
    // Let it settle then stop
    setTimeout(() => sim.stop(), 3000);
  }, []);

  const handleForceChange = (k: keyof typeof DEFAULT_FORCES, v: number) => {
    const nf = { ...forces, [k]: v };
    setForces(nf);
    applyForces(nf);
  };
  const handleForceReset = () => {
    setForces({ ...DEFAULT_FORCES });
    applyForces({ ...DEFAULT_FORCES });
  };

  // ── Pointer interaction ────────────────────────────────────────────────────
  const panStart = React.useRef<{
    sx: number;
    sy: number;
    ox: number;
    oy: number;
  } | null>(null);
  const dragNode = React.useRef<SimNode | null>(null);
  const didMove = React.useRef(false);

  function c2w(cx: number, cy: number) {
    const el = containerRef.current!;
    const rect = el.getBoundingClientRect();
    const vp = vpRef.current;
    const { w, h } = sizeRef.current;
    const sx = ((cx - rect.left) / rect.width) * w,
      sy = ((cy - rect.top) / rect.height) * h;
    return {
      wx: (sx - vp.x) / Math.max(0.01, vp.scale),
      wy: (sy - vp.y) / Math.max(0.01, vp.scale),
    };
  }

  function hitNode(wx: number, wy: number): SimNode | null {
    const nodes = simNodesRef.current,
      deg = degreeRef.current;
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const r = getNodeSize(n.kind, deg.get(n.id) ?? 0) + 4;
      if (Math.hypot(wx - n.x, wy - n.y) <= r) return n;
    }
    return null;
  }

  const onPointerDown = (e: React.PointerEvent) => {
    const { wx, wy } = c2w(e.clientX, e.clientY);
    const hit = hitNode(wx, wy);
    didMove.current = false;
    if (hit) {
      dragNode.current = hit;
      hit.fx = hit.x;
      hit.fy = hit.y;
      simRef.current?.alphaTarget(0.15).restart();
    } else {
      panStart.current = {
        sx: e.clientX,
        sy: e.clientY,
        ox: vpRef.current.x,
        oy: vpRef.current.y,
      };
    }
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const { wx, wy } = c2w(e.clientX, e.clientY);
    didMove.current = true;
    if (dragNode.current) {
      dragNode.current.fx = wx;
      dragNode.current.fy = wy;
      return;
    }
    if (panStart.current) {
      vpRef.current = {
        ...vpRef.current,
        x: panStart.current.ox + (e.clientX - panStart.current.sx),
        y: panStart.current.oy + (e.clientY - panStart.current.sy),
      };
      return;
    }
    const hit = hitNode(wx, wy);
    const hid = hit?.id ?? null;
    if (hid !== hoveredRef.current) {
      hoveredRef.current = hid;
      setHovered(hid);
    }
  };
  const onPointerUp = (e: React.PointerEvent) => {
    const { wx, wy } = c2w(e.clientX, e.clientY);
    if (dragNode.current) {
      const n = dragNode.current;
      if (
        !didMove.current ||
        Math.hypot(wx - (n.fx ?? n.x), wy - (n.fy ?? n.y)) < 6
      ) {
        const next = selectedRef.current === n.id ? null : n.id;
        setSelected(next);
        if (n.kind === "agent" && next) onSelectAgent?.(n.id);
      }
      n.fx = null;
      n.fy = null;
      simRef.current?.alphaTarget(0);
      dragNode.current = null;
    } else {
      panStart.current = null;
      if (!didMove.current) {
        setSelected(null);
      }
    }
  };
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const el = containerRef.current!;
    const rect = el.getBoundingClientRect();
    const { w, h } = sizeRef.current;
    const sx = ((e.clientX - rect.left) / rect.width) * w,
      sy = ((e.clientY - rect.top) / rect.height) * h;
    const vp = vpRef.current;
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    const ns = Math.max(0.05, Math.min(8, vp.scale * factor));
    const wx = (sx - vp.x) / vp.scale,
      wy = (sy - vp.y) / vp.scale;
    vpRef.current = { scale: ns, x: sx - wx * ns, y: sy - wy * ns };
  };
  const fitView = () => {
    const nodes = simNodesRef.current;
    if (!nodes.length) return;
    const { w, h } = sizeRef.current;
    let mnX = Infinity,
      mxX = -Infinity,
      mnY = Infinity,
      mxY = -Infinity;
    for (const n of nodes) {
      mnX = Math.min(mnX, n.x);
      mxX = Math.max(mxX, n.x);
      mnY = Math.min(mnY, n.y);
      mxY = Math.max(mxY, n.y);
    }
    const pad = 80,
      s = Math.max(
        0.05,
        Math.min(
          2.5,
          Math.min(
            w / Math.max(1, mxX - mnX + pad * 2),
            h / Math.max(1, mxY - mnY + pad * 2),
          ),
        ),
      );
    vpRef.current = {
      scale: s,
      x: w / 2 - ((mnX + mxX) / 2) * s,
      y: h / 2 - ((mnY + mxY) / 2) * s,
    };
  };

  const selectedNode = selectedId ? (nodeById.get(selectedId) ?? null) : null;

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-hidden select-none ${
        resolvedTheme === "light" ? "bg-[#f5f5f4]" : "bg-black"
      }`}
      style={{
        cursor: dragNode.current
          ? "grabbing"
          : panStart.current
            ? "grabbing"
            : hoveredId
              ? "pointer"
              : "grab",
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onWheel={onWheel}
    >
      {loading && (
        <div
          className={`absolute inset-0 flex flex-col items-center justify-center z-50 ${
            resolvedTheme === "light" ? "bg-white/85" : "bg-black/80"
          }`}
        >
          <div className="w-10 h-10 border-2 border-[#6366f1]/30 border-t-[#6366f1] rounded-full animate-spin mb-3" />
          <p className="text-[10px] text-[#6366f1] font-mono uppercase tracking-widest animate-pulse">
            Building graph…
          </p>
        </div>
      )}

      {!loading && stats.nodes === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 z-10 pointer-events-none">
          <Network className="w-14 h-14 text-foreground/20" />
          <div className="text-center">
            <p className="text-foreground/70 text-sm font-medium">
              No graph data
            </p>
            <p className="text-muted-foreground text-xs mt-1">
              Spawn agents then refresh
            </p>
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="pointer-events-auto flex items-center gap-2 px-4 py-2 rounded-lg border border-[#6366f1]/40 text-[#6366f1] text-xs font-bold uppercase tracking-widest hover:bg-[#6366f1]/10 transition-colors"
            >
              <RefreshCcw className="w-3.5 h-3.5" />
              Build Graph
            </button>
          )}
        </div>
      )}

      {/* Toolbar — always visible */}
      <div
        className={`absolute top-3 left-1/2 -translate-x-1/2 flex items-center gap-1 rounded-xl px-2 py-1.5 z-20 pointer-events-auto ${
          resolvedTheme === "light"
            ? "bg-white/90 border border-slate-300"
            : "bg-black/80 border border-white/10"
        }`}
      >
        <button
          onClick={() => {
            vpRef.current = {
              ...vpRef.current,
              scale: Math.min(8, vpRef.current.scale * 1.2),
            };
          }}
          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-black/5 transition-colors"
          title="Zoom in"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => {
            vpRef.current = {
              ...vpRef.current,
              scale: Math.max(0.05, vpRef.current.scale * 0.83),
            };
          }}
          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-black/5 transition-colors"
          title="Zoom out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <div className="w-px h-4 bg-border mx-0.5" />
        <button
          onClick={fitView}
          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-black/5 transition-colors"
          title="Fit"
        >
          <LocateFixed className="w-3.5 h-3.5" />
        </button>
        <div className="w-px h-4 bg-border mx-0.5" />
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-black/5 transition-colors"
            title="Rebuild"
          >
            <RefreshCcw className="w-3.5 h-3.5" />
          </button>
        )}
        <div className="w-px h-4 bg-border mx-0.5" />
        <span className="text-[9px] text-muted-foreground font-mono px-1">
          {stats.nodes > 0
            ? `${stats.agents}p · ${stats.nodes - stats.agents}meta · ${
                stats.edges
              }e`
            : "no data"}
        </span>
      </div>

      {!selectedNode && <Legend theme={resolvedTheme} />}

      {/* Force controls — always visible */}
      <ForcePanel
        linkDist={forces.linkDist}
        chargeStrength={forces.chargeStrength}
        chargeRange={forces.chargeRange}
        onChange={handleForceChange}
        onReset={handleForceReset}
        theme={resolvedTheme}
        sidebarOpen={!!selectedNode}
      />

      <Sidebar
        node={selectedNode}
        nodes={zellNodes}
        edges={zellEdges}
        onClose={() => setSelected(null)}
        theme={resolvedTheme}
        onSelect={(id) => {
          setSelected(id);
          const n = nodeById.get(id);
          if (n?.kind === "agent") onSelectAgent?.(id);
        }}
      />
    </div>
  );
}
