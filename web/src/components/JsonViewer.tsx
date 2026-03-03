"use client";

import { useState, useCallback } from "react";
import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";

function JsonValue({ value, depth, defaultExpand }: { value: unknown; depth: number; defaultExpand: number }) {
  const [expanded, setExpanded] = useState(depth < defaultExpand);

  if (value === null) return <span className="text-gov-gray-400 italic">null</span>;
  if (value === undefined) return <span className="text-gov-gray-400 italic">undefined</span>;
  if (typeof value === "boolean") return <span className="text-amber-600">{String(value)}</span>;
  if (typeof value === "number") return <span className="text-gov-blue-600">{value}</span>;
  if (typeof value === "string") {
    if (value.length > 120) {
      return <span className="text-gov-teal-500">&quot;{value.slice(0, 120)}&hellip;&quot;</span>;
    }
    return <span className="text-gov-teal-500">&quot;{value}&quot;</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gov-gray-500">[]</span>;

    return (
      <span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-0.5 text-gov-gray-500 hover:text-gov-gray-700"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className="text-xs">[{value.length}]</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-gov-gray-200 pl-3">
            {value.map((item, i) => (
              <div key={i} className="py-0.5">
                <span className="text-gov-gray-400 text-xs mr-1">{i}:</span>
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
    if (entries.length === 0) return <span className="text-gov-gray-500">{"{}"}</span>;

    return (
      <span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-0.5 text-gov-gray-500 hover:text-gov-gray-700"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          <span className="text-xs">{"{"}...{"}"} {entries.length} keys</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-gov-gray-200 pl-3">
            {entries.map(([key, val]) => (
              <div key={key} className="py-0.5">
                <span className="text-gov-blue-800 font-medium text-sm">{key}</span>
                <span className="text-gov-gray-400 mx-1">:</span>
                <JsonValue value={val} depth={depth + 1} defaultExpand={defaultExpand} />
              </div>
            ))}
          </div>
        )}
      </span>
    );
  }

  return <span className="text-gov-gray-600">{String(value)}</span>;
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
    <div className={`relative rounded-lg bg-gov-gray-50 border border-gov-gray-200 ${className}`}>
      <div className="absolute top-2 right-2 z-10">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-white border border-gov-gray-200 text-gov-gray-600 hover:bg-gov-gray-100 transition-colors"
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
