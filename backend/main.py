from __future__ import annotations

from typing import Any, Optional
import asyncio
import logging
import json
import psutil
import os
import time
import re
from collections import defaultdict
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.services.cache import TTLCache
from app.services.profile_generator import build_profile_pool
from app.services.persona_generator import generate_agent_persona
from app.services.llm import init_llm, get_llm, llm_health
from app.services.llm_persona_generator import (
    generate_and_save_persona,
    reset_corpus_cache,
)
from app.services.batch_generator import get_batch_generator, reset_batch_generator
from app.services.search import (
    semantic_search,
    fuzzy_search,
    reload_index_from_db,
    get_search_index,
)
from app.simulation.agent import Agent
from app.simulation.memory import create_memory_system
from app.simulation.executor import execute_agent_decision
from app.simulation.store import init_storage, save_agent, load_agent, list_agents
from app.simulation.db import (
    init_db,
    list_simulation_runs,
    get_simulation_run,
    get_run_responses,
    get_run_evolution,
    get_agent_history,
    get_search_entries,
    get_run_agent_nodes,
    get_run_relationships,
    save_agent_relationship,
)


def load_landmarks():
    _landmarks = []
    try:
        states_path = os.path.join(
            os.path.dirname(__file__), "app", "data", "States.json"
        )
        if os.path.exists(states_path):
            with open(states_path, "r", encoding="utf-8") as f:
                for state in json.load(f):
                    if state.get("latitude") and state.get("longitude"):
                        try:
                            _landmarks.append(
                                {
                                    "name": state.get("name") or "Unknown",
                                    "country": state.get("country_name") or "Unknown",
                                    "state": state.get("name") or "Unknown",
                                    "continent": "Unknown",
                                    "region": "Unknown",
                                    "lon": float(state.get("longitude")),
                                    "lat": float(state.get("latitude")),
                                }
                            )
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to load States.json: {e}")
    if not _landmarks:
        from app.data.landmarks import LANDMARKS as FALLBACK

        _landmarks = FALLBACK
    return _landmarks


LANDMARKS = load_landmarks()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Zell Backend", version="0.1.0")
init_db()


def _parse_cors_origins(value: Optional[str]) -> list[str]:
    if value:
        parsed = [origin.strip() for origin in value.split(",") if origin.strip()]
        if parsed:
            return parsed
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS")),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

cache = TTLCache(ttl_seconds=300)


# Initialize services on startup
@app.on_event("startup")
async def startup():
    """Initialize LLM and storage services on startup."""
    logger.info("Initializing Zell backend services...")

    # Initialize storage (ephemeral mode for MVP)
    init_storage()
    logger.info("Storage service initialized")

    # Initialize LLM (loads config from environment)
    try:
        init_llm()
        health = llm_health()
        logger.info(f"LLM service initialized: {health}")
    except Exception as e:
        logger.error(f"LLM initialization failed (non-blocking): {e}")
        logger.info("Continuing without LLM. Agent decisions will use fallback mode.")

    # Reload TF-IDF search index from persisted DB entries
    try:
        count = reload_index_from_db()
        logger.info(f"Search index restored: {count} documents")
    except Exception as e:
        logger.error(f"Search index reload failed (non-blocking): {e}")


def build_bootstrap_payload() -> dict[str, Any]:
    logger.info("Building bootstrap payload...")
    profiles = build_profile_pool(LANDMARKS, count=1000)
    import random

    sampled_cities = (
        random.sample(LANDMARKS, min(1000, len(LANDMARKS))) if LANDMARKS else []
    )
    logger.info(
        f"Bootstrap payload ready: {len(profiles)} profiles, {len(sampled_cities)} cities"
    )
    return {"cities": sampled_cities, "profiles": profiles}


def _resolve_run_id(run_id: Optional[str]) -> Optional[str]:
    """Resolve a run_id or fall back to the most recent run."""
    if run_id:
        return run_id
    runs = list_simulation_runs()
    if not runs:
        return None
    return runs[0]["run_id"]


def _normalize_meta_value(value: Any, fallback: str = "Unknown") -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _age_band(age: Optional[int]) -> str:
    if age is None:
        return "Unknown"
    if age < 20:
        return "<20"
    if age < 30:
        return "20s"
    if age < 40:
        return "30s"
    if age < 50:
        return "40s"
    if age < 60:
        return "50s"
    return "60+"


def _slugify(value: Any, fallback: str = "unknown") -> str:
    text = str(value).strip().lower() if value is not None else ""
    text = re.sub(r"[^a-z0-9_\-/]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def _meta_node_id(category: str, value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_\-/]+", "_", value.strip().lower())
    return f"meta:{category}:{slug}"


def _parse_meta_node_id(node_id: str) -> tuple[Optional[str], Optional[str]]:
    if not node_id.startswith("meta:"):
        return None, None
    parts = node_id.split(":", 2)
    if len(parts) < 3:
        return None, None
    category = parts[1]
    raw_value = parts[2].replace("_", " ")
    return category, raw_value


def _meta_node_payload(node_id: str) -> dict[str, Any]:
    category, value = _parse_meta_node_id(node_id)
    label_kind = "tag" if (category and "tag" in category) else "property"
    return {
        "agent_id": node_id,
        "agent_name": value or node_id,
        "node_type": "meta",
        "meta_category": category,
        "labels": ["meta", label_kind, category or "metadata"],
        "attributes": {"category": category, "value": value, "kind": label_kind},
        "properties": {"category": category or "metadata", "kind": label_kind},
    }


