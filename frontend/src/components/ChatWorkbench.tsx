import React from "react";
import { SendHorizonal, Sparkles } from "lucide-react";
import { sendWorkbenchQuery } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatWorkbenchProps {
  runId?: string | null;
  selectedAgent?: { id: string; name: string } | null;
  theme?: "light" | "dark";
}

const QUICK_PROMPTS = [
  "Who influences whom in this run?",
  "Which agents are the most connected?",
  "Summarize conflict relationships.",
  "What patterns are visible in migration intent?",
];

export function ChatWorkbench({
  runId,
  selectedAgent,
  theme,
}: ChatWorkbenchProps) {
  const resolvedTheme =
    theme ??
    (document.documentElement.classList.contains("light") ? "light" : "dark");
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Atlas Workbench ready. Ask about agent relationships, influence paths, or conflict clusters.",
    },
  ]);
  const [query, setQuery] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const ask = async (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuery("");
    setLoading(true);

    try {
      const payloadQuery = selectedAgent
        ? `${trimmed}\nFocus on agent: ${selectedAgent.name} (${selectedAgent.id})`
        : trimmed;

      const res = await sendWorkbenchQuery({
        query: payloadQuery,
        run_id: runId,
        top_k: 8,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.response },
      ]);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Workbench request failed";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Workbench error: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-card">
      <div className="px-3 py-2 border-b border-border flex items-center justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-widest font-bold text-foreground/80">
            General Chat / Workbench
          </p>
          <p className="text-[10px] text-muted-foreground">
            Run: {runId ? runId.slice(0, 8) : "none"}
          </p>
        </div>
        <span className="text-[9px] px-2 py-1 rounded border border-border text-muted-foreground">
          {selectedAgent ? `Scoped: ${selectedAgent.name}` : "Global"}
        </span>
      </div>

      <div className="px-3 py-2 border-b border-border/70 flex flex-wrap gap-1.5">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => ask(prompt)}
            className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-[#FE6B36]/40"
          >
            {prompt}
          </button>
        ))}
      </div>

      <div
        className={`flex-1 overflow-y-auto px-3 py-3 space-y-2 ${
          resolvedTheme === "light" ? "bg-[#f6f4ee]" : "bg-[#0b0b0b]"
        }`}
      >
        {messages.map((m, idx) => (
          <div
            key={`${m.role}-${idx}`}
            className={`max-w-[92%] rounded-lg px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap ${
              m.role === "user"
                ? resolvedTheme === "light"
                  ? "ml-auto bg-[#FE6B36]/15 border border-[#FE6B36]/40 text-slate-900"
                  : "ml-auto bg-[#FE6B36]/15 border border-[#FE6B36]/40 text-white"
                : resolvedTheme === "light"
                  ? "mr-auto bg-slate-100 border border-slate-300 text-slate-800"
                  : "mr-auto bg-white/[0.04] border border-white/10 text-white/80"
            }`}
          >
            {m.content}
          </div>
        ))}

        {loading && (
          <div
            className={`mr-auto rounded-lg px-3 py-2 text-[12px] flex items-center gap-2 ${
              resolvedTheme === "light"
                ? "bg-slate-100 border border-slate-300 text-slate-800"
                : "bg-white/[0.04] border border-white/10 text-white/80"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-[#FE6B36] animate-pulse" />
            Working on relationship query...
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(query);
        }}
        className="p-3 border-t border-border flex items-center gap-2"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything about graph relationships..."
          className="flex-1 bg-background border border-border rounded-md px-3 py-2 text-[12px] text-foreground placeholder:text-muted-foreground outline-none focus:border-[#FE6B36]/50"
        />
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="px-3 py-2 rounded-md border border-[#FE6B36]/40 text-[#FE6B36] hover:bg-[#FE6B36]/10 disabled:opacity-40"
        >
          <SendHorizonal className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
