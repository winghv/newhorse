"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";

interface Model {
  id: string;
  model_id: string;
  display_name: string;
  is_default: boolean;
}

interface ProviderGroup {
  provider_id: string;
  provider_name: string;
  protocol: string;
  has_api_key: boolean;
  models: Model[];
}

interface ModelSelectorProps {
  value?: string;              // current model_id
  providerId?: string;         // current provider_id
  onChange: (modelId: string, providerId: string) => void;
  className?: string;
}

export default function ModelSelector({ value, providerId, onChange, className = "" }: ModelSelectorProps) {
  const t = useTranslations('modelSelector');
  const [groups, setGroups] = useState<ProviderGroup[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/models")
      .then((r) => r.json())
      .then(setGroups)
      .catch(() => {});
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Find current display name
  const currentLabel = (() => {
    for (const g of groups) {
      for (const m of g.models) {
        if (m.model_id === value && (providerId ? g.provider_id === providerId : true)) {
          return m.display_name;
        }
      }
    }
    return value || t('selectModel');
  })();

  // Filter to only providers with API key configured
  const available = groups.filter((g) => g.has_api_key);

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 hover:border-zinc-600 text-sm text-zinc-300 transition-colors"
      >
        <span className="truncate max-w-[160px]">{currentLabel}</span>
        <ChevronDown className="w-3.5 h-3.5 text-zinc-500" />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-64 max-h-80 overflow-y-auto rounded-lg bg-zinc-800 border border-zinc-700 shadow-xl">
          {available.length === 0 && (
            <div className="px-3 py-2 text-sm text-zinc-500">{t('noProviders')}</div>
          )}
          {available.map((g) => (
            <div key={g.provider_id}>
              <div className="px-3 py-1.5 text-xs font-medium text-zinc-500 uppercase tracking-wide bg-zinc-900/50">
                {g.provider_name}
              </div>
              {g.models.map((m) => (
                <button
                  key={`${g.provider_id}-${m.model_id}`}
                  onClick={() => {
                    onChange(m.model_id, g.provider_id);
                    setOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-zinc-700 transition-colors ${
                    m.model_id === value && g.provider_id === providerId
                      ? "text-blue-400 bg-zinc-700/50"
                      : "text-zinc-300"
                  }`}
                >
                  {m.display_name}
                  <span className="ml-2 text-xs text-zinc-600">{m.model_id}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