def _attach_link_indexes(
    nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> None:
    linked: dict[str, dict[str, set[str]]] = {
        n["agent_id"]: {"inbound": set(), "outbound": set()} for n in nodes
    }
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in linked and target:
            linked[source]["outbound"].add(target)
        if target in linked and source:
            linked[target]["inbound"].add(source)

    for node in nodes:
        node_id = node["agent_id"]
        inbound = sorted(linked.get(node_id, {}).get("inbound", set()))
        outbound = sorted(linked.get(node_id, {}).get("outbound", set()))
        node["inbound_links"] = inbound
        node["outbound_links"] = outbound
        node["backlinks_count"] = len(inbound)
        node.setdefault("properties", {})
        if node.get("node_type") == "meta":
            node["properties"].setdefault("meta_category", node.get("meta_category"))


def _collect_live_agent_metadata() -> dict[str, dict[str, Any]]:
    """Collect richer agent metadata from in-memory store for graph enrichment."""
    live: dict[str, dict[str, Any]] = {}
    for agent in list_agents():
        role = _normalize_meta_value(getattr(agent, "role", None), "Unknown")
        country = _normalize_meta_value(
            getattr(agent, "country", None) or getattr(agent, "region", None),
            "Unknown",
        )
        live[agent.id] = {
            "name": _normalize_meta_value(getattr(agent, "name", None), "Unknown"),
            "region": _normalize_meta_value(getattr(agent, "region", None), "Unknown"),
            "country": country,
            "role": role,
            "occupation": role,
            "image_job_tag": f"#job/{_slugify(role)}",
            "ethnicity": _normalize_meta_value(
                getattr(agent, "ethnicity", None), "Unknown"
            ),
            "archetype": _normalize_meta_value(
                getattr(agent, "personality_archetype", None), "Unknown"
            ),
            "age": getattr(agent, "age", None),
        }
    return live


def _build_fallback_interconnect_edges(
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build lightweight synthetic edges so the atlas graph is never disconnected.
    Used only when no inferred interaction edges exist yet.
    """
    by_region: dict[str, list[dict[str, Any]]] = {}
    for n in nodes:
        region = n.get("agent_region") or n.get("region") or "Unknown"
        by_region.setdefault(region, []).append(n)

    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    # Region-local mesh: each node links to at most 2 peers.
    for group in by_region.values():
        for i, src in enumerate(group):
            neighbors = group[i + 1 : i + 3]
            for target in neighbors:
                pair = (src["agent_id"], target["agent_id"])
                if pair in seen:
                    continue
                seen.add(pair)
                edges.append(
                    {
                        "source": src["agent_id"],
                        "source_name": src.get("agent_name", src["agent_id"]),
                        "target": target["agent_id"],
                        "target_name": target.get("agent_name", target["agent_id"]),
                        "relation_type": "coexists",
                        "weight": 0.6,
                        "count": 1,
                        "context": f"Both agents are active in {src.get('agent_region') or 'the same region'}.",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    # Ensure global connectivity by linking region representatives.
    reps = [group[0] for group in by_region.values() if group]
    for i in range(len(reps) - 1):
        src = reps[i]
        target = reps[i + 1]
        pair = (src["agent_id"], target["agent_id"])
        if pair in seen:
            continue
        edges.append(
            {
                "source": src["agent_id"],
                "source_name": src.get("agent_name", src["agent_id"]),
                "target": target["agent_id"],
                "target_name": target.get("agent_name", target["agent_id"]),
                "relation_type": "coexists",
                "weight": 0.5,
                "count": 1,
                "context": "Regional bridge edge to keep the graph interconnected.",
                "timestamp": datetime.now().isoformat(),
            }
        )

    return edges


def _build_metadata_link_edges(
    nodes: list[dict[str, Any]],
    live_meta: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Build deeper graph edges for schematic/demographic/work metadata.
    This includes Logseq-like links:
    - Person note -> property nodes (country, occupation)
    - Person note -> job tag nodes (image-job tag)
    - Person <-> person links for same occupation (full mesh)
    """
    if not nodes:
        return [], {
            "occupation_peer_edges": 0,
            "max_occupation_group": 0,
            "warnings": [],
        }

    edges: list[dict[str, Any]] = []

    by_country: dict[str, list[str]] = defaultdict(list)
    by_occupation: dict[str, list[str]] = defaultdict(list)
    by_archetype: dict[str, list[str]] = defaultdict(list)
    by_ethnicity: dict[str, list[str]] = defaultdict(list)
    by_age_group: dict[str, list[str]] = defaultdict(list)

    for n in nodes:
        agent_id = n["agent_id"]
        name = n.get("agent_name") or agent_id
        meta = live_meta.get(agent_id, {})

        country = _normalize_meta_value(
            meta.get("country") or meta.get("region") or n.get("agent_region")
        )
        occupation = _normalize_meta_value(
            meta.get("occupation") or meta.get("role") or n.get("agent_role")
        )
        archetype = _normalize_meta_value(
            meta.get("archetype") or n.get("attributes", {}).get("archetype")
        )
        ethnicity = _normalize_meta_value(
            meta.get("ethnicity") or n.get("attributes", {}).get("ethnicity")
        )
        age = meta.get("age") or n.get("attributes", {}).get("age")

        # Age group derivation
        if age and str(age).isdigit():
            age_int = int(age)
            if age_int < 20:
                age_group = "Youth"
            elif age_int < 35:
                age_group = "Young Adult"
            elif age_int < 55:
                age_group = "Adult"
            else:
                age_group = "Elder"
        else:
            age_group = "Unknown Age"

        image_job_tag = _normalize_meta_value(
            meta.get("image_job_tag"), f"#job/{_slugify(occupation)}"
        )

        by_country[country].append(agent_id)
        by_occupation[occupation].append(agent_id)
        by_archetype[archetype].append(agent_id)
        by_ethnicity[ethnicity].append(agent_id)
        by_age_group[age_group].append(agent_id)

        metadata_links = [
            ("country", country, "property_country", 0.98, "property"),
            ("occupation", occupation, "property_occupation", 0.96, "property"),
            ("archetype", archetype, "property_archetype", 0.92, "property"),
            ("ethnicity", ethnicity, "property_ethnicity", 0.90, "property"),
            ("age_group", age_group, "property_age_group", 0.88, "property"),
            ("image_job_tag", image_job_tag, "tag_image_job", 0.94, "tag"),
        ]

        for category, value, rel_type, weight, subtype in metadata_links:
            meta_id = _meta_node_id(category, value)
            edges.append(
                {
                    "source": agent_id,
                    "source_name": name,
                    "target": meta_id,
                    "target_name": value,
                    "relation_type": rel_type,
                    "relation_subtype": subtype,
                    "weight": weight,
                    "count": 1,
                    "bidirectional": False,
                    "properties": {"category": category, "value": value},
                    "context": f"{name} links to {category.replace('_', ' ')}: {value}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    # We REMOVED the O(N^2) full-mesh peer edges because they create an unreadable "hairball".
    # The property nodes (hub nodes) naturally cluster similar agents together via D3 force physics.

    warnings: list[str] = []

    return edges, {
        "occupation_peer_edges": 0,
        "max_occupation_group": 0,
        "warnings": warnings,
    }


def _build_live_graph_payload(
    live_meta: dict[str, dict[str, Any]],
    run_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build graph payload directly from live in-memory agents."""
    live_agents = list_agents()
    nodes = []
    for a in live_agents:
        meta = live_meta.get(a.id, {})
        country = _normalize_meta_value(meta.get("country") or a.region)
        occupation = _normalize_meta_value(meta.get("occupation") or a.role)
        image_job_tag = _normalize_meta_value(
            meta.get("image_job_tag"), f"#job/{_slugify(occupation)}"
        )
        nodes.append(
            {
                "agent_id": a.id,
                "agent_name": a.name,
                "agent_role": a.role,
                "agent_region": a.region,
                "node_type": "agent",
                "labels": ["agent", "note", "person"],
                "attributes": {
                    "region": a.region,
                    "country": country,
                    "role": a.role,
                    "occupation": occupation,
                    "ethnicity": getattr(a, "ethnicity", "Unknown"),
                    "archetype": getattr(a, "personality_archetype", "Unknown"),
                    "age": getattr(a, "age", None),
                },
                "properties": {
                    "country": country,
                    "occupation": occupation,
                    "image_job_tag": image_job_tag,
                },
            }
        )

    metadata_edges, metadata_diag = _build_metadata_link_edges(nodes, live_meta)
    edges = _build_fallback_interconnect_edges(nodes) + metadata_edges

    relation_types: dict[str, int] = {}
    for e in edges:
        relation_types[e["relation_type"]] = (
            relation_types.get(e["relation_type"], 0) + 1
        )

    node_ids = {n["agent_id"] for n in nodes}
    node_types = {"agent": len(nodes)}
    for edge in edges:
        for endpoint in (edge["source"], edge["target"]):
            if not endpoint.startswith("meta:") or endpoint in node_ids:
                continue
            category, value = _parse_meta_node_id(endpoint)
            nodes.append(_meta_node_payload(endpoint))
            node_ids.add(endpoint)
            node_types["meta"] = node_types.get("meta", 0) + 1

    _attach_link_indexes(nodes, edges)

    return {
        "run_id": run_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "relation_types": relation_types,
            "node_types": node_types,
            "occupation_peer_edges": metadata_diag.get("occupation_peer_edges", 0),
            "max_occupation_group": metadata_diag.get("max_occupation_group", 0),
            "warnings": metadata_diag.get("warnings", []),
        },
    }


def _build_graph_payload(run_id: Optional[str]) -> dict[str, Any]:
    """Build normalized graph payload consumed by Atlas view."""
    resolved_run_id = _resolve_run_id(run_id)

    live_meta = _collect_live_agent_metadata()

    if not resolved_run_id:
        return _build_live_graph_payload(live_meta, run_id=None)

    raw_nodes = get_run_agent_nodes(resolved_run_id)
    raw_edges = get_run_relationships(resolved_run_id)

    # Run exists but has no persisted response rows yet: fall back to live agent graph.
    if not raw_nodes:
        return _build_live_graph_payload(live_meta, run_id=resolved_run_id)

    nodes = []
    for n in raw_nodes:
        meta = live_meta.get(n["agent_id"], {})
        country = _normalize_meta_value(meta.get("country") or n.get("agent_region"))
        occupation = _normalize_meta_value(
            meta.get("occupation") or n.get("agent_role")
        )
        image_job_tag = _normalize_meta_value(
            meta.get("image_job_tag"), f"#job/{_slugify(occupation)}"
        )
        nodes.append(
            {
                "agent_id": n["agent_id"],
                "agent_name": n.get("agent_name") or n["agent_id"],
                "agent_role": n.get("agent_role"),
                "agent_region": n.get("agent_region"),
                "node_type": "agent",
                "labels": ["agent", "note", "person"],
                "attributes": {
                    "region": n.get("agent_region"),
                    "country": country,
                    "role": n.get("agent_role"),
                    "occupation": occupation,
                    "ethnicity": meta.get("ethnicity"),
                    "archetype": meta.get("archetype"),
                    "age": meta.get("age"),
                },
                "properties": {
                    "country": country,
                    "occupation": occupation,
                    "image_job_tag": image_job_tag,
                },
            }
        )
    node_ids = {n["agent_id"] for n in nodes}

    edge_buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for e in raw_edges:
        key = (e["source_agent_id"], e["target_agent_id"], e["relation_type"])
        if key not in edge_buckets:
            relation_type = e["relation_type"]
            if relation_type.startswith("property_"):
                relation_subtype = "property"
            elif relation_type.startswith("tag_"):
                relation_subtype = "tag"
            elif "peer" in relation_type:
                continue  # Skip all O(N^2) peer edges to stop graph unreadability
            else:
                relation_subtype = None
            edge_buckets[key] = {
                "source": e["source_agent_id"],
                "source_name": e.get("source_agent_name") or e["source_agent_id"],
                "target": e["target_agent_id"],
                "target_name": e.get("target_agent_name") or e["target_agent_id"],
                "relation_type": relation_type,
                "relation_subtype": relation_subtype,
                "weight": float(e.get("weight") or 1.0),
                "count": 1,
                "bidirectional": relation_type == "same_occupation_peer",
                "context": e.get("context") or "",
                "timestamp": e.get("timestamp"),
            }
        else:
            edge_buckets[key]["weight"] += float(e.get("weight") or 1.0)
            edge_buckets[key]["count"] += 1
            if e.get("context"):
                edge_buckets[key]["context"] = e["context"]
            if e.get("timestamp"):
                edge_buckets[key]["timestamp"] = e["timestamp"]

    edges = list(edge_buckets.values())
    if not edges:
        edges = _build_fallback_interconnect_edges(nodes)

    for edge in edges:
        rel_type = str(edge.get("relation_type") or "")
        if rel_type.startswith("property_") and not edge.get("properties"):
            edge["properties"] = {
                "value": edge.get("target_name") or edge.get("target")
            }
        elif rel_type.startswith("tag_") and not edge.get("properties"):
            edge["properties"] = {"tag": edge.get("target_name") or edge.get("target")}

    # Attach metadata nodes discovered through persisted metadata links.
    for edge in edges:
        for endpoint in (edge["source"], edge["target"]):
            if endpoint in node_ids:
                continue
            if endpoint.startswith("meta:"):
                category, value = _parse_meta_node_id(endpoint)
                nodes.append(_meta_node_payload(endpoint))
            else:
                nodes.append(
                    {
                        "agent_id": endpoint,
                        "agent_name": endpoint,
                        "node_type": "meta",
                        "meta_category": "unknown",
                        "labels": ["meta", "unknown"],
                        "attributes": {
                            "category": "unknown",
                            "value": endpoint,
                            "kind": "property",
                        },
                        "properties": {"category": "unknown", "kind": "property"},
                    }
                )
            node_ids.add(endpoint)

    relation_types: dict[str, int] = {}
    for e in edges:
        relation_types[e["relation_type"]] = (
            relation_types.get(e["relation_type"], 0) + 1
        )

    node_types: dict[str, int] = {}
    for n in nodes:
        node_type = n.get("node_type", "agent")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    occupation_peer_edges = sum(
        1 for e in edges if e.get("relation_type") == "same_occupation_peer"
    )
    warnings: list[str] = []
    if occupation_peer_edges > 25000:
        warnings.append(
            "Dense same-occupation peer mesh detected; use layer filters to focus property/tag links."
        )

    _attach_link_indexes(nodes, edges)

    return {
        "run_id": resolved_run_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "relation_types": relation_types,
            "node_types": node_types,
            "occupation_peer_edges": occupation_peer_edges,
            "warnings": warnings,
        },
    }


@app.get("/")
def defualt():
    return {"status": "maja"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cities")
def get_cities() -> dict[str, Any]:
    cached = cache.get("cities")
    if cached is not None:
        return {"cities": cached, "cached": True}
    cache.set("cities", LANDMARKS)
    return {"cities": LANDMARKS, "cached": False}


@app.get("/api/bootstrap")
def get_bootstrap() -> dict[str, Any]:
    cached = cache.get("bootstrap")
    if cached is not None:
        logger.info("[GET /api/bootstrap] Served from cache")
        return {"data": cached, "cached": True}

    logger.info("[GET /api/bootstrap] Generating fresh bootstrap payload...")
    payload = build_bootstrap_payload()
    cache.set("bootstrap", payload)
    logger.info("[GET /api/bootstrap] Payload cached and returned")
    return {"data": payload, "cached": False}


@app.post("/api/cache/clear")
def clear_cache() -> dict[str, Any]:
    cleared = cache.clear()
    return {"clearedEntries": cleared}


# ==================== AGENT ENDPOINTS ====================


@app.get("/api/llm/health")
def get_llm_health() -> dict[str, Any]:
    """Check LLM service health."""
    health = llm_health()
    return {**health, "timestamp": datetime.now().isoformat()}


@app.get("/api/system/stats")
def get_system_stats() -> dict[str, Any]:
    """Get real-time system performance data."""
    try:
        # Get LLM health
        llm = llm_health()

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        # Backend process metrics
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()

        return {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "llm": {
                "status": llm.get("status", "unknown"),
                "model": llm.get("model", "unknown"),
                "provider": llm.get("provider", "unknown"),
            },
            "hardware": {
                "cpu_usage": cpu_percent,
                "ram_usage": memory.percent,
                "ram_total_gb": round(memory.total / (1024**3), 2),
                "ram_used_gb": round(memory.used / (1024**3), 2),
            },
            "backend": {
                "memory_mb": round(mem_info.rss / (1024 * 1024), 2),
                "uptime_seconds": round(time.time() - process.create_time(), 1),
            },
        }
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/agent/compile-prompt")
def compile_agent_prompt_endpoint(request: dict[str, Any]) -> dict[str, Any]:
    """
    Compile agent persona + runtime context into system prompt.

    Request body:
    {
        "agent_metadata": {
            "name": "Alice",
            "age": 35,
            "ethnicity": "African",
            "region": "Africa",
            "role": "Farmer",
            "personality_archetype": "Guardian"
        },
        "runtime_context": {
            "world": {"time": "...", "season": "spring"},
            "agent": {"location": "fields", "resources": {...}}
        }
    }
    """
    try:
        agent_meta = request.get("agent_metadata", {})
        runtime_ctx = request.get("runtime_context", {})

        # Generate persona files dynamically
        persona_files = generate_agent_persona(agent_meta)

        # Simple compilation: concatenate sections
        system_prompt = "\n\n---\n\n".join(persona_files.values())

        # Add runtime context at the end
        if runtime_ctx:
            context_str = json.dumps(runtime_ctx, indent=2)
            system_prompt += f"\n\n# RUNTIME CONTEXT\n{context_str}"

        return {
            "agent_name": agent_meta.get("name"),
            "system_prompt": system_prompt,
            "persona_sections": list(persona_files.keys()),
        }
    except Exception as e:
        logger.error(f"Prompt compilation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/create")
def create_agent(request: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new agent with generated persona.

    Request body:
    {
        "name": "Alice",
        "age": 35,
        "ethnicity": "African",
        "region": "Africa",
        "role": "Farmer",
        "personality_archetype": "Guardian",
        "location": "farm_settlement"
    }
    """
    try:
        reset_corpus_cache()

        # Create agent with dynamically generated persona
        agent = Agent(
            name=request.get("name", "Unnamed"),
            age=request.get("age", 30),
            ethnicity=request.get("ethnicity", "Mixed"),
            region=request.get("region", "Europe"),
            role=request.get("role", "Scholar"),
            role_label=request.get("role_label", "Job"),
            personality_archetype=request.get("personality_archetype", "Pragmatist"),
            location=request.get("location"),
        )

        # Create memory system
        memory = create_memory_system(agent.id)

        # Save to storage
        save_agent(agent, memory)

        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "metadata": agent.get_metadata(),
            "state": agent.get_state(),
            "persona_sections": list((agent.persona_files or {}).keys()),
        }
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/generate-persona")
def generate_persona_endpoint(request: dict[str, Any]):
    """Ensure persona exists for an agent, generating it via LLM if missing."""
    try:
        agent_id = request.get("agent_id")
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required")
        metadata = request.get("metadata", {})

        from app.simulation.db import get_persona_sections

        sections = get_persona_sections(agent_id)

        if not sections:
            logger.info(
                f"Generating NEW persona for agent {agent_id} ({metadata.get('name')})..."
            )
            from app.services.llm_persona_generator import generate_and_save_persona

            reset_corpus_cache()
            generate_and_save_persona(metadata, agent_id)
            sections = get_persona_sections(agent_id)

        return {"agent_id": agent_id, "sections": sections}
    except Exception as e:
        logger.error(f"Error ensuring persona for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/{agent_id}/persona")
def get_agent_persona(agent_id: str):
    """Fetch generated persona sections for a specific agent."""
    try:
        from app.simulation.db import get_persona_sections

        sections = get_persona_sections(agent_id)
        if not sections:
            # Try to load from disk
            from app.services.llm_persona_generator import LLMPersonaGenerator

            sections = LLMPersonaGenerator.load_persona_files(agent_id) or {}

        return {"agent_id": agent_id, "sections": sections}
    except Exception as e:
        logger.error(f"Error fetching persona for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/{agent_id}")
def get_agent(agent_id: str) -> dict[str, Any]:
    """Get agent metadata and current state."""
    agent = load_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": agent.id,
        "metadata": agent.get_metadata(),
        "state": agent.get_state(),
    }


@app.post("/api/agent/{agent_id}/decide")
def agent_decide(
    agent_id: str, request: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Trigger one decision cycle for agent (perceive → think → act).

    Optional request body:
    {
        "world_state": {
            "time": "...",
            "season": "spring",
            "alerts": [...],
            "opportunities": [...]
        },
        "scenario": "You notice strangers arriving. What do you do?"
    }
    """
    try:
        agent = load_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Create memory system if needed
        memory = create_memory_system(agent_id)

        # Get world state from request or use default
        request_data = request or {}
        world_state = request_data.get(
            "world_state",
            {
                "time": "morning",
                "season": "spring",
                "region": agent.region,
            },
        )
        scenario = request_data.get("scenario")

        # Execute decision cycle
        decision_result = execute_agent_decision(agent, memory, world_state, scenario)

        # Save updated agent and memory
        save_agent(agent, memory)

        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "decision": decision_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Decision execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
def list_all_agents(
    region: Optional[str] = None, role: Optional[str] = None
) -> dict[str, Any]:
    """List all agents, optionally filtered by region or role."""
    agents = list_agents(region=region, role=role)
    return {
        "count": len(agents),
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "region": a.region,
                "location": a.location,
                "age": a.age,
            }
            for a in agents
        ],
    }


@app.post("/api/bootstrap")
def post_bootstrap(request: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Enhanced bootstrap: Generate profiles + initialize agents with personas.
    """
    try:
        request_data = request or {}
        profile_count = request_data.get("count", 1800)
        with_agents = request_data.get("with_agents", False)

        logger.info(
            f"[POST /api/bootstrap] Request received: count={profile_count}, with_agents={with_agents}"
        )

        cached = cache.get("bootstrap")
        if cached is not None:
            logger.info("[POST /api/bootstrap] Found cached bootstrap")
            result = {"data": cached, "cached": True}
            if not with_agents:
                return result

        logger.info(
            f"[POST /api/bootstrap] Building pool of {profile_count} profiles..."
        )
        profiles = build_profile_pool(LANDMARKS, count=profile_count)
        import random

        sampled_cities = (
            random.sample(LANDMARKS, min(profile_count, len(LANDMARKS)))
            if LANDMARKS
            else []
        )
        payload = {"cities": sampled_cities, "profiles": profiles}

        # If requested, create agents with personas from profiles
        if with_agents:
            logger.info("[POST /api/bootstrap] Initializing agents from profiles...")
            reset_corpus_cache()
            agents_data = []
            for profile in profiles[:20]:  # Limit to first 20 for MVP
                try:
                    agent = Agent(
                        name=profile["name"],
                        age=profile["age"],
                        ethnicity=profile["race"],
                        region=profile.get("region", "Europe"),
                        role=profile["roleValue"],
                        role_label=profile["roleLabel"],
                    )
                    memory = create_memory_system(agent.id)
                    save_agent(agent, memory)

                    agents_data.append(
                        {
                            "id": agent.id,
                            "name": agent.name,
                            "metadata": agent.get_metadata(),
                        }
                    )
                except Exception as e:
                    logger.error(f"[POST /api/bootstrap] Failed to create agent: {e}")

            payload["agents"] = agents_data
            logger.info(f"[POST /api/bootstrap] Created {len(agents_data)} agents")

        cache.set("bootstrap", payload)
        logger.info("[POST /api/bootstrap] Bootstrap complete")
        return {"data": payload, "cached": False}

    except Exception as e:
        logger.error(f"[POST /api/bootstrap] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LLM PERSONA GENERATION ====================


@app.post("/api/agent/{agent_id}/generate-persona")
def generate_agent_persona_llm(
    agent_id: str, request: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Generate LLM-based persona files for a single agent.
    Creates SOUL.md, IDENTITY.md, VOICE.md, BRAIN.md, SKILLS.md, DRIVES.md

    Request body (optional):
    {
        "agent_metadata": {
            "name": "Alice",
            "age": 35,
            "ethnicity": "African",
            "region": "Africa",
            "role": "Farmer",
            "personality_archetype": "Guardian"
        }
    }
    """
    try:
        request_data = request or {}
        agent_metadata = request_data.get("agent_metadata", {})

        if not agent_metadata:
            # Try to load from existing agent
            agent = load_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            agent_metadata = agent.get_metadata()

        # Generate personas via LLM
        reset_corpus_cache()
        sections = generate_and_save_persona(agent_metadata, agent_id)

        return {
            "agent_id": agent_id,
            "status": "generated",
            "sections": list(sections.keys()),
            "section_sizes": {k: len(v) for k, v in sections.items()},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Persona generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/generate-personas-batch")
async def generate_agents_personas_batch(request: dict[str, Any]) -> dict[str, Any]:
    """
    Generate LLM-based personas for multiple agents (1000+).
    Processes agents with rate limiting and concurrent workers.

    Request body:
    {
        "agents": [
            {
                "id": "agent_1",
                "name": "Alice",
                "age": 35,
                "ethnicity": "African",
                "region": "Africa",
                "role": "Farmer",
                "personality_archetype": "Guardian"
            },
            ...
        ],
        "max_concurrent": 3,  # Max concurrent LLM calls (default: 3)
        "dry_run": false       # If true, just validate without generating
    }
    """
    try:
        agents = request.get("agents", [])
        max_concurrent = request.get("max_concurrent", 3)
        dry_run = request.get("dry_run", False)

        if not agents:
            raise HTTPException(status_code=400, detail="No agents provided")

        if len(agents) > 10000:
            raise HTTPException(
                status_code=400, detail="Too many agents. Max 10,000 per request."
            )

        logger.info(
            f"Starting batch generation for {len(agents)} agents (dry_run={dry_run})"
        )
        reset_corpus_cache()

        from app.simulation.agent import Agent
        from app.simulation.memory import create_memory_system
        from app.simulation.store import save_agent

        for a_dict in agents:
            try:
                temp_agent = Agent(
                    name=a_dict.get("name", "Unnamed"),
                    age=a_dict.get("age", 30),
                    ethnicity=a_dict.get("ethnicity", "Mixed"),
                    region=a_dict.get("region", "Europe"),
                    role=a_dict.get("role", "Scholar"),
                    role_label=a_dict.get("role_label", "Job"),
                    personality_archetype=a_dict.get(
                        "personality_archetype", "Pragmatist"
                    ),
                )
                # Override assigned UUID to match the frontend spawned UUID
                if a_dict.get("id"):
                    temp_agent.id = a_dict["id"]

                # Save into backend ephemeral store so 404 errors don't occur when hitting /decide
                save_agent(temp_agent, create_memory_system(temp_agent.id))
            except Exception as e:
                logger.error(f"Failed to prime agent in memory: {e}")

        if dry_run:
            return {
                "status": "dry_run_complete",
                "agents_count": len(agents),
                "message": "Validation passed. Ready to generate.",
            }

        # Reset the singleton so status polling reflects this fresh run
        generator = reset_batch_generator(max_concurrent=max_concurrent)

        # Start workers
        await generator.start()

        # Add all jobs
        jobs = await generator.add_batch(agents)
        logger.info(f"Added {len(jobs)} generation jobs")

        # Run generation in the background so we can return immediately
        # and let the frontend poll /api/agents/generation-status for progress
        async def _run_and_stop():
            try:
                await generator.stop()
                logger.info("Background batch generation complete")
            except Exception as e:
                logger.error(f"Background batch generation error: {e}")

        asyncio.create_task(_run_and_stop())

        return {
            "status": "batch_started",
            "agents_count": len(agents),
            "message": "Generation started in background. Poll /api/agents/generation-status for progress.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/generation-status")
def get_batch_generation_status() -> dict[str, Any]:
    """Get status of ongoing batch generation."""
    try:
        generator = get_batch_generator()
        stats = generator.get_stats()

        return {
            "status": "ok",
            "stats": stats,
            "jobs_total": len(generator.jobs),
        }
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/start")
async def start_simulation(request: dict[str, Any]) -> dict[str, Any]:
    """
    Trigger God Mode N-Cycle generic simulation loop.
    Request body:
    {
        "event": "Solar Eclipse",
        "cycles": 3,
        "year": 2026
    }
    """
    from app.simulation.orchestrator import get_orchestrator

    try:
        event = request.get("event", "Mysterious humming from the sky")
        cycles = int(request.get("cycles", 1))
        year = int(request.get("year", 2026))

        orch = get_orchestrator()
        # Fire and forget background task
        asyncio.create_task(orch.run_simulation(event, cycles, year))

        return {
            "status": "simulation_started",
            "event": event,
            "cycles": cycles,
            "year": year,
        }
    except Exception as e:
        logger.error(f"Simulation start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/status")
def get_simulation_status() -> dict[str, Any]:
    """Get status of the God Mode simulation."""
    try:
        from app.simulation.orchestrator import get_orchestrator

        orch = get_orchestrator()
        return orch.get_status()
    except Exception as e:
        logger.error(f"Simulation status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GRAPH / ATLAS / WORKBENCH ====================


@app.get("/api/graph/relationships")
def graph_relationships(run_id: Optional[str] = Query(None)) -> dict[str, Any]:
    """
    Atlas graph payload used by frontend Graph Relationship Visualization.
    Returns nodes/edges from inferred interactions; falls back to soft interconnect mesh.
    """
    try:
        return _build_graph_payload(run_id)
    except Exception as e:
        logger.error(f"Graph relationships error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/build")
def graph_build(request: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Build a deeper relationship graph by persisting:
    - interaction fallback edges
    - schematic links
    - demographic links
    - work links
    - metadata-driven similarity links
    Safe to call repeatedly; inserts only missing edges per (source,target,type).
    """
    try:
        req = request or {}
        run_id = _resolve_run_id(req.get("run_id"))
        if not run_id:
            payload = _build_graph_payload(None)
            return {
                "status": "ok",
                "run_id": None,
                "inserted_edges": 0,
                "inserted_by_type": {},
                "graph": payload,
                "note": "No simulation run found; returned live-agent graph fallback",
            }

        nodes = get_run_agent_nodes(run_id)
        existing = get_run_relationships(run_id)
        existing_pairs = {
            (e["source_agent_id"], e["target_agent_id"], e["relation_type"])
            for e in existing
        }

        live_meta = _collect_live_agent_metadata()
        synthetic = _build_fallback_interconnect_edges(nodes)
        metadata_edges, _metadata_diag = _build_metadata_link_edges(nodes, live_meta)
        to_insert = synthetic + metadata_edges

        inserted = 0
        inserted_by_type: dict[str, int] = {}

        for edge in to_insert:
            key = (edge["source"], edge["target"], edge["relation_type"])
            if key in existing_pairs:
                continue
            save_agent_relationship(
                run_id=run_id,
                source_agent_id=edge["source"],
                source_agent_name=edge["source_name"],
                target_agent_id=edge["target"],
                target_agent_name=edge["target_name"],
                relation_type=edge["relation_type"],
                weight=float(edge.get("weight") or 0.5),
                context=edge.get("context") or "auto-generated co-presence edge",
                cycle=None,
            )
            inserted += 1
            existing_pairs.add(key)
            rel_type = edge["relation_type"]
            inserted_by_type[rel_type] = inserted_by_type.get(rel_type, 0) + 1

        payload = _build_graph_payload(run_id)
        return {
            "status": "ok",
            "run_id": run_id,
            "inserted_edges": inserted,
            "inserted_by_type": inserted_by_type,
            "graph": payload,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workbench/chat")
def workbench_chat(request: dict[str, Any]) -> dict[str, Any]:
    """
    General chat/workbench endpoint over simulation graph + semantic response index.
    """
    try:
        query = (request.get("query") or "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")

        run_id = _resolve_run_id(request.get("run_id"))
        top_k = int(request.get("top_k", 8))
        top_k = max(1, min(top_k, 30))

        if not run_id:
            return {
                "run_id": None,
                "response": "No simulation run exists yet. Start a simulation to populate atlas relationships.",
                "sources": [],
                "related_agents": [],
                "related_edges": [],
            }

        graph = _build_graph_payload(run_id)
        hits = semantic_search(query, run_id=run_id, top_k=top_k)
        sources = [
            {
                "score": h.get("score"),
                "snippet": h.get("snippet"),
                "meta": h.get("meta", {}),
            }
            for h in hits
        ]

        matched_agent_ids = {
            h.get("meta", {}).get("agent_id")
            for h in hits
            if h.get("meta", {}).get("agent_id")
        }

        lowered_query = query.lower()
        for node in graph["nodes"]:
            name = (node.get("agent_name") or "").lower()
            if name and re.search(rf"\b{re.escape(name)}\b", lowered_query):
                matched_agent_ids.add(node["agent_id"])

        related_edges = [
            e
            for e in graph["edges"]
            if e["source"] in matched_agent_ids or e["target"] in matched_agent_ids
        ][:25]
        related_agents = [
            n for n in graph["nodes"] if n["agent_id"] in matched_agent_ids
        ][:20]

        relation_mix = graph.get("stats", {}).get("relation_types", {})
        relation_summary = (
            ", ".join(
                f"{k}: {v}"
                for k, v in sorted(relation_mix.items(), key=lambda kv: -kv[1])
            )
            or "no relation types detected"
        )

        base_summary = (
            f"Atlas run {run_id} contains {graph['stats']['node_count']} agents and "
            f"{graph['stats']['edge_count']} relationship edges. "
            f"Relation mix -> {relation_summary}."
        )

        if sources:
            top_snippets = "\n".join(
                f"- {s['snippet']}" for s in sources[:3] if s.get("snippet")
            )
            base_summary += f"\n\nMost relevant evidence:\n{top_snippets}"

        llm_answer = None
        try:
            llm = get_llm()
            if llm and llm_health().get("status") == "healthy":
                llm_answer = llm.generate(
                    "You are a concise simulation analyst for an agent relationship atlas.",
                    (
                        f"Question: {query}\n\n"
                        f"Context:\n{base_summary}\n\n"
                        f"Return a direct answer grounded in this context."
                    ),
                    max_tokens=280,
                    temperature=0.2,
                )
        except Exception:
            llm_answer = None

        return {
            "run_id": run_id,
            "response": llm_answer or base_summary,
            "sources": sources,
            "related_agents": related_agents,
            "related_edges": related_edges,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workbench chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/{agent_id}/persona-files")
def get_agent_persona_files(agent_id: str) -> dict[str, Any]:
    """Get generated persona files for an agent."""
    try:
        from app.services.llm_persona_generator import LLMPersonaGenerator

        sections = LLMPersonaGenerator.load_persona_files(agent_id)

        if not sections:
            raise HTTPException(status_code=404, detail="Persona files not found")

        return {
            "agent_id": agent_id,
            "sections": {k: len(v) for k, v in sections.items()},
            "total_size": sum(len(v) for v in sections.values()),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Persona files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/{agent_id}/persona/{section}")
def get_agent_persona_section(agent_id: str, section: str) -> dict[str, Any]:
    """Download a specific persona section (SOUL, VOICE, etc.)."""
    try:
        from app.services.llm_persona_generator import LLMPersonaGenerator

        sections = LLMPersonaGenerator.load_persona_files(agent_id)

        if not sections:
            raise HTTPException(status_code=404, detail="Persona files not found")

        section_upper = section.upper()
        if section_upper not in sections:
            raise HTTPException(status_code=404, detail=f"Section {section} not found")

        return {
            "agent_id": agent_id,
            "section": section_upper,
            "content": sections[section_upper],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Section retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD ENDPOINTS ====================


@app.get("/api/dashboard/runs")
def dashboard_list_runs() -> dict[str, Any]:
    """
    List all simulation runs, newest first.
    Returns metadata: run_id, event_name, year, cycles, agent_count, status, timestamps.
    """
    try:
        runs = list_simulation_runs()
        return {"runs": runs, "count": len(runs)}
    except Exception as e:
        logger.error(f"Dashboard runs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/runs/{run_id}")
def dashboard_get_run(run_id: str) -> dict[str, Any]:
    """Get metadata for a single simulation run."""
    run = get_simulation_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/dashboard/runs/{run_id}/responses")
def dashboard_run_responses(
    run_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    cycle: Optional[int] = Query(None),
    region: Optional[str] = Query(None),
    migrating_only: bool = Query(False),
    less_trusting_only: bool = Query(False),
    q: Optional[str] = Query(None),
) -> dict[str, Any]:
    """
    Get paginated agent responses for a run.
    Optionally filter by cycle, region, migrating_only, less_trusting_only, or keyword search (q).
    """
    try:
        run = get_simulation_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if q and q.strip():
            # Semantic search within this run
            semantic_results = semantic_search(q.strip(), run_id=run_id, top_k=per_page)
            # Also get the full response rows for matched doc ids
            matched_ids = {r["meta"]["response_id"] for r in semantic_results}

            # Fetch all responses and filter to matched
            all_responses = get_run_responses(run_id, page=1, per_page=10000)
            filtered = [
                {
                    **resp,
                    "_score": next(
                        (
                            r["score"]
                            for r in semantic_results
                            if r["meta"].get("response_id") == resp["id"]
                        ),
                        0,
                    ),
                }
                for resp in all_responses["responses"]
                if resp["id"] in matched_ids
            ]
            filtered.sort(key=lambda x: -x["_score"])
            return {
                "run": run,
                "query": q,
                "search_mode": "semantic",
                "total": len(filtered),
                "responses": filtered[:per_page],
            }

        result = get_run_responses(
            run_id=run_id,
            page=page,
            per_page=per_page,
            cycle=cycle,
            region=region,
            migrating_only=migrating_only,
            less_trusting_only=less_trusting_only,
        )
        return {"run": run, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard responses error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/runs/{run_id}/evolution")
def dashboard_run_evolution(run_id: str) -> dict[str, Any]:
    """
    Return per-cycle aggregated statistics for a run:
    agent count, migration count, top emotions, regions affected.
    """
    try:
        run = get_simulation_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        evolution = get_run_evolution(run_id)
        return {"run": run, "cycles": evolution}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard evolution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/search")
def dashboard_global_search(
    q: str = Query(..., min_length=1),
    run_id: Optional[str] = Query(None),
    mode: str = Query("semantic", regex="^(semantic|fuzzy|hybrid)$"),
    top_k: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """
    Global search across all runs (or a specific run).
    mode: 'semantic' (cosine TF-IDF), 'fuzzy' (difflib), or 'hybrid' (both merged).
    """
    try:
        q = q.strip()
        results: list[dict[str, Any]] = []

        if mode in ("semantic", "hybrid"):
            semantic_hits = semantic_search(q, run_id=run_id, top_k=top_k)
            for hit in semantic_hits:
                hit["search_type"] = "semantic"
            results.extend(semantic_hits)

        if mode in ("fuzzy", "hybrid"):
            entries = get_search_entries(run_id=run_id)
            fuzzy_hits = fuzzy_search(
                q, entries, text_field="text_content", top_k=top_k
            )
            for hit in fuzzy_hits:
                hit["search_type"] = "fuzzy"
                # Normalise fuzzy score to match semantic score field
                hit["score"] = hit.pop("_fuzzy_score", 0.0)
            results.extend(fuzzy_hits)

        # Deduplicate by response_id if hybrid
        if mode == "hybrid":
            seen: set[Any] = set()
            deduped = []
            for r in sorted(results, key=lambda x: -x.get("score", 0)):
                rid = r.get("meta", {}).get("response_id") or r.get("response_id")
                if rid not in seen:
                    seen.add(rid)
                    deduped.append(r)
            results = deduped[:top_k]

        return {
            "query": q,
            "mode": mode,
            "run_id": run_id,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Dashboard search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/agents/{agent_id}/history")
def dashboard_agent_history(agent_id: str) -> dict[str, Any]:
    """
    All responses ever recorded for a single agent across all simulation runs.
    """
    try:
        history = get_agent_history(agent_id)
        return {"agent_id": agent_id, "count": len(history), "history": history}
    except Exception as e:
        logger.error(f"Dashboard agent history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/stats")
def dashboard_stats() -> dict[str, Any]:
    """High-level stats: total runs, total responses, search index size."""
    try:
        runs = list_simulation_runs()
        idx_size = get_search_index().size()
        total_responses = sum(
            r.get("agent_count", 0) * r.get("cycles", 1) for r in runs
        )
        return {
            "total_runs": len(runs),
            "completed_runs": sum(1 for r in runs if r["status"] == "completed"),
            "total_responses_estimate": total_responses,
            "search_index_size": idx_size,
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
