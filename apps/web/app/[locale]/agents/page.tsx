"use client";

import { useState, useEffect, useCallback } from "react";
import { Link } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Bot,
  Plus,
  Trash2,
  Pencil,
  Shield,
  Eye,
  X,
  Save,
  Code2,
  Wrench,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";
import ModelSelector from "@/components/ModelSelector";

/* ── Types ── */

interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  source: string;
  path?: string;
}

interface AgentConfigData {
  name: string;
  description: string;
  system_prompt: string;
  skills: string[];
  model: string;
  allowed_tools: string[];
}

const DEFAULT_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"];
const ALL_TOOLS = [
  "Read", "Write", "Edit", "Bash", "Glob", "Grep",
  "WebFetch", "WebSearch", "NotebookEdit",
];

const emptyConfig: AgentConfigData = {
  name: "",
  description: "",
  system_prompt: "",
  skills: [],
  model: "claude-sonnet-4-5-20250929",
  allowed_tools: [...DEFAULT_TOOLS],
};

/* ── Helpers ── */

function configToYaml(config: AgentConfigData): string {
  const lines: string[] = [];
  lines.push(`name: "${config.name}"`);
  lines.push(`description: "${config.description}"`);
  lines.push("");
  lines.push("system_prompt: |");
  config.system_prompt.split("\n").forEach((line) => {
    lines.push(`  ${line}`);
  });
  lines.push("");
  if (config.skills.length > 0) {
    lines.push("skills:");
    config.skills.forEach((s) => lines.push(`  - ${s}`));
    lines.push("");
  }
  lines.push(`model: "${config.model}"`);
  lines.push("");
  lines.push("allowed_tools:");
  config.allowed_tools.forEach((t) => lines.push(`  - ${t}`));
  return lines.join("\n");
}

/* ── Component ── */

