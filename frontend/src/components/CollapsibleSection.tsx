import React from "react";
import { ChevronDown } from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface CollapsibleSectionProps {
  id: string;
  label: React.ReactNode;
  value: string;
  color?: string;
  defaultOpen?: boolean;
}

export function CollapsibleSection({
  id,
  label,
  value,
  color = "#FE6B36",
  defaultOpen = false,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  if (!value) return null;

  return (
    <div className="border rounded-lg bg-white/2 border-white/5 overflow-hidden">
      {/* Header - clickable to toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <div
          className="text-[10px] font-bold uppercase tracking-widest flex items-center gap-2"
          style={{ color }}
        >
          {label}
        </div>
        <ChevronDown
          className="w-4 h-4 transition-transform shrink-0"
          style={{
            color,
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
          }}
        />
      </button>

      {/* Content - collapsible with markdown rendering */}
      {isOpen && (
        <div className="px-4 pb-3 border-t border-white/5 pt-3 bg-black/20">
          <div className="text-[12px] text-white/75 leading-relaxed">
            <MarkdownRenderer content={value} />
          </div>
        </div>
      )}
    </div>
  );
}
