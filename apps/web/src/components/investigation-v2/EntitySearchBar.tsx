"use client";

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";

interface EntitySearchBarProps {
  onSearch: (query: string, type: string) => void;
  placeholder?: string;
  initialQuery?: string;
  initialType?: string;
}

const ENTITY_TYPES = [
  { value: "", label: "Todos" },
  { value: "company", label: "Empresa" },
  { value: "person", label: "Pessoa" },
  { value: "org", label: "Orgao" },
];

export function EntitySearchBar({
  onSearch,
  placeholder = "Nome da entidade...",
  initialQuery = "",
  initialType = "",
}: EntitySearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const [type, setType] = useState(initialType);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) return;

    debounceRef.current = setTimeout(() => {
      onSearch(query.trim(), type);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, type, onSearch]);

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-xl border border-border bg-surface-card py-2.5 pl-10 pr-3 text-sm text-primary placeholder:text-placeholder outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
        />
      </div>
      <select
        value={type}
        onChange={(e) => setType(e.target.value)}
        className="rounded-xl border border-border bg-surface-card px-3 py-2.5 text-sm text-primary outline-none focus:border-accent/50"
      >
        {ENTITY_TYPES.map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </select>
    </div>
  );
}
