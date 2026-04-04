import React from "react";

// Simple markdown to JSX renderer
export function MarkdownRenderer({ content }: { content: string }) {
  if (!content) return null;

  // Split by lines and process
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // Headers (# ## ###)
    if (trimmed.startsWith("#")) {
      const level = trimmed.match(/^#+/)?.[0].length ?? 1;
      const text = trimmed.slice(level).trim();
      const tag = `h${Math.min(level, 6)}` as const;
      elements.push(
        React.createElement(
          tag,
          { key: `header-${i}`, className: "font-bold mb-2 mt-3 text-white" },
          text,
        ),
      );
    }
    // Bold text **text** or __text__
    else if (trimmed.includes("**") || trimmed.includes("__")) {
      const processed = trimmed
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/__(.*?)__/g, "<strong>$1</strong>");
      elements.push(
        <p
          key={`para-${i}`}
          className="text-white/75 mb-2 leading-relaxed"
          dangerouslySetInnerHTML={{ __html: processed }}
        />,
      );
    }
    // Italic text *text* or _text_
    else if (
      (trimmed.match(/\*/g)?.length ?? 0) > 0 ||
      (trimmed.match(/_/g)?.length ?? 0) > 0
    ) {
      const processed = trimmed
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/_(.*?)_/g, "<em>$1</em>");
      elements.push(
        <p
          key={`para-${i}`}
          className="text-white/75 mb-2 leading-relaxed italic"
          dangerouslySetInnerHTML={{ __html: processed }}
        />,
      );
    }
    // Bullet lists
    else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const listItems = [];
      while (
        i < lines.length &&
        (lines[i].trim().startsWith("- ") || lines[i].trim().startsWith("* "))
      ) {
        const item = lines[i].trim().slice(2).trim();
        listItems.push(
          <li key={`li-${i}`} className="text-white/75 ml-4 mb-1">
            {item}
          </li>,
        );
        i++;
      }
      elements.push(
        <ul key={`list-${elements.length}`} className="mb-3">
          {listItems}
        </ul>,
      );
      i--; // Step back since we increment at end of loop
    }
    // Regular paragraphs
    else {
      elements.push(
        <p key={`para-${i}`} className="text-white/75 mb-2 leading-relaxed">
          {trimmed}
        </p>,
      );
    }

    i++;
  }

  return <div className="space-y-1">{elements}</div>;
}
