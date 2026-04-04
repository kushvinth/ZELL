import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { generatePersona } from "@/lib/api";
import { Zap, Heart, Brain, PartyPopper, MapPin } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  age: number;
  race: string;
  soul_type: "aggressive" | "altruistic" | "technocratic" | "hedonistic";
  bio?: string;
  location: [number, number];
  city: string;
  roleLabel?: string;
  roleValue?: string;
  persona?: Record<string, string>;
}

interface AgentCardProps {
  agent: Agent;
}

const SOUL_CONFIG: Record<
  string,
  { bg: string; border: string; text: string; icon: React.ReactNode }
> = {
  aggressive: {
    bg: "bg-red-500/10",
    border: "border-[#ef4444]",
    text: "text-[#ef4444]",
    icon: <Zap className="w-4 h-4" />,
  },
  altruistic: {
    bg: "bg-cyan-500/10",
    border: "border-[#06b6d4]",
    text: "text-[#06b6d4]",
    icon: <Heart className="w-4 h-4" />,
  },
  technocratic: {
    bg: "bg-purple-500/10",
    border: "border-[#a855f7]",
    text: "text-[#a855f7]",
    icon: <Brain className="w-4 h-4" />,
  },
  hedonistic: {
    bg: "bg-amber-500/10",
    border: "border-[#f59e0b]",
    text: "text-[#f59e0b]",
    icon: <PartyPopper className="w-4 h-4" />,
  },
};

export function AgentCard({ agent }: AgentCardProps) {
  const [persona, setPersona] = React.useState<Record<string, string>>({});
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!agent.id) return;
    const fetchPersona = async () => {
      setLoading(true);
      try {
        const data = await generatePersona(agent.id, {
          name: agent.name,
          age: agent.age,
          ethnicity: agent.race,
          role: agent.roleValue,
          role_label: agent.roleLabel,
          personality_archetype: agent.soul_type,
        });
        if (data.sections) setPersona(data.sections);
      } catch (err) {
        console.error("Error fetching persona:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPersona();
  }, [agent.id]);

  const config = SOUL_CONFIG[agent.soul_type] || SOUL_CONFIG.altruistic;

  return (
    <Card className={`w-72 ${config.bg} border-2 ${config.border}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>{config.icon}</span>
              {agent.name}
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">{agent.city}</p>
          </div>
          <div className="text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {agent.soul_type}
            </p>
            <p className="text-xs text-muted-foreground">Age {agent.age}</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Background</p>
          <p className="text-sm text-foreground">{agent.race}</p>
        </div>

        {agent.roleLabel && agent.roleValue && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">
              {agent.roleLabel}
            </p>
            <p className="text-sm text-foreground font-medium">
              {agent.roleValue}
            </p>
          </div>
        )}

        {agent.bio && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">Bio</p>
            <p className="text-xs text-foreground leading-relaxed">
              {agent.bio}
            </p>
          </div>
        )}

        {loading && (
          <p className="text-xs text-[#FE6B36] animate-pulse">
            Loading persona sections...
          </p>
        )}

        {Object.entries(persona).length > 0 && (
          <div className="space-y-4 pt-2 border-t border-border">
            {Object.entries(persona).map(([section, content]) => (
              <div key={section} className="space-y-1">
                <p
                  className={`text-[10px] font-bold uppercase tracking-widest ${config.text}`}
                >
                  {section}
                </p>
                <div className="text-[11px] text-foreground/90 leading-relaxed max-h-32 overflow-y-auto pr-2">
                  {content}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <MapPin className="w-3 h-3" /> {agent.location[1].toFixed(2)},{" "}
            {agent.location[0].toFixed(2)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
