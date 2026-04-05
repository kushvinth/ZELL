from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import math
import sqlite3
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from app.simulation.db import DB_PATH, get_simulation_run


POSITIVE_EMOTIONS = {
    "hopeful",
    "optimistic",
    "relieved",
    "calm",
    "confident",
    "determined",
}
NEGATIVE_EMOTIONS = {
    "fearful",
    "afraid",
    "terrified",
    "anxious",
    "worried",
    "angry",
    "furious",
    "outraged",
    "sad",
    "grief",
    "devastated",
}

COLOR_THEME = {
    "primary": "#1f6feb",
    "secondary": "#12b886",
    "accent": "#f59f00",
    "danger": "#e03131",
    "ink": "#0f172a",
    "muted": "#475569",
    "paper": "#f8fafc",
}

_REPORT_SERVICES_DIR = Path(__file__).resolve().parent
_REPORT_TEMPLATE_PATH = _REPORT_SERVICES_DIR / "report_template.html"
_REPORT_UI_DIR = _REPORT_SERVICES_DIR / "report_ui"
_REPORT_UI_FILES = (
    "report_tokens.jsx",
    "report_hooks.jsx",
    "report_components.jsx",
    "report_app.jsx",
)


@dataclass
class ReportDataset:
    run: dict[str, Any]
    responses: list[dict[str, Any]]
    relationships: list[dict[str, Any]]


@lru_cache(maxsize=1)
def _load_report_template() -> str:
    return _REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_report_jsx_bundle() -> str:
    chunks: list[str] = []
    for name in _REPORT_UI_FILES:
        chunks.append((_REPORT_UI_DIR / name).read_text(encoding="utf-8"))
    return "\n\n".join(chunks)


def _safe_json_for_script(data: dict[str, Any]) -> str:
    # Prevent accidental </script> termination and preserve unicode separators.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("</", "<\\/")
    text = text.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return text


def _fetch_dataset(run_id: str) -> ReportDataset:
    run = get_simulation_run(run_id)
    if not run:
        raise ValueError("Run not found")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
		SELECT *
		FROM agent_responses
		WHERE run_id = ?
		ORDER BY cycle ASC, timestamp ASC, id ASC
		""",
        (run_id,),
    )
    responses = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
		SELECT *
		FROM agent_relationships
		WHERE run_id = ?
		ORDER BY COALESCE(cycle, 0) ASC, timestamp ASC, id ASC
		""",
        (run_id,),
    )
    relationships = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return ReportDataset(run=run, responses=responses, relationships=relationships)


def _token(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    return text.split()[0].strip('.,:;!?()[]{}"')


def _decision_label(response: dict[str, Any]) -> str:
    action = str(response.get("action") or "").lower()
    migration_intent = str(response.get("migration_intent") or "").lower()
    trust_change = str(response.get("trust_change") or "").lower()

    if response.get("is_migrating"):
        return "Migration"
    if response.get("is_less_trusting") or trust_change in {"decrease", "drop"}:
        return "Trust Reduction"
    if any(t in action for t in ("help", "support", "aid", "assist")):
        return "Mutual Aid"
    if any(t in action for t in ("plan", "coordinate", "organize")):
        return "Coordination"
    if any(t in action for t in ("wait", "observe", "monitor")):
        return "Observation"
    if any(t in migration_intent for t in ("stay", "remain")):
        return "Stay Put"
    return "Other"


def _emotion_score(raw_emotion: Any) -> float:
    t = _token(raw_emotion)
    if t in POSITIVE_EMOTIONS:
        return 1.0
    if t in NEGATIVE_EMOTIONS:
        return -1.0
    return 0.0


def _top_counter(counter: Counter[str], max_items: int) -> list[dict[str, Any]]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:max_items]
    return [{"label": label, "value": value} for label, value in items]


