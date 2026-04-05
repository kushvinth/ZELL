const { useState, useEffect, useMemo, useRef } = React;
const {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area,
} = Recharts;

const TOKENS = {
  bg: "#060b16",
  bgElevated: "#0b1428",
  panel: "rgba(9, 17, 34, 0.86)",
  panelSolid: "#0a1429",
  card: "#0d1932",
  border: "rgba(113, 154, 255, 0.22)",
  borderSoft: "rgba(113, 154, 255, 0.12)",
  text: "#e6eeff",
  muted: "#8ea7d6",
  subtle: "#6f88b6",
  primary: "#54b6ff",
  cyan: "#31e6ff",
  blue: "#7b8dff",
  green: "#37e7ab",
  amber: "#ffb55f",
  danger: "#ff6e9b",
  violet: "#bb7cff",
};

const CHART_COLORS = [
  TOKENS.primary,
  TOKENS.cyan,
  TOKENS.green,
  TOKENS.amber,
  TOKENS.violet,
  TOKENS.danger,
  "#6bd1ff",
  "#9fb3ff",
];

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function safeNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatInt(value) {
  return safeNumber(value).toLocaleString();
}

function formatPct(value) {
  return `${(safeNumber(value) * 100).toFixed(1)}%`;
}

function truncate(value, maxLen = 72) {
  const text = String(value || "");
  if (text.length <= maxLen) {
    return text;
  }
  return `${text.slice(0, maxLen - 1)}...`;
}

function emotionTone(text) {
  const token = String(text || "").toLowerCase();
  if (
    ["fearful", "afraid", "anxious", "angry", "sad"].some((t) =>
      token.includes(t),
    )
  ) {
    return TOKENS.danger;
  }
  if (
    ["hopeful", "optimistic", "calm", "relieved", "confident"].some((t) =>
      token.includes(t),
    )
  ) {
    return TOKENS.green;
  }
  return TOKENS.primary;
}

function cycleLabel(cycle) {
  return `C${safeNumber(cycle)}`;
}

function compactId(value, head = 8, tail = 4) {
  const text = String(value || "").trim();
  if (!text) {
    return "unknown";
  }
  if (text.length <= head + tail + 1) {
    return text;
  }
  return `${text.slice(0, head)}...${text.slice(-tail)}`;
}
