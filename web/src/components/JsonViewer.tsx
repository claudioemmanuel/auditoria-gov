"use client";

import { useState, useCallback } from "react";
import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";

function JsonValue({ value, depth, defaultExpand }: { value: unknown; depth: number; defaultExpand: number }) {
  const [expanded, setExpanded] = useState(depth < defaultExpand);

  if (value === null) return <span className="text-placeholder italic">null</span>;
  if (value === undefined) return <span className="text-placeholder italic">undefined</span>;
  if (typeof value === "boolean") return <span className="text-amber-600">{String(value)}</span>;
  if (typeof value === "number") return <span className="text-accent">{value}</span>;
  if (typeof value === "string") {
    if (value.length > 120) {
      return <span className="text-emerald-600">&quot;{value.slice(0, 120)}&hellip;&quot;</span>;
    }
    return <span className="text-emerald-600">&quot;{value}&quot;</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-muted">[]</span>;

    return (
      <span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-0.5 text-muted hover:text-secondary"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className="text-xs">[{value.length}]</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-border pl-3">
            {value.map((item, i) => (
              <div key={i} className="py-0.5">
                <span className="text-placeholder text-xs mr-1">{i}:</span>
                <JsonValue value={item} depth={depth + 1} defaultExpand={defaultExpand} />
              </div>
            ))}
          </div>
        )}
      </span>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) return <span className="text-muted">{"{}"}</span>;

    return (
      <span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-0.5 text-muted hover:text-secondary"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className="text-xs">{"{"}...{"}"} {entries.length} keys</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-border pl-3">
            {entries.map(([key, val]) => (
              <div key={key} className="py-0.5">
                <span className="text-accent-hover font-medium text-sm">{key}</span>
                <span className="text-placeholder mx-1">:</span>
                <JsonValue value={val} depth={depth + 1} defaultExpand={defaultExpand} />
              </div>
            ))}
          </div>
        )}
      </span>
    );
  }

  return <span className="text-secondary">{String(value)}</span>;
}

export default function JsonViewer({
  data,
  defaultExpand = 2,
  className = "",
}: {
  data: unknown;
  defaultExpand?: number;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data]);

  return (
    <div className={`relative rounded-lg bg-surface-base border border-border ${className}`}>
      <div className="absolute top-2 right-2 z-10">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-surface-card border border-border text-secondary hover:bg-surface-subtle transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copiado" : "Copiar"}
        </button>
      </div>
      <div className="p-4 max-h-[400px] overflow-y-auto text-sm font-mono leading-relaxed">
        <JsonValue value={data} depth={0} defaultExpand={defaultExpand} />
      </div>
    </div>
  );
}