def _signature(dataset: ReportDataset) -> str:
    stable = {
        "run": {
            "run_id": dataset.run.get("run_id"),
            "event_name": dataset.run.get("event_name"),
            "year": dataset.run.get("year"),
            "cycles": dataset.run.get("cycles"),
            "agent_count": dataset.run.get("agent_count"),
            "status": dataset.run.get("status"),
        },
        "responses": [
            {
                "id": r.get("id"),
                "cycle": r.get("cycle"),
                "agent_id": r.get("agent_id"),
                "emotion": _token(r.get("emotional_state")),
                "decision": _decision_label(r),
                "is_migrating": int(r.get("is_migrating") or 0),
                "is_less_trusting": int(r.get("is_less_trusting") or 0),
            }
            for r in dataset.responses
        ],
        "relationships": [
            {
                "source": e.get("source_agent_id"),
                "target": e.get("target_agent_id"),
                "type": e.get("relation_type"),
                "cycle": e.get("cycle"),
            }
            for e in dataset.relationships
        ],
    }
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_report_data(run_id: str) -> dict[str, Any]:
    dataset = _fetch_dataset(run_id)
    responses = dataset.responses
    relationships = dataset.relationships

    role_counter: Counter[str] = Counter()
    region_counter: Counter[str] = Counter()
    emotion_counter: Counter[str] = Counter()
    decision_counter: Counter[str] = Counter()
    relation_type_counter: Counter[str] = Counter()

    by_cycle = defaultdict(
        lambda: {
            "responses": 0,
            "migrating": 0,
            "less_trusting": 0,
            "sentiment_sum": 0.0,
            "actions": Counter(),
        }
    )
    heatmap_counts: defaultdict[tuple[int, str], int] = defaultdict(int)
    agent_degree: Counter[str] = Counter()

    for r in responses:
        cycle = int(r.get("cycle") or 0)
        role = str(r.get("agent_role") or "Unknown")
        region = str(r.get("agent_region") or "Unknown")
        emotion = _token(r.get("emotional_state"))
        decision = _decision_label(r)
        action = str(r.get("action") or "").strip() or "No explicit action"

        role_counter[role] += 1
        region_counter[region] += 1
        emotion_counter[emotion] += 1
        decision_counter[decision] += 1

        by_cycle[cycle]["responses"] += 1
        by_cycle[cycle]["migrating"] += int(r.get("is_migrating") or 0)
        by_cycle[cycle]["less_trusting"] += int(r.get("is_less_trusting") or 0)
        by_cycle[cycle]["sentiment_sum"] += _emotion_score(r.get("emotional_state"))
        by_cycle[cycle]["actions"][action] += 1

        heatmap_counts[(cycle, region)] += 1

    for e in relationships:
        rel_type = str(e.get("relation_type") or "unknown")
        source = str(e.get("source_agent_id") or "")
        target = str(e.get("target_agent_id") or "")
        relation_type_counter[rel_type] += 1
        if source:
            agent_degree[source] += 1
        if target:
            agent_degree[target] += 1

    behavior_rows: list[dict[str, Any]] = []
    timeline_rows: list[dict[str, Any]] = []
    migration_rates: list[float] = []
    trust_drop_rates: list[float] = []

    for cycle in sorted(by_cycle.keys()):
        row = by_cycle[cycle]
        n = max(1, int(row["responses"]))
        mig_rate = row["migrating"] / n
        trust_rate = row["less_trusting"] / n
        sentiment = row["sentiment_sum"] / n

        top_action, top_count = sorted(
            row["actions"].items(), key=lambda kv: (-kv[1], kv[0])
        )[0]

        behavior_rows.append(
            {
                "cycle": cycle,
                "responses": row["responses"],
                "migrating": row["migrating"],
                "less_trusting": row["less_trusting"],
                "migrating_rate": round(mig_rate, 4),
                "trust_drop_rate": round(trust_rate, 4),
                "avg_sentiment": round(sentiment, 4),
            }
        )
        timeline_rows.append(
            {
                "cycle": cycle,
                "event_label": top_action,
                "event_frequency": top_count,
            }
        )
        migration_rates.append(mig_rate)
        trust_drop_rates.append(trust_rate)

    top_regions = [x["label"] for x in _top_counter(region_counter, max_items=8)]
    heatmap_rows = []
    for cycle in sorted(by_cycle.keys()):
        row = {"cycle": cycle}
        for region in top_regions:
            row[region] = heatmap_counts.get((cycle, region), 0)
        heatmap_rows.append(row)

    top_connected = sorted(agent_degree.items(), key=lambda kv: (-kv[1], kv[0]))[:16]

    response_times = [
        str(r.get("timestamp"))
        for r in responses
        if isinstance(r.get("timestamp"), str) and r.get("timestamp")
    ]
    started_at = (
        min(response_times) if response_times else dataset.run.get("started_at")
    )
    completed_at = (
        max(response_times) if response_times else dataset.run.get("completed_at")
    )

    anomalies: list[str] = []
    if migration_rates:
        avg = sum(migration_rates) / len(migration_rates)
        spike = avg + 0.18
        for row in behavior_rows:
            if row["migrating_rate"] > spike:
                anomalies.append(
                    f"Cycle {row['cycle']} migration spike at {row['migrating_rate'] * 100:.1f}% (avg {avg * 100:.1f}%)."
                )
    if trust_drop_rates:
        avg = sum(trust_drop_rates) / len(trust_drop_rates)
        spike = avg + 0.18
        for row in behavior_rows:
            if row["trust_drop_rate"] > spike:
                anomalies.append(
                    f"Cycle {row['cycle']} trust-drop spike at {row['trust_drop_rate'] * 100:.1f}% (avg {avg * 100:.1f}%)."
                )
    for agent_id, degree in top_connected[:3]:
        anomalies.append(f"High-centrality agent {agent_id} reached degree {degree}.")

    signature = _signature(dataset)

    return {
        "report_version": "2.0",
        "reproducibility": {
            "deterministic": True,
            "signature": signature,
            "notes": "Stable sorting and fixed chart order produce reproducible visuals for identical run data.",
        },
        "metadata": {
            "run_id": dataset.run.get("run_id"),
            "event_name": dataset.run.get("event_name"),
            "year": dataset.run.get("year"),
            "cycles": dataset.run.get("cycles"),
            "agent_count": dataset.run.get("agent_count"),
            "status": dataset.run.get("status"),
            "started_at": started_at,
            "completed_at": completed_at,
            "response_count": len(responses),
            "relationship_count": len(relationships),
        },
        "executive_summary": {
            "key_metrics": {
                "total_responses": len(responses),
                "migration_events": sum(
                    int(r.get("is_migrating") or 0) for r in responses
                ),
                "trust_drop_events": sum(
                    int(r.get("is_less_trusting") or 0) for r in responses
                ),
                "relationship_edges": len(relationships),
                "dominant_decision": _top_counter(decision_counter, max_items=1)[0][
                    "label"
                ]
                if decision_counter
                else "none",
                "dominant_emotion": _top_counter(emotion_counter, max_items=1)[0][
                    "label"
                ]
                if emotion_counter
                else "none",
            }
        },
        "charts": {
            "agent_behavior_over_time": behavior_rows,
            "distribution_decisions": _top_counter(decision_counter, max_items=4),
            "distribution_emotions": _top_counter(emotion_counter, max_items=12),
            "distribution_roles": _top_counter(role_counter, max_items=12),
            "distribution_regions": _top_counter(region_counter, max_items=12),
            "relationship_types": _top_counter(relation_type_counter, max_items=12),
            "timeline_major_events": timeline_rows,
            "cycle_region_heatmap": heatmap_rows,
            "heatmap_regions": top_regions,
            "network_top_connected": [
                {"agent_id": agent_id, "degree": degree}
                for agent_id, degree in top_connected
            ],
            "network_edges": [
                {
                    "source": str(e.get("source_agent_id") or ""),
                    "target": str(e.get("target_agent_id") or ""),
                    "type": str(e.get("relation_type") or "unknown"),
                    "weight": float(e.get("weight") or 1.0),
                }
                for e in relationships
            ],
        },
        "raw_tables": {
            "responses": responses[:240],
            "top_relationships": [
                {"relation_type": i["label"], "count": i["value"]}
                for i in _top_counter(relation_type_counter, max_items=24)
            ],
        },
        "insights": {
            "anomalies": anomalies[:14],
            "final_notes": [
                "Behavior trajectories are deterministic over persisted run data.",
                "Sentiment index is a lexical proxy from emotional-state fields.",
                "Network centrality uses in+out relationship degree.",
            ],
        },
    }


