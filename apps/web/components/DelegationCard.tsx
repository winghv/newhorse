"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, Loader2, XCircle } from "lucide-react";

interface DelegationCardProps {
  message: {
    id: string;
    type: string;
    content: string;
    metadata?: Record<string, any>;
  };
  updates?: Array<{
    id: string;
    content: string;
    metadata?: Record<string, any>;
  }>;
  completion?: {
    id: string;
    content: string;
    metadata?: Record<string, any>;
  };
}

const AGENT_COLORS: Record<string, string> = {
  planner: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  coder: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  researcher: "text-green-400 bg-green-400/10 border-green-400/20",
  reviewer: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  writer: "text-purple-400 bg-purple-400/10 border-purple-400/20",
};

export function DelegationCard({ message, updates = [], completion }: DelegationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const agentType = message.metadata?.agent_type || "unknown";
  const task = message.metadata?.task || message.content;
  const isComplete = !!completion;
  const hasError = completion?.metadata?.error;
  const colorClass = AGENT_COLORS[agentType] || "text-zinc-400 bg-zinc-400/10 border-zinc-400/20";

  return (
    <div
      className={`rounded-lg border transition-colors ${
        isComplete
          ? hasError
            ? "border-red-800/50 bg-red-900/10"
            : "border-zinc-700/50 bg-zinc-900/50"
          : "border-zinc-700 bg-zinc-900/80"
      }`}
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left cursor-pointer"
      >
        {/* Status icon */}
        {isComplete ? (
          hasError ? (
            <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
          )
        ) : (
          <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
        )}

        {/* Agent badge */}
        <span className={`px-2 py-0.5 rounded-md text-xs font-medium border ${colorClass}`}>
          {agentType}
        </span>

        {/* Task text */}
        <span className="text-sm text-zinc-300 truncate flex-1">
          {task.length > 80 ? task.slice(0, 80) + "..." : task}
        </span>

        {/* Expand chevron */}
        {(updates.length > 0 || completion) && (
          expanded ? (
            <ChevronDown className="w-4 h-4 text-zinc-500 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-zinc-500 flex-shrink-0" />
          )
        )}
      </button>

      {/* Expanded content */}
      {expanded && (updates.length > 0 || completion) && (
        <div className="px-3 pb-3 border-t border-zinc-800 pt-2 space-y-1">
          {updates.map((u) => (
            <div key={u.id} className="text-xs text-zinc-500 font-mono pl-2">
              {u.content}
            </div>
          ))}
          {completion && (
            <div className={`text-xs mt-2 pl-2 ${hasError ? "text-red-400" : "text-green-400"}`}>
              {completion.content}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
