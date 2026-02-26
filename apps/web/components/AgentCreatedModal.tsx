"use client";

import { useState, useEffect, useRef } from "react";
import { X, Sparkles, ArrowRight, MessageSquare, ChevronDown } from "lucide-react";

interface Model {
  id: string;
  model_id: string;
  display_name: string;
}

interface ProviderGroup {
  provider_id: string;
  provider_name: string;
  has_api_key: boolean;
  models: Model[];
}

interface AgentCreatedModalProps {
  isOpen: boolean;
  agentName: string;
  agentDescription: string;
  agentModel: string;
  newProjectId: string;
  onConfirm: (data: { name: string; description: string; model: string }) => void;
  onCancel: () => void;
}

export function AgentCreatedModal({
  isOpen,
  agentName,
  agentDescription,
  agentModel,
  newProjectId,
  onConfirm,
  onCancel,
}: AgentCreatedModalProps) {
  const [name, setName] = useState(agentName);
  const [description, setDescription] = useState(agentDescription);
  const [model, setModel] = useState(agentModel);
  const [providerGroups, setProviderGroups] = useState<ProviderGroup[]>([]);
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setShowModelDropdown(false);
      }
    };
    if (showModelDropdown) {
      document.addEventListener("mousedown", handler);
      return () => document.removeEventListener("mousedown", handler);
    }
  }, [showModelDropdown]);

  // Fetch available models
  useEffect(() => {
    if (!isOpen) return;
    fetch("/api/models")
      .then((r) => r.json())
      .then(setProviderGroups)
      .catch(() => {});
  }, [isOpen]);

  // Filter to providers with API key
  const availableGroups = providerGroups.filter((g) => g.has_api_key);

  // Find current model display name
  const currentModelName = (() => {
    for (const g of availableGroups) {
      for (const m of g.models) {
        if (m.model_id === model) return m.display_name;
      }
    }
    return model;
  })();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-600/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="font-semibold text-lg">Agent 已生成</h2>
              <p className="text-xs text-zinc-500">确认信息后开始使用</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-1.5 hover:bg-zinc-800 rounded-lg transition"
          >
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1.5">
              名称
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1.5">
              描述
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-blue-500 transition resize-none"
            />
          </div>

          {/* Model */}
          <div className="relative" ref={modelDropdownRef}>
            <label className="block text-sm font-medium text-zinc-400 mb-1.5">
              模型
            </label>
            <button
              type="button"
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              className="w-full flex items-center justify-between px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-blue-500 transition"
            >
              <span className="truncate">{currentModelName}</span>
              <ChevronDown className="w-4 h-4 text-zinc-500 flex-shrink-0" />
            </button>
            {showModelDropdown && (
              <div className="absolute z-10 w-full mt-1 max-h-48 overflow-y-auto bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg">
                {availableGroups.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-zinc-500">No providers configured</div>
                ) : (
                  availableGroups.map((g) => (
                    <div key={g.provider_id}>
                      <div className="px-3 py-1.5 text-xs font-medium text-zinc-500 uppercase bg-zinc-900/50">
                        {g.provider_name}
                      </div>
                      {g.models.map((m) => (
                        <button
                          key={`${g.provider_id}-${m.model_id}`}
                          type="button"
                          onClick={() => {
                            setModel(m.model_id);
                            setShowModelDropdown(false);
                          }}
                          className={`w-full text-left px-3 py-2 text-sm hover:bg-zinc-700 ${
                            m.model_id === model ? "text-blue-400 bg-zinc-700/50" : "text-zinc-300"
                          }`}
                        >
                          {m.display_name}
                        </button>
                      ))}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-800">
          <button
            onClick={onCancel}
            className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition"
          >
            <MessageSquare className="w-4 h-4" />
            继续修改
          </button>
          <button
            onClick={() => onConfirm({ name, description, model })}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-500 rounded-lg transition"
          >
            确认并前往
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
