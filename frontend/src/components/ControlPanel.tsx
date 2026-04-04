import React from "react";
import { Button } from "./ui/button";
import { Separator } from "./ui/separator";
import {
  Settings,
  Crown,
  ChevronRight,
  ChevronLeft,
  Users,
  Globe,
  Thermometer,
  Wind,
  Droplets,
  Zap,
} from "lucide-react";

interface ControlPanelProps {
  agentCount: number;
  onSpawn: (count: number) => void;
  onReset: () => void;
  isLoading?: boolean;
  onTriggerEvent?: (eventName: string) => void;
  currentYear: number;
  onYearChange: (year: number) => void;
}

const MIN_WIDTH = 52;
const DEFAULT_WIDTH = 220;
const MAX_WIDTH = 420;

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  onChange,
  displayValue,
  icon: Icon,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  displayValue?: string;
  icon?: React.ElementType;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-[9px] uppercase tracking-widest text-white/40 flex items-center gap-1">
          {Icon && <Icon className="w-3 h-3" />}
          {label}
        </span>
        <span className="text-[11px] font-mono text-white/80">
          {displayValue ?? value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 appearance-none rounded-full bg-muted outline-none accent-[#FE6B36] cursor-pointer [&::-webkit-scrollbar]:hidden"
        style={{ scrollbarWidth: "none" }}
      />
    </div>
  );
}

