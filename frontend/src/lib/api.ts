// Get API base URL - works both in dev and production
// Override by setting VITE_API_BASE in .env (e.g. VITE_API_BASE=https://api.myapp.com)
const getApiBase = (): string => {
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE as string;
  }
  if (typeof window !== "undefined" && window.location) {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000`;
  }
  return "http://localhost:8000";
};

export const API_BASE = getApiBase();

// ── Health ────────────────────────────────────────────────
export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchLLMHealth(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/llm/health`);
  if (!res.ok) throw new Error(`LLM health failed: ${res.statusText}`);
  return res.json();
}

export async function fetchSystemStats(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/system/stats`);
  if (!res.ok) throw new Error(`System stats failed: ${res.statusText}`);
  return res.json();
}

// ── Bootstrap & Cities ────────────────────────────────────
export async function fetchBootstrap(): Promise<{
  data: { cities: any[]; profiles: any[] };
  cached: boolean;
}> {
  const res = await fetch(`${API_BASE}/api/bootstrap`);
  if (!res.ok) throw new Error(`Bootstrap failed: ${res.statusText}`);
  return res.json();
}

export async function postBootstrap(count = 1800, withAgents = false) {
  const res = await fetch(`${API_BASE}/api/bootstrap`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ count, with_agents: withAgents }),
  });
  if (!res.ok) throw new Error(`Bootstrap POST failed: ${res.statusText}`);
  return res.json();
}

export async function fetchCities() {
  const res = await fetch(`${API_BASE}/api/cities`);
  if (!res.ok) throw new Error(`Cities failed: ${res.statusText}`);
  return res.json();
}

export async function clearCache() {
  const res = await fetch(`${API_BASE}/api/cache/clear`, { method: "POST" });
  if (!res.ok) throw new Error(`Cache clear failed: ${res.statusText}`);
  return res.json();
}

// ── Agents ────────────────────────────────────────────────
export async function fetchAgents(region?: string, role?: string) {
  const params = new URLSearchParams();
  if (region) params.set("region", region);
  if (role) params.set("role", role);
  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/agents${query}`);
  if (!res.ok) throw new Error(`Agents fetch failed: ${res.statusText}`);
  return res.json();
}

export async function createAgent(data: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/api/agent/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Create agent failed: ${res.statusText}`);
  return res.json();
}

export async function getAgent(agentId: string) {
  const res = await fetch(`${API_BASE}/api/agent/${agentId}`);
  if (!res.ok) throw new Error(`Get agent failed: ${res.statusText}`);
  return res.json();
}

export async function agentDecide(
  agentId: string,
  worldState?: Record<string, unknown>,
  scenario?: string,
) {
  const res = await fetch(`${API_BASE}/api/agent/${agentId}/decide`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ world_state: worldState, scenario }),
  });
  if (!res.ok) throw new Error(`Agent decide failed: ${res.statusText}`);
  return res.json();
}

// ── Persona ───────────────────────────────────────────────
export async function generatePersona(
  agentId: string,
  metadata: Record<string, unknown>,
) {
  const res = await fetch(`${API_BASE}/api/agent/generate-persona`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, metadata }),
  });
  if (!res.ok) throw new Error(`Generate persona failed: ${res.statusText}`);
  return res.json();
}

export async function getAgentPersona(agentId: string) {
  const res = await fetch(`${API_BASE}/api/agent/${agentId}/persona`);
  if (!res.ok) throw new Error(`Get persona failed: ${res.statusText}`);
  return res.json();
}

export async function getAgentPersonaSection(agentId: string, section: string) {
  const res = await fetch(
    `${API_BASE}/api/agent/${agentId}/persona/${section}`,
  );
  if (!res.ok) throw new Error(`Get persona section failed: ${res.statusText}`);
  return res.json();
}

export async function getAgentPersonaFiles(agentId: string) {
  const res = await fetch(`${API_BASE}/api/agent/${agentId}/persona-files`);
  if (!res.ok) throw new Error(`Get persona files failed: ${res.statusText}`);
  return res.json();
}

export async function generateAgentPersonaLLM(
  agentId: string,
  metadata?: Record<string, unknown>,
) {
  const res = await fetch(`${API_BASE}/api/agent/${agentId}/generate-persona`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(metadata ? { agent_metadata: metadata } : {}),
  });
  if (!res.ok)
    throw new Error(`LLM persona generation failed: ${res.statusText}`);
  return res.json();
}

// ── Batch Persona Generation ──────────────────────────────
export interface BatchAgent {
  id: string;
  name: string;
  age: number;
  ethnicity: string;
  region?: string;
  role: string;
  role_label?: string;
  personality_archetype: string;
}

export async function spawnAgentsBatch(
  agents: BatchAgent[],
  maxConcurrent = 3,
) {
  const res = await fetch(`${API_BASE}/api/agents/generate-personas-batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agents, max_concurrent: maxConcurrent }),
  });
  if (!res.ok) throw new Error(`Batch spawn failed: ${res.statusText}`);
  return res.json();
}