def _setup_matplotlib() -> tuple[Any, Any]:
    import matplotlib  # type: ignore[import-not-found]

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    from matplotlib.backends.backend_pdf import PdfPages  # type: ignore[import-not-found]

    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["savefig.dpi"] = 150
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.titleweight"] = "bold"
    return plt, PdfPages


def _fig_to_uri(fig: Any) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _compact_identifier(value: Any, head: int = 10, tail: int = 8) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    if len(text) <= head + tail + 1:
        return text
    return f"{text[:head]}...{text[-tail:]}"


def _shorten_text(value: Any, max_len: int = 28) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return textwrap.shorten(text, width=max_len, placeholder="...")


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        n = float(value)
        if math.isfinite(n):
            return n
    except (TypeError, ValueError):
        pass
    return fallback


def _style_dark_chart(
    fig: Any, ax: Any, title: str, subtitle: str | None = None
) -> None:
    fig.patch.set_facecolor("#06090f")
    ax.set_facecolor("#0b1120")
    fig.subplots_adjust(top=0.80)
    for spine in ax.spines.values():
        spine.set_color("#223a5c")
        spine.set_linewidth(0.9)
    ax.tick_params(colors="#9cb3de", labelsize=9)
    ax.yaxis.label.set_color("#a9c1eb")
    ax.xaxis.label.set_color("#a9c1eb")
    ax.set_title("")
    fig.text(
        0.125,
        0.955,
        title,
        color="#e5efff",
        fontsize=16,
        fontweight="bold",
        ha="left",
        va="top",
    )
    if subtitle:
        fig.text(
            0.125, 0.925, subtitle, color="#6fcdf3", fontsize=10, ha="left", va="top"
        )


