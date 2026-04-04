import React from "react";
import multiavatar from "@multiavatar/multiavatar";
import {
  Map,
  MapControls,
  MapMarker,
  MarkerContent,
  MarkerTooltip,
} from "@/components/ui/map";
import {
  Zap,
  Heart,
  Brain,
  PartyPopper,
  Briefcase,
  MapPin,
} from "lucide-react";

interface Agent {
  id: string;
  name: string;
  age: number;
  race: string;
  soul_type: "aggressive" | "altruistic" | "technocratic" | "hedonistic";
  traits: Record<string, number>;
  bio?: string;
  location: [number, number]; // [lon, lat]
  city: string;
  roleLabel?: string;
  roleValue?: string;
}

interface WorldMapProps {
  agents: Agent[];
  selectedAgent: Agent | null;
  onAgentSelect: (agent: Agent) => void;
  theme?: "light" | "dark";
}

const SOUL_COLORS: Record<string, string> = {
  aggressive: "#ef4444",
  altruistic: "#06b6d4",
  technocratic: "#a855f7",
  hedonistic: "#f59e0b",
};

const SOUL_ICON: Record<string, React.ReactNode> = {
  aggressive: <Zap className="w-3 h-3 text-white/60 inline mr-1" />,
  altruistic: <Heart className="w-3 h-3 text-white/60 inline mr-1" />,
  technocratic: <Brain className="w-3 h-3 text-white/60 inline mr-1" />,
  hedonistic: <PartyPopper className="w-3 h-3 text-white/60 inline mr-1" />,
};

// Per-agent tooltip component
function AgentMarker({
  agent,
  onAgentSelect,
}: {
  agent: Agent;
  onAgentSelect: (agent: Agent) => void;
}) {
  const [lon, lat] = agent.location;
  const color = SOUL_COLORS[agent.soul_type] ?? "#06b6d4";
  const icon = SOUL_ICON[agent.soul_type] ?? null;
  const avatarUrl = `data:image/svg+xml;utf8,${encodeURIComponent(
    multiavatar(agent.id),
  )}`;

  if (
    typeof lat !== "number" ||
    typeof lon !== "number" ||
    isNaN(lat) ||
    isNaN(lon)
  ) {
    return null;
  }

  return (
    <MapMarker
      longitude={lon}
      latitude={lat}
      onClick={() => onAgentSelect(agent)}
    >
      {/* Marker visual */}
      <MarkerContent>
        <div className="relative flex items-center justify-center cursor-pointer group">
          <div
            className="absolute inset-0 rounded-full animate-ping opacity-40"
            style={{ backgroundColor: color }}
          />
          <img
            src={avatarUrl}
            alt={agent.name}
            className="w-9 h-9 rounded-full border-2 shadow-lg transition-transform group-hover:scale-125"
            style={{ borderColor: color }}
          />
        </div>
      </MarkerContent>

      {/* Hover tooltip */}
      <MarkerTooltip
        className="!bg-transparent !p-0 !shadow-none"
        offset={[0, -8]}
      >
        <div
          className="min-w-[260px] rounded-lg border-2 bg-black/95 backdrop-blur-xl p-4 text-white shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-[#FE6B36]/30"
          style={{ borderLeftColor: color, borderLeftWidth: "4px" }}
        >
          {/* Header */}
          <div className="flex justify-between items-start mb-2 pb-2 border-b border-white/10">
            <div>
              <p className="font-bold text-base font-mono" style={{ color }}>
                {agent.name}
              </p>
              <p className="text-[10px] text-white/50 uppercase tracking-widest">
                {agent.city}
              </p>
            </div>
            <div className="text-right flex flex-col items-end">
              <div className="flex items-center text-[10px] font-bold text-white/60 uppercase">
                {icon} AGE {agent.age}
              </div>
              <p className="text-[10px] text-white/40 uppercase">
                {agent.race}
              </p>
            </div>
          </div>

          {/* Role + location */}
          <div className="space-y-1 mb-2">
            {agent.roleValue && (
              <div className="flex items-center gap-1.5 text-white/80">
                <Briefcase className="w-3 h-3" />
                <p className="text-[11px] font-mono">{agent.roleValue}</p>
              </div>
            )}
            <div className="flex items-center gap-1.5 text-white/50">
              <MapPin className="w-3 h-3" />
              <p className="text-[11px] font-mono">
                {lat.toFixed(2)}, {lon.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Soul archetype */}
          <div className="flex items-center gap-1.5 mb-2">
            <span
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ backgroundColor: color }}
            />
            <p
              className="text-[9px] font-bold uppercase tracking-widest font-mono"
              style={{ color }}
            >
              {agent.soul_type} archetype
            </p>
          </div>

          {/* Bio */}
          {agent.bio && (
            <p
              className="text-[9px] italic text-white/40 border-l-2 pl-2 leading-tight"
              style={{ borderColor: color }}
            >
              "{agent.bio}"
            </p>
          )}

          {/* Click hint */}
          <p className="text-[8px] text-white/20 mt-2 uppercase tracking-widest">
            Click to view full profile →
          </p>
        </div>
      </MarkerTooltip>
    </MapMarker>
  );
}

export function WorldMap({
  agents,
  selectedAgent,
  onAgentSelect,
  theme,
}: WorldMapProps) {
  return (
    <div className="relative w-full h-full">
      <Map center={[0, 20]} zoom={2} theme={theme} className="w-full h-full">
        <MapControls position="bottom-right" showZoom showCompass />

        {agents.map((agent) => (
          <AgentMarker
            key={agent.id}
            agent={agent}
            onAgentSelect={onAgentSelect}
          />
        ))}
      </Map>

      {/* Soul type legend */}
      <div className="absolute top-3 left-3 bg-black/70 border border-white/10 rounded-lg p-2.5 z-40 text-xs space-y-1 backdrop-blur-sm max-w-[140px]">
        <p className="font-semibold text-white/50 mb-1.5 text-[9px] uppercase tracking-widest">
          Soul Types
        </p>
        {Object.entries(SOUL_COLORS).map(([type, hex]) => {
          const count = agents.filter((a) => a.soul_type === type).length;
          return (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: hex }}
              />
              <span className="capitalize text-white/60 text-[10px] truncate">
                {type}
              </span>
              <span className="text-white/30 ml-auto text-[10px] font-mono">
                {count}
              </span>
            </div>
          );
        })}
      </div>

      {/* Hint */}
      <div className="absolute bottom-10 left-3 bg-black/50 border border-white/10 rounded-lg px-2.5 py-1.5 z-40 text-[9px] text-white/40 backdrop-blur-sm hidden sm:block">
        Hover agents for details • Click to select
      </div>
    </div>
  );
}
