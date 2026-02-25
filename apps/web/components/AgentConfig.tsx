"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bot,
  Save,
  RefreshCw,
  ChevronDown,
  Check,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { SkillManager } from "./SkillManager";
import ModelSelector from "@/components/ModelSelector";

interface AgentTemplate {
  id: string;
  name: string;
  description: string;
}

interface AgentConfigData {
  name: string;
  description: string;
  system_prompt: string;
  skills: string[];
  model: string;
  allowed_tools: string[];
}

interface AgentConfigProps {
  projectId: string;
  onConfigChange?: (config: AgentConfigData) => void;
  className?: string;
}

export function AgentConfig({ projectId, onConfigChange, className }: AgentConfigProps) {
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [config, setConfig] = useState<AgentConfigData>({
    name: "",
    description: "",
    system_prompt: "",
    skills: [],
    model: "claude-sonnet-4-5-20250929",
    allowed_tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
  });
  const [configSource, setConfigSource] = useState<string>("default");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showTemplateDropdown, setShowTemplateDropdown] = useState(false);

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch("/api/agents/templates");
      if (res.ok) {
        const data = await res.json();
        setTemplates(data.templates || []);
      }
    } catch (err) {
      console.error("Failed to fetch templates:", err);
    }
  }, []);

  // Fetch current config
  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/agents/projects/${projectId}/config`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data.config);
        setConfigSource(data.source);
      }
    } catch (err) {
      console.error("Failed to fetch config:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchTemplates();
    fetchConfig();
  }, [fetchTemplates, fetchConfig]);

  // Apply template
  const applyTemplate = async (templateId: string) => {
    try {
      const res = await fetch(`/api/agents/templates/${templateId}`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data.config);
        setSelectedTemplate(templateId);
        setShowTemplateDropdown(false);
        toast.success(`已应用模板: ${data.config.name}`);
      }
    } catch (err) {
      toast.error("应用模板失败");
    }
  };

  // Save config
  const saveConfig = async () => {
    try {
      setSaving(true);
      const res = await fetch(`/api/agents/projects/${projectId}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (res.ok) {
        toast.success("配置已保存");
        setConfigSource(`project:${projectId}`);
        onConfigChange?.(config);
      } else {
        throw new Error("Save failed");
      }
    } catch (err) {
      toast.error("保存配置失败");
    } finally {
      setSaving(false);
    }
  };

  // Toggle skill
  const toggleSkill = (skillId: string) => {
    setConfig((prev) => ({
      ...prev,
      skills: prev.skills.includes(skillId)
        ? prev.skills.filter((s) => s !== skillId)
        : [...prev.skills, skillId],
    }));
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <RefreshCw className="w-6 h-6 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-500" />
          <h3 className="font-medium">Agent 配置</h3>
        </div>
        <div className="text-xs text-zinc-500">
          来源: {configSource.startsWith("project:") ? "项目配置" : configSource.startsWith("template:") ? "模板" : "默认"}
        </div>
      </div>

      {/* Template selector */}
      <div className="relative">
        <label className="block text-sm text-zinc-400 mb-1">模板</label>
        <button
          onClick={() => setShowTemplateDropdown(!showTemplateDropdown)}
          className="w-full flex items-center justify-between px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg hover:border-zinc-600 transition"
        >
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-yellow-500" />
            {selectedTemplate
              ? templates.find((t) => t.id === selectedTemplate)?.name || "选择模板"
              : "选择模板应用..."}
          </span>
          <ChevronDown className="w-4 h-4" />
        </button>

        {showTemplateDropdown && (
          <div className="absolute z-10 w-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg overflow-hidden">
            {templates.map((template) => (
              <button
                key={template.id}
                onClick={() => applyTemplate(template.id)}
                className="w-full px-3 py-2 text-left hover:bg-zinc-800 transition flex items-center justify-between"
              >
                <div>
                  <div className="font-medium">{template.name}</div>
                  <div className="text-xs text-zinc-500">{template.description}</div>
                </div>
                {selectedTemplate === template.id && (
                  <Check className="w-4 h-4 text-green-500" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Name & Description */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm text-zinc-400 mb-1">名称</label>
          <input
            type="text"
            value={config.name}
            onChange={(e) => setConfig({ ...config, name: e.target.value })}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500"
            placeholder="Agent 名称"
          />
        </div>
        <div>
          <label className="block text-sm text-zinc-400 mb-1">模型</label>
          <ModelSelector
            value={config.model}
            onChange={(modelId, _providerId) => setConfig({ ...config, model: modelId })}
          />
        </div>
      </div>

      <div>
        <label className="block text-sm text-zinc-400 mb-1">描述</label>
        <input
          type="text"
          value={config.description}
          onChange={(e) => setConfig({ ...config, description: e.target.value })}
          className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500"
          placeholder="简短描述 Agent 的用途"
        />
      </div>

      {/* System Prompt */}
      <div>
        <label className="block text-sm text-zinc-400 mb-1">System Prompt</label>
        <textarea
          value={config.system_prompt}
          onChange={(e) => setConfig({ ...config, system_prompt: e.target.value })}
          rows={8}
          className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 font-mono text-sm resize-y"
          placeholder="定义 Agent 的角色、能力和行为..."
        />
      </div>

      {/* Skills */}
      <SkillManager
        projectId={projectId}
        selectedSkills={config.skills}
        onToggleSkill={toggleSkill}
      />

      {/* Save button */}
      <button
        onClick={saveConfig}
        disabled={saving}
        className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition"
      >
        {saving ? (
          <RefreshCw className="w-4 h-4 animate-spin" />
        ) : (
          <Save className="w-4 h-4" />
        )}
        保存配置
      </button>
    </div>
  );
}

export default AgentConfig;