def _tight_layout_chart(fig: Any) -> None:
    # Reserve consistent top area for fig-level title/subtitle to avoid overlap.
    fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.82))


def _plot_behavior(plt: Any, rows: list[dict[str, Any]]) -> Any:
    fig, ax = plt.subplots(figsize=(10.8, 4.9))
    if not rows:
        _style_dark_chart(fig, ax, "Agent Behavior Over Time")
        ax.text(0.5, 0.5, "No behavior data", ha="center", va="center", color="#9cb3de")
        ax.set_axis_off()
        return fig

    _style_dark_chart(
        fig,
        ax,
        "Agent Behavior Over Time",
        "Migration, trust stress, and normalized sentiment",
    )
    xs = [r["cycle"] for r in rows]
    mig = [r["migrating_rate"] * 100 for r in rows]
    trust = [r["trust_drop_rate"] * 100 for r in rows]
    sent = [r["avg_sentiment"] * 50 + 50 for r in rows]

    ax.fill_between(xs, mig, color="#1f6feb", alpha=0.14)
    ax.fill_between(xs, trust, color="#e03131", alpha=0.10)
    ax.plot(
        xs,
        mig,
        marker="o",
        markersize=4.8,
        linewidth=2.9,
        color="#54b6ff",
        label="Migration %",
    )
    ax.plot(
        xs,
        trust,
        marker="s",
        markersize=4.4,
        linewidth=2.7,
        color="#ff6e9b",
        label="Trust-drop %",
    )
    ax.plot(
        xs,
        sent,
        marker="^",
        markersize=4.2,
        linewidth=2.2,
        color="#37e7ab",
        linestyle="--",
        label="Sentiment index",
    )

    ax.set_xlabel("Cycle")
    ax.set_ylabel("Rate / Index")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.22, linestyle="--", color="#5270a3")

    if mig:
        peak_i = max(range(len(mig)), key=lambda i: mig[i])
        ax.scatter(
            [xs[peak_i]],
            [mig[peak_i]],
            s=52,
            color="#ffb55f",
            edgecolor="#fff3d0",
            linewidth=0.8,
            zorder=5,
        )
        ax.annotate(
            f"Peak {mig[peak_i]:.1f}%",
            (xs[peak_i], mig[peak_i]),
            xytext=(10, 10),
            textcoords="offset points",
            color="#ffe6af",
            fontsize=8,
        )

    legend = ax.legend(loc="upper right", frameon=True)
    legend.get_frame().set_facecolor("#0b1120")
    legend.get_frame().set_edgecolor("#2a4469")
    for text in legend.get_texts():
        text.set_color("#d9e6ff")
    _tight_layout_chart(fig)
    return fig


def _plot_bar(plt: Any, title: str, items: list[dict[str, Any]], color: str) -> Any:
    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    _style_dark_chart(fig, ax, title, "Top categories ranked by frequency")
    labels = [str(i["label"]) for i in items][:12]
    display_labels = [_shorten_text(label, 16) for label in labels]
    values = [i["value"] for i in items][:12]
    if not values:
        ax.text(
            0.5, 0.5, "No distribution data", ha="center", va="center", color="#9cb3de"
        )
        ax.set_axis_off()
        return fig

    bar_colors = [color for _ in values]
    bars = ax.bar(
        display_labels,
        values,
        color=bar_colors,
        alpha=0.92,
        edgecolor="#bfd4ff26",
        linewidth=0.8,
    )
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.22, linestyle="--", color="#5270a3")
    ax.set_axisbelow(True)

    max_v = max(values)
    for bar, value in zip(bars, values):
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        ax.text(
            x,
            y + max_v * 0.015,
            f"{value:,}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#deecff",
        )
    _tight_layout_chart(fig)
    return fig


def _plot_donut(plt: Any, title: str, items: list[dict[str, Any]]) -> Any:
    fig, ax = plt.subplots(figsize=(8.2, 6.0))
    _style_dark_chart(fig, ax, title, "Share of top decision clusters")
    labels = [i["label"] for i in items]
    values = [i["value"] for i in items]
    if not values:
        labels = ["No data"]
        values = [1]

    palette = [
        "#54b6ff",
        "#37e7ab",
        "#ffb55f",
        "#bb7cff",
        "#ff6e9b",
        "#7b8dff",
        "#31e6ff",
    ]
    explode = [0.05] + [0.0] * (len(values) - 1)
    total = sum(values)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=[_shorten_text(label, 20) for label in labels],
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 4 else "",
        startangle=90,
        explode=explode,
        colors=palette[: len(values)],
        wedgeprops={"width": 0.52, "edgecolor": "#0b1120", "linewidth": 1.3},
    )
    for t in texts:
        t.set_fontsize(8)
        t.set_color("#c8dbff")
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color("#f3f8ff")

    ax.text(
        0,
        0.05,
        f"{total:,}",
        ha="center",
        va="center",
        fontsize=17,
        color="#eaf2ff",
        fontweight="bold",
    )
    ax.text(0, -0.12, "total", ha="center", va="center", fontsize=9, color="#85a3d2")
    _tight_layout_chart(fig)
    return fig


