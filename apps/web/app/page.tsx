"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2, Bot, Sparkles, ChevronDown, Check, Search, ArrowUpDown, History, Activity } from "lucide-react";
import { toast } from "sonner";

interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  preferred_cli: string;
  created_at: string;
}

interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  source?: string;
}

interface ActivityItem {
  project_id: string;
  project_name: string;
  role: string;
  content: string;
  message_type: string;
  created_at: string;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} 个月前`;
  return `${Math.floor(months / 12)} 年前`;
}

export default function Home() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [useAiGeneration, setUseAiGeneration] = useState(false);
  const [showTemplateDropdown, setShowTemplateDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"created" | "name">("created");
  const [recentProject, setRecentProject] = useState<{ project: Project; visitedAt: string } | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  useEffect(() => {
    fetchProjects();
    fetchTemplates();
    fetchActivity();
  }, []);

  useEffect(() => {
    if (projects.length === 0) return;
    try {
      const stored = localStorage.getItem("newhorse-recent-projects");
      if (stored) {
        const recent = JSON.parse(stored);
        const found = projects.find((p) => p.id === recent.id);
        if (found) setRecentProject({ project: found, visitedAt: recent.visitedAt });
      }
    } catch {}
  }, [projects]);

  const fetchProjects = async () => {
    try {
      const res = await fetch("/api/projects/");
      const data = await res.json();
      setProjects(data);
    } catch (error) {
      toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const res = await fetch("/api/agents/templates");
      if (res.ok) {
        const data = await res.json();
        const filtered = (data.templates || []).filter(
            (t: AgentTemplate) => t.id !== "system-agent"
        );
        setTemplates(filtered);
      }
    } catch (error) {
      console.error("Failed to load templates:", error);
    }
  };

  const fetchActivity = async () => {
    try {
      const res = await fetch("/api/activity/recent");
      if (res.ok) {
        const data = await res.json();
        setActivities(data.activities || []);
      }
    } catch {}
  };

  const createProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      // Create project
      const res = await fetch("/api/projects/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newProjectName,
          preferred_cli: useAiGeneration ? "system-agent" : "hello",
        }),
      });

      if (res.ok) {
        const project = await res.json();

        // Apply template if selected
        if (selectedTemplate && !useAiGeneration) {
          await fetch(`/api/agents/projects/${project.id}/config/from-template?template_id=${selectedTemplate}`, {
            method: "POST",
          });
        }

        setProjects([project, ...projects]);
        setNewProjectName("");
        setSelectedTemplate("");
        setUseAiGeneration(false);
        setShowNewProject(false);
        toast.success("Project created");

        // If AI generation selected, redirect to chat with system-agent
        if (useAiGeneration) {
          router.push(`/chat/${project.id}`);
        }
      }
    } catch (error) {
      toast.error("Failed to create project");
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm("Delete this project?")) return;

    try {
      const res = await fetch(`/api/projects/${id}`, { method: "DELETE" });
      if (res.ok) {
        setProjects(projects.filter((p) => p.id !== id));
        toast.success("Project deleted");
      }
    } catch (error) {
      toast.error("Failed to delete project");
    }
  };

  const selectTemplate = (templateId: string) => {
    setSelectedTemplate(templateId);
    setUseAiGeneration(false);
    setShowTemplateDropdown(false);
  };

  const selectAiGeneration = () => {
    setUseAiGeneration(true);
    setSelectedTemplate("");
    setShowTemplateDropdown(false);
  };

  const navigateToChat = (project: Project) => {
    try {
      localStorage.setItem(
        "newhorse-recent-projects",
        JSON.stringify({ id: project.id, visitedAt: new Date().toISOString() })
      );
    } catch {}
    router.push(`/chat/${project.id}`);
  };

  const filteredProjects = projects
    .filter((p) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(q) || (p.description?.toLowerCase().includes(q) ?? false);
    })
    .sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  return (
    <main className="min-h-screen px-6 py-10">
      {/* Header */}
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8 text-blue-500" />
            <h1 className="text-2xl font-bold">Newhorse</h1>
          </div>
          <button
            onClick={() => setShowNewProject(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            New Project
          </button>
        </div>

        {/* New Project Form */}
        {showNewProject && (
          <div className="mb-6 p-4 bg-zinc-900 rounded-lg border border-zinc-800">
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project name..."
              className="w-full px-3 py-2 bg-zinc-800 rounded-lg border border-zinc-700 focus:outline-none focus:border-blue-500 mb-3"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && createProject()}
            />

            {/* Agent Template Selection */}
            <div className="mb-3">
              <label className="block text-sm text-zinc-400 mb-2">Agent 模板</label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowTemplateDropdown(!showTemplateDropdown)}
                  className="w-full flex items-center justify-between px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg hover:border-zinc-600 transition text-left"
                >
                  <span className="flex items-center gap-2">
                    {useAiGeneration ? (
                      <>
                        <Sparkles className="w-4 h-4 text-yellow-500" />
                        让 AI 帮我创建 Agent
                      </>
                    ) : selectedTemplate ? (
                      <>
                        <Bot className="w-4 h-4 text-blue-500" />
                        {templates.find((t) => t.id === selectedTemplate)?.name || selectedTemplate}
                      </>
                    ) : (
                      <span className="text-zinc-500">选择模板（可选）</span>
                    )}
                  </span>
                  <ChevronDown className="w-4 h-4" />
                </button>

                {showTemplateDropdown && (
                  <>
                  <div className="fixed inset-0 z-[9]" onClick={() => setShowTemplateDropdown(false)} />
                  <div className="absolute z-10 w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-xl shadow-lg p-2">
                    {/* AI Generation - full width top */}
                    <button
                      type="button"
                      onClick={selectAiGeneration}
                      className={`w-full p-3 text-left rounded-lg transition flex items-center gap-3 mb-2 cursor-pointer ${
                        useAiGeneration
                          ? "bg-yellow-500/10 border border-yellow-500/30"
                          : "hover:bg-zinc-700 border border-transparent"
                      }`}
                    >
                      <div className="w-8 h-8 rounded-lg bg-yellow-500/10 flex items-center justify-center shrink-0">
                        <Sparkles className="w-4 h-4 text-yellow-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium">让 AI 帮我创建 Agent</div>
                        <div className="text-xs text-zinc-500">描述你的需求，AI 自动生成配置</div>
                      </div>
                      {useAiGeneration && <Check className="w-4 h-4 text-green-500 shrink-0" />}
                    </button>

                    {/* Template grid - 2 columns */}
                    {templates.length > 0 && (
                      <div className="grid grid-cols-2 gap-1.5">
                        {templates.map((template) => (
                          <button
                            key={template.id}
                            type="button"
                            onClick={() => selectTemplate(template.id)}
                            className={`p-2.5 text-left rounded-lg transition flex items-center gap-2.5 cursor-pointer ${
                              selectedTemplate === template.id
                                ? "bg-blue-500/10 border border-blue-500/30"
                                : "hover:bg-zinc-700 border border-transparent"
                            }`}
                          >
                            <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                              <Bot className="w-3.5 h-3.5 text-blue-500" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-medium truncate flex items-center gap-1">
                                {template.name}
                                {template.source === "user" && (
                                  <span className="text-[10px] px-1 py-0.5 bg-blue-900/50 text-blue-400 rounded">
                                    自定义
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-zinc-500 truncate">{template.description}</div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* No template */}
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedTemplate("");
                        setUseAiGeneration(false);
                        setShowTemplateDropdown(false);
                      }}
                      className="w-full mt-2 pt-2 border-t border-zinc-700 text-center text-xs text-zinc-500 hover:text-zinc-300 transition cursor-pointer py-1.5"
                    >
                      不使用模板
                    </button>
                  </div>
                  </>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={createProject}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
              >
                {useAiGeneration && <Sparkles className="w-4 h-4" />}
                Create
              </button>
              <button
                onClick={() => {
                  setShowNewProject(false);
                  setNewProjectName("");
                  setSelectedTemplate("");
                  setUseAiGeneration(false);
                }}
                className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Projects */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="p-4 bg-zinc-900/80 rounded-xl border border-zinc-800 animate-pulse">
                <div className="h-4 w-2/3 bg-zinc-800 rounded mb-3" />
                <div className="h-3 w-full bg-zinc-800/60 rounded mb-2" />
                <div className="h-3 w-1/3 bg-zinc-800/40 rounded mt-4" />
              </div>
            ))}
          </div>
        ) : projects.length > 0 ? (
          <>
            {/* Quick Continue */}
            {recentProject && (
              <div
                onClick={() => navigateToChat(recentProject.project)}
                className="mb-4 flex items-center justify-between p-3 bg-zinc-900/80 rounded-xl border border-zinc-800 hover:border-blue-500/30 transition-all duration-200 cursor-pointer group"
              >
                <div className="flex items-center gap-2 text-sm text-zinc-400">
                  <History className="w-4 h-4" />
                  <span>继续上次</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium group-hover:text-blue-400 transition-colors">{recentProject.project.name}</span>
                  <span className="text-xs text-zinc-600">{relativeTime(recentProject.visitedAt)}</span>
                </div>
              </div>
            )}

            {/* Search & Sort */}
            {projects.length >= 5 && (
              <div className="mb-4 flex items-center gap-3">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索项目..."
                    className="w-full pl-9 pr-3 py-2 bg-zinc-900/80 rounded-lg border border-zinc-800 focus:outline-none focus:border-blue-500/50 text-sm transition"
                  />
                </div>
                <button
                  onClick={() => setSortBy(sortBy === "created" ? "name" : "created")}
                  className="flex items-center gap-1.5 px-3 py-2 bg-zinc-900/80 rounded-lg border border-zinc-800 hover:border-zinc-700 text-sm text-zinc-400 hover:text-zinc-300 transition cursor-pointer shrink-0"
                >
                  <ArrowUpDown className="w-3.5 h-3.5" />
                  {sortBy === "created" ? "最近创建" : "名称排序"}
                </button>
              </div>
            )}

            {/* Project Grid */}
            {filteredProjects.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {filteredProjects.map((project, index) => (
                  <div
                    key={project.id}
                    onClick={() => navigateToChat(project)}
                    style={{ animation: `fadeInUp 0.3s ease-out ${index * 50}ms both` }}
                    className="group flex flex-col p-4 bg-zinc-900/80 rounded-xl border border-zinc-800 hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-500/5 transition-all duration-200 cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <Bot className="w-4 h-4 text-blue-500 shrink-0" />
                        <h3 className="font-medium truncate">{project.name}</h3>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteProject(project.id); }}
                        className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-900/50 transition-all text-zinc-500 hover:text-red-400 shrink-0"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {project.description && (
                      <p className="text-sm text-zinc-500 line-clamp-2 pl-6">{project.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-auto pt-3 pl-6">
                      <span className="text-xs px-2 py-0.5 bg-zinc-800 text-zinc-400 rounded-full">
                        {project.preferred_cli}
                      </span>
                      <span className="text-xs text-zinc-600">{relativeTime(project.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-zinc-500 text-sm">没有匹配的项目</div>
            )}

            {/* Recent Activity */}
            {activities.length > 0 && (
              <div className="mt-8">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-4 h-4 text-zinc-500" />
                  <h3 className="text-sm font-medium text-zinc-400">最近活动</h3>
                </div>
                <div className="space-y-1">
                  {activities.map((item, i) => (
                    <div
                      key={i}
                      onClick={() => router.push(`/chat/${item.project_id}`)}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-zinc-900/80 transition cursor-pointer group"
                    >
                      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${item.role === "assistant" ? "bg-blue-500" : "bg-zinc-600"}`} />
                      <span className="text-sm text-zinc-300 font-medium shrink-0 group-hover:text-blue-400 transition-colors">
                        {item.project_name}
                      </span>
                      <span className="text-sm text-zinc-600 truncate">
                        {item.role === "user" ? "发送了消息" : "回复了消息"}
                        {item.content ? ` — ${item.content}` : ""}
                      </span>
                      <span className="text-xs text-zinc-700 shrink-0 ml-auto">
                        {relativeTime(item.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : !showNewProject ? (
          <div className="py-16 flex flex-col items-center">
            <div className="w-14 h-14 rounded-2xl bg-zinc-800 border border-zinc-700 flex items-center justify-center mb-6">
              <Bot className="w-7 h-7 text-blue-500" />
            </div>
            <h2 className="text-xl font-semibold mb-2">开始构建你的 AI Agent</h2>
            <p className="text-sm text-zinc-500 mb-10">选择一种方式快速开始</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-lg">
              <button
                onClick={() => { setShowNewProject(true); setUseAiGeneration(true); }}
                className="flex flex-col items-center gap-3 p-5 bg-zinc-900/80 rounded-xl border border-zinc-800 hover:border-yellow-500/30 hover:bg-zinc-800/50 transition-all duration-200 cursor-pointer group"
              >
                <div className="w-10 h-10 rounded-xl bg-yellow-500/10 flex items-center justify-center group-hover:bg-yellow-500/20 transition-colors">
                  <Sparkles className="w-5 h-5 text-yellow-500" />
                </div>
                <div className="text-center">
                  <div className="text-sm font-medium mb-1">AI 生成</div>
                  <div className="text-xs text-zinc-500">描述需求，自动创建</div>
                </div>
              </button>
              <button
                onClick={() => { setShowNewProject(true); setShowTemplateDropdown(true); }}
                className="flex flex-col items-center gap-3 p-5 bg-zinc-900/80 rounded-xl border border-zinc-800 hover:border-blue-500/30 hover:bg-zinc-800/50 transition-all duration-200 cursor-pointer group"
              >
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                  <Bot className="w-5 h-5 text-blue-500" />
                </div>
                <div className="text-center">
                  <div className="text-sm font-medium mb-1">选择模板</div>
                  <div className="text-xs text-zinc-500">从预置模板快速开始</div>
                </div>
              </button>
              <button
                onClick={() => setShowNewProject(true)}
                className="flex flex-col items-center gap-3 p-5 bg-zinc-900/80 rounded-xl border border-zinc-800 hover:border-zinc-600 hover:bg-zinc-800/50 transition-all duration-200 cursor-pointer group"
              >
                <div className="w-10 h-10 rounded-xl bg-zinc-700/50 flex items-center justify-center group-hover:bg-zinc-700 transition-colors">
                  <Plus className="w-5 h-5 text-zinc-400" />
                </div>
                <div className="text-center">
                  <div className="text-sm font-medium mb-1">空白项目</div>
                  <div className="text-xs text-zinc-500">从零开始自定义</div>
                </div>
              </button>
            </div>
          </div>
        ) : null}
      </div>
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </main>
  );
}
