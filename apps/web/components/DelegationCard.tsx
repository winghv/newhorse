"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Loader2,
  XCircle,
  FileEdit,
  Search,
  FolderSearch,
  Terminal,
  FileText,
  Eye,
} from "lucide-react";

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

const AGENT_LABELS: Record<string, string> = {
  planner: "Planner",
  coder: "Coder",
  researcher: "Researcher",
  reviewer: "Reviewer",
  writer: "Writer",
};

const AGENT_COLORS: Record<string, string> = {
  planner: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  coder: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  researcher: "text-green-400 bg-green-400/10 border-green-400/30",
  reviewer: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  writer: "text-purple-400 bg-purple-400/10 border-purple-400/30",
};

const TOOL_ICONS: Record<string, typeof FileEdit> = {
  Read: Eye,
  Write: FileText,
  Edit: FileEdit,
  Grep: Search,
  Glob: FolderSearch,
  Bash: Terminal,
};

function ToolIcon({ name }: { name: string }) {
  const Icon = TOOL_ICONS[name] || Terminal;
  return <Icon className="w-3 h-3 flex-shrink-0" />;
}

export function DelegationCard({ message, updates = [], completion }: DelegationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const agentType = message.metadata?.agent_type || "unknown";
  const task = message.metadata?.task || message.content;
  const isComplete = !!completion;
  const hasError = completion?.metadata?.error;
  const colorClass = AGENT_COLORS[agentType] || "text-zinc-400 bg-zinc-400/10 border-zinc-400/30";
  const label = AGENT_LABELS[agentType] || agentType;

  // Parse tool updates to extract tool name and file
  const parseUpdate = (content: string) => {
    const parts = content.trim().split(" ");
    const toolName = parts[0] || "";
    const fileName = parts.slice(1).join(" ") || "";
    return { toolName, fileName };
  };

  return (
    <div
      className={`rounded-lg border transition-all ${
        isComplete
          ? hasError
            ? "border-red-800/50 bg-red-950/30"
            : "border-zinc-700/50 bg-zinc-900/40"
          : "border-zinc-600/60 bg-zinc-900/70 shadow-sm shadow-zinc-800/50"
      }`}
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-left cursor-pointer hover:bg-zinc-800/30 rounded-lg transition-colors"
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
        <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${colorClass}`}>
          {label}
        </span>

        {/* Task text */}
        <span className="text-sm text-zinc-300 truncate flex-1">
          {task.length > 80 ? task.slice(0, 80) + "..." : task}
        </span>

        {/* Step counter + expand chevron */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {updates.length > 0 && (
            <span className="text-[10px] text-zinc-500 tabular-nums">
              {updates.length} steps
            </span>
          )}
          {(updates.length > 0 || completion) && (
            expanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-zinc-500" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-zinc-500" />
            )
          )}
        </div>
      </button>

      {/* Expanded content — tool steps */}
      {expanded && (updates.length > 0 || completion) && (
        <div className="px-3.5 pb-3 border-t border-zinc-800/70 pt-2 space-y-0.5">
          {updates.map((u) => {
            const { toolName, fileName } = parseUpdate(u.content);
            return (
              <div key={u.id} className="flex items-center gap-2 py-0.5 text-xs text-zinc-500">
                <ToolIcon name={toolName} />
                <span className="font-medium text-zinc-400">{toolName}</span>
                {fileName && (
                  <span className="text-zinc-600 truncate font-mono">{fileName}</span>
                )}
              </div>
            );
          })}
          {completion && (
            <div className={`flex items-center gap-2 text-xs mt-1.5 pt-1.5 border-t border-zinc-800/50 ${
              hasError ? "text-red-400" : "text-green-400"
            }`}>
              {hasError ? (
                <XCircle className="w-3 h-3 flex-shrink-0" />
              ) : (
                <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
              )}
              {completion.content}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