def _plot_heatmap(plt: Any, rows: list[dict[str, Any]], regions: list[str]) -> Any:
    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    _style_dark_chart(
        fig,
        ax,
        "Cycle x Region Activity Heatmap",
        "Regional activity concentration over time",
    )
    if not rows or not regions:
        ax.text(0.5, 0.5, "No heatmap data", ha="center", va="center", color="#9cb3de")
        ax.set_axis_off()
        return fig

    matrix = [[row.get(region, 0) for region in regions] for row in rows]
    im = ax.imshow(matrix, cmap="magma", aspect="auto")
    ax.set_xlabel("Region")
    ax.set_ylabel("Cycle")
    ax.set_xticks(
        range(len(regions)),
        labels=[_shorten_text(region, 15) for region in regions],
        rotation=30,
        ha="right",
    )
    ax.set_yticks(range(len(rows)), labels=[r["cycle"] for r in rows])
    max_v = max(max(r) for r in matrix) if matrix else 1
    for row_i, row_values in enumerate(matrix):
        for col_i, value in enumerate(row_values):
            text_color = "#f4f6ff" if value > max_v * 0.45 else "#a8bcde"
            ax.text(
                col_i,
                row_i,
                str(value),
                ha="center",
                va="center",
                fontsize=7.5,
                color=text_color,
            )

    cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cb.ax.yaxis.set_tick_params(color="#9cb3de")
    cb.outline.set_edgecolor("#2f476f")
    for tick in cb.ax.get_yticklabels():
        tick.set_color("#9cb3de")
    _tight_layout_chart(fig)
    return fig


def _plot_timeline(plt: Any, rows: list[dict[str, Any]]) -> Any:
    fig, ax = plt.subplots(figsize=(10.8, 4.6))
    _style_dark_chart(
        fig, ax, "Timeline of Major Events", "Most frequent event marker by cycle"
    )
    if not rows:
        ax.text(0.5, 0.5, "No timeline data", ha="center", va="center", color="#9cb3de")
        ax.set_axis_off()
        return fig

    ys = list(range(len(rows)))
    freqs = [r["event_frequency"] for r in rows]
    labels = [f"Cycle {r['cycle']}" for r in rows]
    names = [str(r["event_label"])[:68] for r in rows]

    ax.hlines(ys, [0 for _ in ys], freqs, color="#2a3d5f", linewidth=3, alpha=0.6)
    ax.scatter(
        freqs, ys, color="#ffb55f", s=48, edgecolor="#ffe9c9", linewidth=0.9, zorder=3
    )
    ax.set_yticks(ys, labels=labels)
    ax.set_xlabel("Top Event Frequency")
    for idx, name in enumerate(names):
        ax.text(
            freqs[idx] + 0.2,
            idx,
            _shorten_text(name, 48),
            va="center",
            fontsize=8,
            color="#d7e6ff",
        )
    ax.grid(axis="x", alpha=0.22, linestyle="--", color="#5270a3")
    _tight_layout_chart(fig)
    return fig


