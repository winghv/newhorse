"use client";

import { useState } from "react";
import { X, Sparkles, ArrowRight, MessageSquare } from "lucide-react";

interface AgentCreatedModalProps {
  isOpen: boolean;
  agentName: string;
  agentDescription: string;
  agentModel: string;
  newProjectId: string;
  onConfirm: (data: { name: string; description: string; model: string }) => void;
  onCancel: () => void;
}

const MODEL_OPTIONS = [
  { value: "claude-sonnet-4-5-20250929", label: "Claude Sonnet 4.5" },
  { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
  { value: "claude-opus-4-6", label: "Claude Opus 4.6" },
];

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
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1.5">
              模型
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-blue-500 transition"
            >
              {MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
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