export function ControlPanel({
  agentCount,
  onSpawn,
  onReset,
  isLoading,
  onTriggerEvent,
  currentYear,
  onYearChange,
}: ControlPanelProps) {
  const [spawnCount, setSpawnCount] = React.useState(1);
  const [customEvent, setCustomEvent] = React.useState("");
  // Auto-collapse on small viewports
  const [collapsed, setCollapsed] = React.useState(
    () => typeof window !== "undefined" && window.innerWidth < 768,
  );
  const [width, setWidth] = React.useState(DEFAULT_WIDTH);
  const [temperature, setTemperature] = React.useState(22);
  const [windSpeed, setWindSpeed] = React.useState(12);
  const [rainfall, setRainfall] = React.useState(45);
  const [conflictLevel, setConflictLevel] = React.useState(30);
  const isDragging = React.useRef(false);
  const startX = React.useRef(0);
  const startW = React.useRef(0);

  const onMouseDown = (e: React.MouseEvent) => {
    if (collapsed) return;
    isDragging.current = true;
    startX.current = e.clientX;
    startW.current = width;
    e.preventDefault();
  };

  React.useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = e.clientX - startX.current;
      setWidth(
        Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startW.current + delta)),
      );
    };
    const onUp = () => {
      isDragging.current = false;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const era =
    currentYear < 1000
      ? "Ancient"
      : currentYear < 1800
        ? "Medieval"
        : currentYear < 2000
          ? "Industrial"
          : currentYear < 2100
            ? "Modern"
            : "Future";

  const panelWidth = collapsed ? 0 : width;

  return (
    <div
      className="relative flex h-full shrink-0"
      style={{
        width: panelWidth,
        transition: "width 0.2s ease",
        overflow: "visible",
      }}
    >
      {/* Main sidebar */}
      <aside
        className="flex-1 bg-card border-r border-border flex flex-col overflow-hidden"
        style={{ overflow: "hidden", minWidth: 0 }}
      >
        {!collapsed && (
          <div
            className="flex flex-col gap-0 overflow-y-auto flex-1 p-4 scrollbar-none"
            style={{ scrollbarWidth: "none" }}
          >
            {/* World Settings */}
            <div>
              <h3 className="text-[9px] font-bold uppercase tracking-widest text-white/40 mb-4 flex items-center gap-2">
                <Settings className="w-3.5 h-3.5" /> World Settings
              </h3>

              <div className="space-y-3">
                <Button
                  onClick={() => onSpawn(spawnCount)}
                  disabled={isLoading}
                  className="w-full bg-[#FE6B36] hover:bg-[#FE6B36]/90 text-white font-bold tracking-tight shadow-[0_0_15px_rgba(254,107,54,0.2)] text-xs"
                >
                  {isLoading ? (
                    <div className="flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Spawning...</span>
                    </div>
                  ) : (
                    `Spawn Agents (${spawnCount.toLocaleString()})`
                  )}
                </Button>

                <SliderRow
                  label="Agent Count"
                  value={spawnCount}
                  min={1}
                  max={9999}
                  step={1}
                  onChange={(v) => setSpawnCount(v)}
                  displayValue={spawnCount.toLocaleString()}
                  icon={Users}
                />
              </div>

              <Separator className="my-5" />

              {/* Timeline */}
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="text-[9px] font-bold uppercase tracking-widest text-[#FE6B36] flex items-center gap-1.5">
                    <Globe className="w-3 h-3" /> Timeline
                  </h3>
                  <div className="text-right">
                    <span className="text-base font-black text-white font-mono leading-none">
                      {currentYear}
                    </span>
                    <p className="text-[8px] uppercase tracking-widest text-white/30 leading-none mt-0.5">
                      {era} Era
                    </p>
                  </div>
                </div>
                <input
                  type="range"
                  min={100}
                  max={3000}
                  step={1}
                  value={currentYear}
                  onChange={(e) => onYearChange(parseInt(e.target.value))}
                  className="w-full h-1 appearance-none rounded-full bg-muted outline-none accent-[#FE6B36] cursor-pointer"
                  style={{ scrollbarWidth: "none" }}
                />
              </div>

              <Separator className="my-5" />

              {/* Environment */}
              <div className="space-y-4">
                <h3 className="text-[9px] font-bold uppercase tracking-widest text-white/40 flex items-center gap-2">
                  <Thermometer className="w-3.5 h-3.5" /> Environment
                </h3>
                <SliderRow
                  label="Temperature"
                  value={temperature}
                  min={-30}
                  max={50}
                  step={1}
                  onChange={setTemperature}
                  displayValue={`${temperature}°C`}
                  icon={Thermometer}
                />
                <SliderRow
                  label="Wind Speed"
                  value={windSpeed}
                  min={0}
                  max={120}
                  step={1}
                  onChange={setWindSpeed}
                  displayValue={`${windSpeed} km/h`}
                  icon={Wind}
                />
                <SliderRow
                  label="Rainfall"
                  value={rainfall}
                  min={0}
                  max={100}
                  step={1}
                  onChange={setRainfall}
                  displayValue={`${rainfall}%`}
                  icon={Droplets}
                />
                <SliderRow
                  label="Conflict Level"
                  value={conflictLevel}
                  min={0}
                  max={100}
                  step={1}
                  onChange={setConflictLevel}
                  displayValue={`${conflictLevel}%`}
                  icon={Zap}
                />
              </div>

              <Separator className="my-5" />

              {/* God Mode */}
              <div className="space-y-3">
                <h3 className="text-[9px] font-bold uppercase tracking-widest text-white/40 mb-3 flex items-center gap-2">
                  <Crown className="w-3.5 h-3.5" /> God Mode
                </h3>
                <textarea
                  rows={2}
                  placeholder="E.g., Trump dies"
                  value={customEvent}
                  onChange={(e) => setCustomEvent(e.target.value)}
                  className="w-full bg-input border border-border rounded p-2 text-xs text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-[#FE6B36] resize-none"
                />
                <Button
                  onClick={() => {
                    if (customEvent) {
                      onTriggerEvent?.(customEvent);
                      setCustomEvent("");
                    }
                  }}
                  variant="outline"
                  className="w-full text-xs text-[#FE6B36] border-[#FE6B36]/30 hover:bg-[#FE6B36]/10"
                >
                  Trigger Event
                </Button>
              </div>

              <Separator className="my-5" />

              {/* Stats */}
              <div className="space-y-2 text-[10px] text-muted-foreground mt-auto">
                <div className="flex justify-between">
                  <span>Total Agents</span>
                  <span className="text-[#FE6B36] font-mono">
                    {agentCount.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Era</span>
                  <span className="text-white/60 font-mono">{era}</span>
                </div>
                <div className="flex justify-between">
                  <span>Conflict</span>
                  <span
                    className="font-mono"
                    style={{
                      color:
                        conflictLevel > 60
                          ? "#ef4444"
                          : conflictLevel > 30
                            ? "#f59e0b"
                            : "#22c55e",
                    }}
                  >
                    {conflictLevel}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Climate</span>
                  <span className="text-blue-400 font-mono">
                    {temperature}°C
                  </span>
                </div>
              </div>

              <Separator className="my-4" />

              <Button
                onClick={onReset}
                variant="destructive"
                className="w-full text-xs"
              >
                Reset Simulation
              </Button>
            </div>
          </div>
        )}
      </aside>

      {/* Drag resize handle */}
      {!collapsed && (
        <div
          onMouseDown={onMouseDown}
          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-[#FE6B36]/40 transition-colors z-10"
        />
      )}

      {/* Collapse toggle — centred bulge tab, always visible */}
      <button
        onClick={() => setCollapsed((v) => !v)}
        style={{ right: -16 }}
        className="absolute top-1/2 -translate-y-1/2 z-[30] flex items-center justify-center w-4 h-10 bg-card border border-l-0 border-border rounded-r-md hover:bg-[#FE6B36]/10 hover:border-[#FE6B36]/40 transition-colors shadow-[2px_0_8px_rgba(0,0,0,0.4)]"
        title={collapsed ? "Expand panel" : "Collapse panel"}
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3 text-white/50" />
        ) : (
          <ChevronLeft className="w-3 h-3 text-white/50" />
        )}
      </button>
    </div>
  );
}