def _plot_network(
    plt: Any, top_nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> Any:
    fig, ax = plt.subplots(figsize=(8.8, 8.0))
    _style_dark_chart(
        fig,
        ax,
        "Relationship Network Graph",
        "Top central agents and strongest visible ties",
    )
    if not top_nodes:
        ax.text(
            0.5, 0.5, "No relationship data", ha="center", va="center", color="#9cb3de"
        )
        ax.set_axis_off()
        return fig

    node_ids = [n["agent_id"] for n in top_nodes[:16]]
    n = len(node_ids)
    if n == 0:
        ax.text(0.5, 0.5, "No relationship data", ha="center", va="center")
        ax.set_axis_off()
        return fig

    positions: dict[str, tuple[float, float]] = {}
    for idx, node_id in enumerate(sorted(node_ids)):
        angle = 2 * math.pi * idx / n
        positions[node_id] = (math.cos(angle), math.sin(angle))

    allowed = set(node_ids)
    drawn = 0
    for edge in edges:
        s = edge.get("source")
        t = edge.get("target")
        if s not in allowed or t not in allowed:
            continue
        if not isinstance(s, str) or not isinstance(t, str):
            continue
        x1, y1 = positions[s]
        x2, y2 = positions[t]
        weight = _safe_float(edge.get("weight"), 1.0)
        width = 0.6 + min(2.0, max(0.0, weight) * 0.9)
        alpha = 0.12 + min(0.45, max(0.0, weight) * 0.2)
        ax.plot([x1, x2], [y1, y2], color="#8ec4ff", alpha=alpha, linewidth=width)
        drawn += 1
        if drawn >= 200:
            break

    max_degree = max(
        (_safe_float(node.get("degree"), 1.0) for node in top_nodes[:16]), default=1.0
    )
    for node in top_nodes[:16]:
        node_id = node["agent_id"]
        degree = _safe_float(node.get("degree"), 1.0)
        x, y = positions[node_id]
        size = 120 + min(560, degree * 19)
        intensity = min(1.0, degree / max_degree)
        color = (0.33 + 0.52 * intensity, 0.56 + 0.25 * (1 - intensity), 1.0)
        ax.scatter(
            [x],
            [y],
            s=size,
            color=color,
            alpha=0.9,
            edgecolor="#eef5ff",
            linewidth=0.9,
        )
        ax.text(
            x,
            y,
            _shorten_text(node_id, 8),
            ha="center",
            va="center",
            color="#081122",
            fontsize=7,
            fontweight="bold",
        )

    ax.set_axis_off()
    _tight_layout_chart(fig)
    return fig


def _chart_figures(report_data: dict[str, Any]) -> list[tuple[str, Any]]:
    plt, _ = _setup_matplotlib()
    c = report_data["charts"]
    return [
        ("Agent Behavior", _plot_behavior(plt, c["agent_behavior_over_time"])),
        (
            "Decision Distribution",
            _plot_donut(plt, "Decision Distribution", c["distribution_decisions"]),
        ),
        (
            "Emotion Distribution",
            _plot_bar(
                plt, "Emotion Distribution", c["distribution_emotions"], "#2f9e44"
            ),
        ),
        (
            "Role Distribution",
            _plot_bar(plt, "Role Distribution", c["distribution_roles"], "#7c3aed"),
        ),
        (
            "Region Distribution",
            _plot_bar(plt, "Region Distribution", c["distribution_regions"], "#2563eb"),
        ),
        (
            "Relationship Types",
            _plot_bar(plt, "Relationship Types", c["relationship_types"], "#0f766e"),
        ),
        ("Timeline", _plot_timeline(plt, c["timeline_major_events"])),
        (
            "Heatmap",
            _plot_heatmap(plt, c["cycle_region_heatmap"], c["heatmap_regions"]),
        ),
        (
            "Network",
            _plot_network(plt, c["network_top_connected"], c["network_edges"]),
        ),
    ]


def render_report_md(report_data: dict[str, Any]) -> str:
    """Generate a structured Markdown report from the dataset."""
    meta = report_data["metadata"]
    metrics = report_data["executive_summary"]["key_metrics"]

    lines = [
        "# Simulation Intelligence Report",
        f"**Event / Context:** {meta.get('event_name', 'Unknown')}",
        f"**Run ID:** `{meta.get('run_id', 'unknown')}` | **Year:** {meta.get('year')} | **Cycles:** {meta.get('cycles')} | **Agents:** {meta.get('agent_count')}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Total Responses Recorded:** {metrics.get('total_responses'):,}",
        f"- **Migration Events:** {metrics.get('migration_events'):,}",
        f"- **Trust Collapse Events:** {metrics.get('trust_drop_events'):,}",
        f"- **Relationship Edges Built:** {metrics.get('relationship_edges'):,}",
        f"- **Dominant Global Decision:** {metrics.get('dominant_decision')}",
        f"- **Dominant Global Emotion:** {metrics.get('dominant_emotion')}",
        "",
        "## 2. Behavioral Highlights",
        "",
    ]

    # Extract timeline & evolution
    evol = report_data.get("executive_summary", {}).get("evolution", [])
    if evol:
        for e in evol:
            lines.append(f"### Cycle {e.get('cycle')}")
            lines.append(
                f"Migration count reached {e.get('migration_count', 0)}, with dominant emotion shifting to **{e.get('top_emotion', 'unknown')}**."
            )
            if e.get("affected_regions"):
                lines.append(
                    f"Affected regions: {', '.join(e.get('affected_regions', []))}."
                )
            lines.append("")

    lines.append("## 3. Notable Agent Actions")
    lines.append("")
    sample_rows = report_data["raw_tables"]["responses"][:10]
    for r in sample_rows:
        lines.append(
            f"**{r.get('agent_name')}** _({r.get('agent_region')}, Cycle {r.get('cycle')})_"
        )
        if r.get("is_migrating"):
            lines.append("> [Migrating]")
        if r.get("is_less_trusting"):
            lines.append("> [Trust Dropped]")
        lines.append(f'> "{r.get("action")}"')
        lines.append("")

    lines.append("## 4. Anomalies & Automatic Insights")
    lines.append("")
    anomalies = report_data["insights"].get("anomalies", [])
    if not anomalies:
        lines.append("No statistical anomalies detected during the run.")
    else:
        for a in anomalies:
            lines.append(f"- **Anomaly Detected**: {a}")
    lines.append("")

    notes = report_data["insights"].get("final_notes", [])
    for n in notes:
        lines.append(f"- {n}")

    lines.append("")
    lines.append("---")
    lines.append(
        f"*Reproducibility Signature: `{report_data['reproducibility']['signature']}`*"
    )

    return "\n".join(lines)


def render_report_html(report_data: dict[str, Any]) -> str:
    """Render an interactive HTML report from reusable JSX components."""
    meta = report_data.get("metadata", {})
    template = _load_report_template()
    jsx_bundle = _load_report_jsx_bundle()

    return (
        template.replace(
            "__ZELL_TITLE__", html.escape(str(meta.get("run_id", "unknown")))
        )
        .replace("__ZELL_DATA__", _safe_json_for_script(report_data))
        .replace("__ZELL_JSX_BUNDLE__", jsx_bundle)
    )


def _add_text_page(plt: Any, pdf: Any, title: str, lines: Iterable[str]) -> None:
    BG = "#06090f"
    TEAL = "#00d4ff"
    TEXT = "#deeeff"
    MUTED = "#3d5a7a"

    fig = plt.figure(figsize=(11.0, 8.3))
    fig.patch.set_facecolor(BG)
    fig.text(
        0.05,
        0.93,
        title,
        fontsize=20,
        fontweight="bold",
        color=TEAL,
        fontfamily="monospace",
    )
    fig.text(0.05, 0.905, "─" * 90, fontsize=7, color=MUTED)
    y = 0.87
    for line in lines:
        fig.text(0.06, y, line, fontsize=10.5, color=TEXT, fontfamily="monospace")
        y -= 0.045
        if y < 0.07:
            break
    pdf.savefig(fig)
    plt.close(fig)


def render_report_pdf(report_data: dict[str, Any]) -> bytes:
    """
    Render a PDF report using matplotlib.

    The PDF mirrors the same data as the interactive HTML report and includes:
      – Cover page with metadata + KPIs
      – One page per chart
      – Raw data table page
      – Anomalies / insights page
    """
    plt, PdfPages = _setup_matplotlib()

    BG = "#06090f"
    PANEL = "#0b1120"
    TEAL = "#00d4ff"
    TEXT = "#deeeff"
    MUTED = "#3d5a7a"

    meta = report_data["metadata"]
    metrics = report_data["executive_summary"]["key_metrics"]
    sig = report_data["reproducibility"]["signature"]

    out = io.BytesIO()
    with PdfPages(out) as pdf:
        # ── Cover page ───────────────────────────────────────────────────────
        fig = plt.figure(figsize=(11.0, 8.3))
        fig.patch.set_facecolor(BG)
        from matplotlib.patches import FancyBboxPatch  # type: ignore[import-not-found]

        # Accent bar at top
        fig.add_axes([0, 0.96, 1, 0.04]).set_facecolor(TEAL)
        fig.axes[-1].set_axis_off()

        event_title = textwrap.fill(
            str(meta.get("event_name") or "Simulation Intelligence Report"),
            width=68,
            max_lines=3,
            placeholder="...",
        )
        full_run_id = str(meta.get("run_id") or "")
        compact_run_id = _compact_identifier(full_run_id, 8, 6)

        fig.text(
            0.05,
            0.90,
            "◈  ZELL SIMULATION INTELLIGENCE",
            fontsize=9,
            color=TEAL,
            fontfamily="monospace",
            fontweight="bold",
        )
        fig.text(
            0.05,
            0.82,
            event_title,
            fontsize=18,
            fontweight="bold",
            color=TEXT,
            fontfamily="monospace",
            wrap=True,
        )

        kpi_pairs = [
            ("RUN ID", compact_run_id),
            ("YEAR", str(meta.get("year", ""))),
            ("CYCLES", str(meta.get("cycles", ""))),
            ("AGENTS", f"{meta.get('agent_count', 0):,}"),
            ("STATUS", str(meta.get("status", "")).upper()),
            ("RESPONSES", f"{metrics.get('total_responses', 0):,}"),
            ("MIGRATIONS", f"{metrics.get('migration_events', 0):,}"),
            ("TRUST DROPS", f"{metrics.get('trust_drop_events', 0):,}"),
            ("REL. EDGES", f"{metrics.get('relationship_edges', 0):,}"),
            ("DECISION", _shorten_text(metrics.get("dominant_decision", ""), 20)),
            ("EMOTION", _shorten_text(metrics.get("dominant_emotion", ""), 20)),
        ]
        cols = 4
        x_starts = [0.05, 0.285, 0.52, 0.755]
        card_w = 0.205
        card_h = 0.074
        for i, (k, v) in enumerate(kpi_pairs):
            col = i % cols
            row = i // cols
            xp = x_starts[col]
            yp = 0.70 - row * 0.105
            card = FancyBboxPatch(
                (xp - 0.008, yp - 0.018),
                card_w,
                card_h,
                boxstyle="round,pad=0.006,rounding_size=0.01",
                transform=fig.transFigure,
                facecolor=PANEL,
                edgecolor="#21344f",
                linewidth=0.9,
                alpha=0.95,
            )
            fig.add_artist(card)
            fig.text(
                xp,
                yp + 0.025,
                k,
                fontsize=7.5,
                color=MUTED,
                fontfamily="monospace",
                fontweight="bold",
                transform=fig.transFigure,
            )
            value_text = _shorten_text(v, 19) if k == "RUN ID" else _shorten_text(v, 23)
            value_size = 11.0 if k == "RUN ID" else 12.5
            fig.text(
                xp,
                yp - 0.001,
                value_text,
                fontsize=value_size,
                color=TEXT,
                fontfamily="monospace",
                fontweight="bold",
                transform=fig.transFigure,
            )

        fig.text(0.05, 0.07, "─" * 112, fontsize=6, color=MUTED)
        fig.text(
            0.05,
            0.045,
            f"DETERMINISTIC MODE ACTIVE  ·  SIG: {sig[:32]}  ·  REPORT v{report_data.get('report_version', '2.0')}",
            fontsize=7.5,
            color=MUTED,
            fontfamily="monospace",
        )
        if full_run_id:
            fig.text(
                0.05,
                0.025,
                f"FULL RUN ID: {full_run_id}",
                fontsize=6.8,
                color="#6d84b0",
                fontfamily="monospace",
            )

        # Bottom teal accent
        fig.add_axes([0, 0, 1, 0.02]).set_facecolor(TEAL)
        fig.axes[-1].set_axis_off()

        pdf.savefig(fig)
        plt.close(fig)

        # ── Chart pages ──────────────────────────────────────────────────────
        for _, fig in _chart_figures(report_data):
            pdf.savefig(fig)
            plt.close(fig)

        # ── Raw data table ───────────────────────────────────────────────────
        sample_rows = report_data["raw_tables"]["responses"][:18]
        fig, ax = plt.subplots(figsize=(11.0, 8.1))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.axis("off")
        ax.set_title(
            "Raw Data Sample",
            fontsize=14,
            loc="left",
            pad=12,
            color=TEAL,
            fontfamily="monospace",
            fontweight="bold",
        )

        table_rows = [
            [
                str(r.get("cycle") or ""),
                _shorten_text(r.get("agent_name") or "", 20),
                _shorten_text(r.get("agent_region") or "", 18),
                "yes" if r.get("is_migrating") else "no",
                "yes" if r.get("is_less_trusting") else "no",
                textwrap.fill(
                    _shorten_text(r.get("action") or "", 64),
                    width=28,
                    max_lines=2,
                    placeholder="...",
                ),
            ]
            for r in sample_rows
        ]

        if table_rows:
            table = ax.table(
                cellText=table_rows,
                colLabels=[
                    "Cycle",
                    "Agent",
                    "Region",
                    "Migrating",
                    "Trust Drop",
                    "Action",
                ],
                loc="center",
                cellLoc="left",
                colWidths=[0.08, 0.16, 0.15, 0.10, 0.11, 0.40],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(7.1)
            table.scale(1, 1.50)
            for (row, col), cell in table.get_celld().items():
                cell.set_facecolor(PANEL if row > 0 else "#162033")
                cell.set_edgecolor("#1e3050")
                cell.set_text_props(
                    color=TEXT if row > 0 else TEAL, fontfamily="monospace"
                )
                if row > 0 and col == 5:
                    cell.get_text().set_fontsize(6.8)
                    cell.get_text().set_linespacing(1.25)
        else:
            ax.text(
                0.5,
                0.5,
                "No response rows available",
                ha="center",
                va="center",
                color=MUTED,
            )

        pdf.savefig(fig)
        plt.close(fig)

        # ── Anomalies page ───────────────────────────────────────────────────
        anomalies = report_data["insights"]["anomalies"] or [
            "No major anomalies detected."
        ]
        notes = report_data["insights"].get("final_notes", [])
        _add_text_page(
            plt,
            pdf,
            "Anomaly Detection  &  Final Insights",
            [f"▸ {a}" for a in anomalies[:14]]
            + ([""] + [f"  {n}" for n in notes] if notes else []),
        )

    out.seek(0)
    return out.read()