export default function AgentsPage() {
  const t = useTranslations("agents");

  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  // Editor state
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [config, setConfig] = useState<AgentConfigData>({ ...emptyConfig });
  const [saving, setSaving] = useState(false);
  const [showYaml, setShowYaml] = useState(false);

  // Preview state
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewConfig, setPreviewConfig] = useState<AgentConfigData | null>(null);

  /* ── Data fetching ── */

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch("/api/agents/templates");
      if (res.ok) {
        const data = await res.json();
        setTemplates(data.templates || []);
      }
    } catch {
      console.error("Failed to fetch templates");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  /* ── Actions ── */

  const openCreate = () => {
    setEditingId(null);
    setConfig({ ...emptyConfig });
    setShowYaml(false);
    setEditorOpen(true);
  };

  const openEdit = async (template: AgentTemplate) => {
    try {
      const res = await fetch(`/api/agents/templates/${template.id}`);
      if (res.ok) {
        const data = await res.json();
        setEditingId(template.id);
        setConfig(data.config);
        setShowYaml(false);
        setEditorOpen(true);
      }
    } catch {
      toast.error(t("updateFailed"));
    }
  };

  const openPreview = async (template: AgentTemplate) => {
    try {
      const res = await fetch(`/api/agents/templates/${template.id}`);
      if (res.ok) {
        const data = await res.json();
        setPreviewId(template.id);
        setPreviewConfig(data.config);
      }
    } catch {
      console.error("Failed to fetch preview");
    }
  };

  const closePreview = () => {
    setPreviewId(null);
    setPreviewConfig(null);
  };

  const saveAgent = async () => {
    if (!config.name.trim()) {
      toast.error(t("nameRequired"));
      return;
    }

    setSaving(true);
    try {
      const url = editingId
        ? `/api/agents/templates/${editingId}`
        : "/api/agents/templates";
      const method = editingId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (res.ok) {
        toast.success(editingId ? t("agentUpdated") : t("agentCreated"));
        setEditorOpen(false);
        fetchTemplates();
      } else {
        const err = await res.json();
        toast.error(err.detail || (editingId ? t("updateFailed") : t("createFailed")));
      }
    } catch {
      toast.error(editingId ? t("updateFailed") : t("createFailed"));
    } finally {
      setSaving(false);
    }
  };

  const deleteAgent = async (template: AgentTemplate) => {
    if (!confirm(t("deleteConfirm", { name: template.name }))) return;

    try {
      const res = await fetch(`/api/agents/templates/${template.id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        toast.success(t("agentDeleted"));
        if (previewId === template.id) closePreview();
        fetchTemplates();
      } else {
        toast.error(t("deleteFailed"));
      }
    } catch {
      toast.error(t("deleteFailed"));
    }
  };

  const toggleTool = (tool: string) => {
    setConfig((prev) => ({
      ...prev,
      allowed_tools: prev.allowed_tools.includes(tool)
        ? prev.allowed_tools.filter((t) => t !== tool)
        : [...prev.allowed_tools, tool],
    }));
  };

  /* ── Derived ── */

  const builtinAgents = templates.filter((t) => t.source === "builtin");
  const userAgents = templates.filter((t) => t.source === "user");

  /* ── Render ── */

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link
            href="/"
            className="p-2 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-zinc-400" />
          </Link>
          <Bot className="w-5 h-5 text-blue-400" />
          <h1 className="text-lg font-medium">{t("title")}</h1>
          <span className="text-sm text-zinc-500">{t("subtitle")}</span>
          <div className="ml-auto">
            <button
              onClick={openCreate}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              {t("createAgent")}
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-6 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="p-5 bg-zinc-900/80 rounded-xl border border-zinc-800 animate-pulse"
              >
                <div className="h-5 w-2/3 bg-zinc-800 rounded mb-3" />
                <div className="h-3 w-full bg-zinc-800/60 rounded mb-2" />
                <div className="h-3 w-1/2 bg-zinc-800/40 rounded mb-4" />
                <div className="flex gap-2">
                  <div className="h-6 w-16 bg-zinc-800/40 rounded-full" />
                  <div className="h-6 w-16 bg-zinc-800/40 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        ) : templates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <Bot className="w-12 h-12 mb-4 text-zinc-700" />
            <p className="text-sm">{t("noAgents")}</p>
            <button
              onClick={openCreate}
              className="mt-4 flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              {t("createAgent")}
            </button>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Built-in Agents */}
            {builtinAgents.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="w-4 h-4 text-blue-400" />
                  <h2 className="text-sm font-medium text-zinc-400">
                    {t("builtin")}
                  </h2>
                  <div className="flex-1 h-px bg-zinc-800" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {builtinAgents.map((agent, i) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      index={i}
                      isBuiltin
                      isPreviewActive={previewId === agent.id}
                      onPreview={() =>
                        previewId === agent.id
                          ? closePreview()
                          : openPreview(agent)
                      }
                      t={t}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* User Agents */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-medium text-zinc-400">
                  {t("custom")}
                </h2>
                <div className="flex-1 h-px bg-zinc-800" />
              </div>
              {userAgents.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {userAgents.map((agent, i) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      index={i}
                      isBuiltin={false}
                      isPreviewActive={previewId === agent.id}
                      onEdit={() => openEdit(agent)}
                      onDelete={() => deleteAgent(agent)}
                      onPreview={() =>
                        previewId === agent.id
                          ? closePreview()
                          : openPreview(agent)
                      }
                      t={t}
                    />
                  ))}
                </div>
              ) : (
                <div
                  onClick={openCreate}
                  className="flex items-center justify-center p-8 rounded-xl border-2 border-dashed border-zinc-800 hover:border-zinc-700 transition-colors cursor-pointer group"
                >
                  <div className="flex flex-col items-center gap-2 text-zinc-600 group-hover:text-zinc-400 transition-colors">
                    <Plus className="w-8 h-8" />
                    <span className="text-sm">{t("createAgent")}</span>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {/* Config Preview Panel */}
        {previewConfig && (
          <div className="fixed bottom-0 right-0 w-full max-w-lg h-[60vh] bg-zinc-900 border-l border-t border-zinc-800 rounded-tl-2xl shadow-2xl shadow-black/50 z-40 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium">{t("configPreview")}</span>
              </div>
              <button
                onClick={closePreview}
                className="p-1.5 rounded-lg hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4 text-zinc-400" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-5">
              <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">
                {configToYaml(previewConfig)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* ── Editor Overlay ── */}
      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-3xl mx-4 my-8 rounded-2xl bg-zinc-900 border border-zinc-800 shadow-2xl overflow-hidden">
            {/* Editor header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-blue-400" />
                </div>
                <h2 className="text-lg font-medium">
                  {editingId ? t("editAgent") : t("createAgent")}
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowYaml(!showYaml)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-colors cursor-pointer ${
                    showYaml
                      ? "bg-blue-500/10 border-blue-500/30 text-blue-400"
                      : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-300"
                  }`}
                >
                  <Code2 className="w-3.5 h-3.5" />
                  YAML
                </button>
                <button
                  onClick={() => setEditorOpen(false)}
                  className="p-2 rounded-lg hover:bg-zinc-800 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4 text-zinc-400" />
                </button>
              </div>
            </div>

            {/* Editor body */}
            <div className="p-6 space-y-5">
              {showYaml ? (
                /* YAML Preview */
                <div className="rounded-xl bg-zinc-950 border border-zinc-800 p-5 overflow-auto max-h-[60vh]">
                  <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">
                    {configToYaml(config)}
                  </pre>
                </div>
              ) : (
                /* Form */
                <>
                  {/* Name & Model row */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1.5">
                        {t("name")}
                      </label>
                      <input
                        type="text"
                        value={config.name}
                        onChange={(e) =>
                          setConfig({ ...config, name: e.target.value })
                        }
                        placeholder={t("namePlaceholder")}
                        className="w-full px-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm transition"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1.5">
                        {t("model")}
                      </label>
                      <ModelSelector
                        value={config.model}
                        onChange={(modelId) =>
                          setConfig({ ...config, model: modelId })
                        }
                      />
                    </div>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1.5">
                      {t("description")}
                    </label>
                    <input
                      type="text"
                      value={config.description}
                      onChange={(e) =>
                        setConfig({ ...config, description: e.target.value })
                      }
                      placeholder={t("descriptionPlaceholder")}
                      className="w-full px-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm transition"
                    />
                  </div>

                  {/* System Prompt */}
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1.5">
                      {t("systemPrompt")}
                    </label>
                    <textarea
                      value={config.system_prompt}
                      onChange={(e) =>
                        setConfig({ ...config, system_prompt: e.target.value })
                      }
                      rows={10}
                      placeholder={t("systemPromptPlaceholder")}
                      className="w-full px-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 text-sm font-mono leading-relaxed transition resize-y"
                    />
                  </div>

                  {/* Allowed Tools */}
                  <div>
                    <label className="block text-sm text-zinc-400 mb-2">
                      {t("tools")}
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {ALL_TOOLS.map((tool) => (
                        <button
                          key={tool}
                          type="button"
                          onClick={() => toggleTool(tool)}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                            config.allowed_tools.includes(tool)
                              ? "bg-blue-500/10 border-blue-500/30 text-blue-400"
                              : "bg-zinc-800/60 border-zinc-700/50 text-zinc-500 hover:border-zinc-600 hover:text-zinc-400"
                          }`}
                        >
                          <Wrench className="w-3 h-3" />
                          {tool}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Editor footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-800">
              <button
                onClick={() => setEditorOpen(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-300 transition cursor-pointer"
              >
                {t("cancel")}
              </button>
              <button
                onClick={saveAgent}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition cursor-pointer"
              >
                {saving ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {editingId ? t("save") : t("create")}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

/* ── Agent Card Sub-Component ── */

function AgentCard({
  agent,
  index,
  isBuiltin,
  isPreviewActive,
  onEdit,
  onDelete,
  onPreview,
  t,
}: {
  agent: AgentTemplate;
  index: number;
  isBuiltin: boolean;
  isPreviewActive: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onPreview: () => void;
  t: (key: string) => string;
}) {
  return (
    <div
      style={{ animation: `fadeInUp 0.3s ease-out ${index * 60}ms both` }}
      className={`group relative flex flex-col p-5 rounded-xl border transition-all duration-200 ${
        isPreviewActive
          ? "bg-zinc-800/80 border-blue-500/30 shadow-lg shadow-blue-500/5"
          : "bg-zinc-900/80 border-zinc-800 hover:border-zinc-700 hover:shadow-lg hover:shadow-black/20"
      }`}
    >
      {/* Top row: icon + name + badges */}
      <div className="flex items-start gap-3 mb-2">
        <div
          className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
            isBuiltin
              ? "bg-blue-500/10 border border-blue-500/20"
              : "bg-emerald-500/10 border border-emerald-500/20"
          }`}
        >
          <Bot
            className={`w-4 h-4 ${
              isBuiltin ? "text-blue-400" : "text-emerald-400"
            }`}
          />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-sm truncate">{agent.name}</h3>
          <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">
            {agent.description}
          </p>
        </div>
      </div>

      {/* Tags */}
      <div className="flex items-center gap-2 mt-auto pt-3">
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
            isBuiltin
              ? "bg-blue-500/10 text-blue-400"
              : "bg-emerald-500/10 text-emerald-400"
          }`}
        >
          {isBuiltin ? t("builtin") : t("custom")}
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500">
          {agent.id}
        </span>
      </div>

      {/* Hover actions */}
      <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onPreview();
          }}
          className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
            isPreviewActive
              ? "bg-blue-500/20 text-blue-400"
              : "hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300"
          }`}
          title={t("viewConfig")}
        >
          <Eye className="w-3.5 h-3.5" />
        </button>
        {!isBuiltin && onEdit && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1.5 rounded-lg hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
            title={t("editConfig")}
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
        )}
        {!isBuiltin && onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 rounded-lg hover:bg-red-900/50 text-zinc-500 hover:text-red-400 transition-colors cursor-pointer"
            title={t("deleteAgent")}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