export async function getBatchStatus(): Promise<{
  status: string;
  stats: {
    total: number;
    completed: number;
    failed: number;
    pending: number;
    in_progress: number;
    completion_percent: number;
    avg_time_per_agent: number;
    estimated_time_remaining: number;
  };
  jobs_total: number;
}> {
  const res = await fetch(`${API_BASE}/api/agents/generation-status`);
  if (!res.ok) throw new Error(`Batch status failed: ${res.statusText}`);
  return res.json();
}

// ── Atlas Graph + Workbench ──────────────────────────────
export interface GraphNode {
  agent_id: string;
  agent_name: string;
  agent_role?: string;
  agent_region?: string;
  node_type?: "agent" | "meta";
  meta_category?: string;
  labels?: string[];
  attributes?: Record<string, unknown>;
  properties?: Record<string, unknown>;
  backlinks_count?: number;
  inbound_links?: string[];
  outbound_links?: string[];
}

export interface GraphEdge {
  source: string;
  source_name?: string;
  target: string;
  target_name?: string;
  relation_type: string;
  relation_subtype?:
    | "interaction"
    | "property"
    | "tag"
    | "peer"
    | "demographic"
    | "work"
    | "schematic"
    | string;
  bidirectional?: boolean;
  properties?: Record<string, unknown>;
  weight: number;
  count?: number;
  context?: string;
  timestamp?: string;
}

export interface GraphRelationshipsResponse {
  run_id: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    node_count: number;
    edge_count: number;
    relation_types: Record<string, number>;
    node_types?: Record<string, number>;
    occupation_peer_edges?: number;
    max_occupation_group?: number;
    warnings?: string[];
  };
}

export async function fetchGraphRelationships(runId?: string) {
  const params = new URLSearchParams();
  if (runId) params.set("run_id", runId);
  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/graph/relationships${query}`);
  if (!res.ok) throw new Error(`Graph fetch failed: ${res.statusText}`);
  return res.json() as Promise<GraphRelationshipsResponse>;
}

export async function buildGraphRelationships(runId?: string) {
  const res = await fetch(`${API_BASE}/api/graph/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(runId ? { run_id: runId } : {}),
  });
  if (!res.ok) throw new Error(`Graph build failed: ${res.statusText}`);
  return res.json();
}

export async function sendWorkbenchQuery(payload: {
  query: string;
  run_id?: string | null;
  top_k?: number;
}) {
  const res = await fetch(`${API_BASE}/api/workbench/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Workbench chat failed: ${res.statusText}`);
  return res.json() as Promise<{
    run_id: string | null;
    response: string;
    sources: Array<{
      score?: number;
      snippet?: string;
      meta?: Record<string, unknown>;
    }>;
    related_agents: GraphNode[];
    related_edges: GraphEdge[];
  }>;
}

// ── Reports ───────────────────────────────────────────────
export async function downloadRunReport(
  runId: string,
  format: "pdf" | "html" = "pdf",
): Promise<Blob> {
  const res = await fetch(
    `${API_BASE}/api/runs/${encodeURIComponent(runId)}/report?format=${format}`,
  );
  if (!res.ok) {
    throw new Error(`Report export failed: ${res.status} ${res.statusText}`);
  }
  return res.blob();
}
