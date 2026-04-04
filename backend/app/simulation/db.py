import sqlite3
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path("agents.db")


def _ensure_agent_responses_columns(cursor: sqlite3.Cursor) -> None:
    """Backfill columns for older local DBs without destructive migrations."""
    cursor.execute("PRAGMA table_info(agent_responses)")
    existing = {row[1] for row in cursor.fetchall()}

    if "trust_shift" not in existing:
        cursor.execute("ALTER TABLE agent_responses ADD COLUMN trust_shift TEXT")
    if "trust_change" not in existing:
        cursor.execute(
            "ALTER TABLE agent_responses ADD COLUMN trust_change TEXT DEFAULT 'none'"
        )
    if "trust_target" not in existing:
        cursor.execute("ALTER TABLE agent_responses ADD COLUMN trust_target TEXT")
    if "is_less_trusting" not in existing:
        cursor.execute(
            "ALTER TABLE agent_responses ADD COLUMN is_less_trusting INTEGER DEFAULT 0"
        )


def init_db():
    """Initialize SQLite database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Original: persona sections
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS persona_sections (
            agent_id TEXT,
            section_name TEXT,
            content TEXT,
            PRIMARY KEY (agent_id, section_name)
        )
    """
    )

    # Original: agent metadata
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            ethnicity TEXT,
            role TEXT,
            region TEXT,
            personality_archetype TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # NEW: one row per simulation run
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_runs (
            run_id TEXT PRIMARY KEY,
            event_name TEXT NOT NULL,
            year INTEGER,
            cycles INTEGER,
            agent_count INTEGER,
            status TEXT DEFAULT 'running',
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """
    )

    # NEW: one row per agent response per cycle per run
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            agent_name TEXT,
            agent_role TEXT,
            agent_region TEXT,
            cycle INTEGER NOT NULL,
            thoughts TEXT,
            emotional_state TEXT,
            action TEXT,
            plan TEXT,
            migration_intent TEXT,
            trust_shift TEXT,
            trust_change TEXT DEFAULT 'none',
            trust_target TEXT,
            is_less_trusting INTEGER DEFAULT 0,
            is_migrating INTEGER DEFAULT 0,
            migration_destination TEXT,
            raw_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
        )
    """
    )

    _ensure_agent_responses_columns(cursor)

    # NEW: TF-IDF search index
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS search_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            response_id INTEGER NOT NULL,
            agent_id TEXT NOT NULL,
            text_content TEXT NOT NULL,
            FOREIGN KEY (response_id) REFERENCES agent_responses(id)
        )
    """
    )

    # NEW: directed relationship edges between agents (graph backbone)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            cycle INTEGER,
            source_agent_id TEXT NOT NULL,
            source_agent_name TEXT,
            target_agent_id TEXT NOT NULL,
            target_agent_name TEXT,
            relation_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            context TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
        )
    """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_responses_run ON agent_responses(run_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_responses_agent ON agent_responses(agent_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_run ON search_index(run_id)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_relationships_run ON agent_relationships(run_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_relationships_source ON agent_relationships(source_agent_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_relationships_target ON agent_relationships(target_agent_id)"
    )

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH.absolute()}")


# ─── Persona helpers (unchanged) ────────────────────────────────────────────


def save_persona_section(agent_id: str, section_name: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO persona_sections (agent_id, section_name, content) VALUES (?, ?, ?)",
        (agent_id, section_name, content),
    )
    conn.commit()
    conn.close()


def get_persona_sections(agent_id: str) -> Dict[str, str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT section_name, content FROM persona_sections WHERE agent_id = ?",
        (agent_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def save_agent_metadata(agent_id: str, metadata: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO agents (id, name, age, ethnicity, role, region, personality_archetype) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            agent_id,
            metadata.get("name"),
            metadata.get("age"),
            metadata.get("ethnicity"),
            metadata.get("role"),
            metadata.get("region"),
            metadata.get("personality_archetype"),
        ),
    )
    conn.commit()
    conn.close()


# ─── Simulation run helpers ──────────────────────────────────────────────────


def create_simulation_run(
    event_name: str, year: int, cycles: int, agent_count: int
) -> str:
    """Create a new simulation run record and return its run_id."""
    run_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO simulation_runs (run_id, event_name, year, cycles, agent_count) VALUES (?, ?, ?, ?, ?)",
        (run_id, event_name, year, cycles, agent_count),
    )
    conn.commit()
    conn.close()
    logger.info(f"Created simulation run {run_id} for event: {event_name}")
    return run_id


def complete_simulation_run(run_id: str):
    """Mark a run as completed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE simulation_runs SET status = ?, completed_at = ? WHERE run_id = ?",
        ("completed", datetime.now().isoformat(), run_id),
    )
    conn.commit()
    conn.close()


def list_simulation_runs() -> List[Dict[str, Any]]:
    """List all simulation runs, newest first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_runs ORDER BY started_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_simulation_run(run_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Agent response helpers ──────────────────────────────────────────────────


def save_agent_response(
    run_id: str,
    agent_id: str,
    agent_name: str,
    agent_role: str,
    agent_region: str,
    cycle: int,
    decision: Dict[str, Any],
) -> int:
    """Persist one agent decision to the database. Returns the inserted row id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO agent_responses
            (run_id, agent_id, agent_name, agent_role, agent_region, cycle,
             thoughts, emotional_state, action, plan, migration_intent,
             trust_shift, trust_change, trust_target, is_less_trusting,
             is_migrating, migration_destination, raw_response)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            run_id,
            agent_id,
            agent_name,
            agent_role,
            agent_region,
            cycle,
            decision.get("thoughts", ""),
            decision.get("emotional_state", ""),
            decision.get("action", ""),
            decision.get("plan", ""),
            decision.get("migration_intent", ""),
            decision.get("trust_shift", ""),
            decision.get("trust_change", "none"),
            decision.get("trust_target"),
            1 if decision.get("is_less_trusting") else 0,
            1 if decision.get("is_migrating") else 0,
            decision.get("migration_destination"),
            decision.get("raw_response", ""),
        ),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return int(row_id or 0)


def get_run_responses(
    run_id: str,
    page: int = 1,
    per_page: int = 50,
    cycle: Optional[int] = None,
    region: Optional[str] = None,
    migrating_only: bool = False,
    less_trusting_only: bool = False,
) -> Dict[str, Any]:
    """Get paginated agent responses for a run."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = ["run_id = ?"]
    params: List[Any] = [run_id]

    if cycle is not None:
        conditions.append("cycle = ?")
        params.append(cycle)
    if region:
        conditions.append("agent_region = ?")
        params.append(region)
    if migrating_only:
        conditions.append("is_migrating = 1")
    if less_trusting_only:
        conditions.append("is_less_trusting = 1")

    where = " AND ".join(conditions)
    offset = (page - 1) * per_page

    cursor.execute(f"SELECT COUNT(*) FROM agent_responses WHERE {where}", params)
    total = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT * FROM agent_responses WHERE {where} ORDER BY timestamp ASC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    )
    rows = cursor.fetchall()
    conn.close()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "responses": [dict(r) for r in rows],
    }


def get_run_evolution(run_id: str) -> List[Dict[str, Any]]:
    """Return per-cycle aggregated statistics for a run."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            cycle,
            COUNT(*) as agent_count,
            SUM(is_migrating) as migrating_count,
            SUM(is_less_trusting) as less_trusting_count,
            GROUP_CONCAT(DISTINCT emotional_state) as emotions,
            GROUP_CONCAT(DISTINCT agent_region) as regions
        FROM agent_responses
        WHERE run_id = ?
        GROUP BY cycle
        ORDER BY cycle ASC
    """,
        (run_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        # Parse emotions into frequency map
        if d.get("emotions"):
            emotion_list = [
                e.strip().lower() for e in d["emotions"].split(",") if e.strip()
            ]
            freq: Dict[str, int] = {}
            for e in emotion_list:
                freq[e] = freq.get(e, 0) + 1
            d["emotion_breakdown"] = dict(sorted(freq.items(), key=lambda x: -x[1])[:5])
        else:
            d["emotion_breakdown"] = {}
        result.append(d)

    return result


def get_agent_history(agent_id: str) -> List[Dict[str, Any]]:
    """Get all responses ever recorded for a single agent across all runs."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ar.*, sr.event_name, sr.year
        FROM agent_responses ar
        JOIN simulation_runs sr ON ar.run_id = sr.run_id
        WHERE ar.agent_id = ?
        ORDER BY ar.timestamp ASC
    """,
        (agent_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_search_entry(run_id: str, response_id: int, agent_id: str, text_content: str):
    """Save a text entry to the search index."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO search_index (run_id, response_id, agent_id, text_content) VALUES (?, ?, ?, ?)",
        (run_id, response_id, agent_id, text_content),
    )
    conn.commit()
    conn.close()


def get_search_entries(run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all search index entries, optionally filtered by run."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if run_id:
        cursor.execute("SELECT * FROM search_index WHERE run_id = ?", (run_id,))
    else:
        cursor.execute("SELECT * FROM search_index")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Relationship graph helpers ─────────────────────────────────────────────


def save_agent_relationship(
    run_id: str,
    source_agent_id: str,
    source_agent_name: str,
    target_agent_id: str,
    target_agent_name: str,
    relation_type: str,
    weight: float = 1.0,
    context: str = "",
    cycle: Optional[int] = None,
) -> int:
    """Persist one directed relationship edge. Returns inserted row id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO agent_relationships
            (run_id, cycle, source_agent_id, source_agent_name,
             target_agent_id, target_agent_name, relation_type,
             weight, context)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            cycle,
            source_agent_id,
            source_agent_name,
            target_agent_id,
            target_agent_name,
            relation_type,
            weight,
            context,
        ),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return int(row_id or 0)


def get_run_relationships(run_id: str) -> List[Dict[str, Any]]:
    """Get raw relationship edges for a simulation run."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM agent_relationships
        WHERE run_id = ?
        ORDER BY timestamp ASC
        """,
        (run_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run_agent_nodes(run_id: str) -> List[Dict[str, Any]]:
    """Get unique agent metadata for a run from persisted responses."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            agent_id,
            MAX(agent_name) AS agent_name,
            MAX(agent_role) AS agent_role,
            MAX(agent_region) AS agent_region
        FROM agent_responses
        WHERE run_id = ?
        GROUP BY agent_id
        ORDER BY agent_name ASC
        """,
        (run_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
