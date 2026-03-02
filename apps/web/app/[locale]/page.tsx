"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "@/i18n/routing";
import { Link } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import {
  Trash2,
  Bot,
  Sparkles,
  Search,
  ArrowUpDown,
  History,
  Activity,
  ArrowUp,
  Check,
  User,
  Settings,
} from "lucide-react";
import { toast } from "sonner";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

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

export default function Home() {
  const router = useRouter();
  const t = useTranslations('home');
  const tTime = useTranslations('time');
  const tActivity = useTranslations('activity');

  const relativeTime = (dateStr: string): string => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return tTime("justNow");
    if (mins < 60) return tTime("minutesAgo", { count: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24) return tTime("hoursAgo", { count: hours });
    const days = Math.floor(hours / 24);
    if (days < 30) return tTime("daysAgo", { count: days });
    const months = Math.floor(days / 30);
    if (months < 12) return tTime("monthsAgo", { count: months });
    return tTime("yearsAgo", { count: Math.floor(months / 12) });
  };

  const generateProjectName = (description: string): string => {
    const trimmed = description.trim().replace(/\n+/g, " ");
    const cut = trimmed.slice(0, 30);
    const atPunctuation = cut.search(/[，。！？,.!?\n]/);
    const name =
      atPunctuation > 4 ? cut.slice(0, atPunctuation) : cut.slice(0, 20);
    return name.trim() || t("newProject");
  };

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"created" | "name">("created");
  const [recentProject, setRecentProject] = useState<{
    project: Project;
    visitedAt: string;
  } | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  // Hero creation state
  const [description, setDescription] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("");
  const [creating, setCreating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
        if (found)
          setRecentProject({ project: found, visitedAt: recent.visitedAt });
      }
    } catch {}
  }, [projects]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [description]);

  const fetchProjects = async () => {
    try {
      const res = await fetch("/api/projects/");
      const data = await res.json();
      setProjects(data);
    } catch (error) {
      toast.error(t("loadFailed"));
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

  // Derived: is an agent selected? (mode 2)
  const selectedAgentInfo = templates.find((t) => t.id === selectedAgent);
  const isAgentMode = !!selectedAgentInfo;

  // Split templates into built-in and user-created
  const builtinTemplates = templates.filter((t) => t.source !== "user");
  const userAgents = templates.filter((t) => t.source === "user");

  const createProject = async () => {
    if (!description.trim() || creating) return;
    setCreating(true);

    try {
      const projectName = generateProjectName(description);

      // Mode 1: no agent selected → system-agent creates agent
      // Mode 2: agent selected → use "hello" cli + apply template
      const res = await fetch("/api/projects/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: projectName,
          preferred_cli: isAgentMode ? "hello" : "system-agent",
        }),
      });

      if (res.ok) {
        const project = await res.json();

        // Apply template if agent is selected
        if (isAgentMode) {
          await fetch(
            `/api/agents/projects/${project.id}/config/from-template?template_id=${selectedAgent}`,
            { method: "POST" }
          );
        }

        // Store the initial message for the chat page to pick up
        localStorage.setItem(
          `newhorse-initial-message-${project.id}`,
          description
        );

        setProjects([project, ...projects]);
        setDescription("");
        toast.success(t("projectCreated"));

        router.push(`/chat/${project.id}`);
      }
    } catch (error) {
      toast.error(t("createFailed"));
    } finally {
      setCreating(false);
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm(t("deleteConfirm"))) return;

    try {
      const res = await fetch(`/api/projects/${id}`, { method: "DELETE" });
      if (res.ok) {
        setProjects(projects.filter((p) => p.id !== id));
        toast.success(t("projectDeleted"));
      }
    } catch (error) {
      toast.error(t("deleteFailed"));
    }
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
      return (
        p.name.toLowerCase().includes(q) ||
        (p.description?.toLowerCase().includes(q) ?? false)
      );
    })
    .sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return (
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    });

  const canCreate = description.trim().length > 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canCreate) createProject();
    }
  };

  const toggleAgent = (id: string) => {
    setSelectedAgent(selectedAgent === id ? "" : id);
    textareaRef.current?.focus();
  };

  return (
    <main className="min-h-screen">
      {/* Top nav */}
      <div className="absolute top-0 right-0 p-4 z-10 flex items-center gap-1">
        <LanguageSwitcher />
        <Link href="/agents" className="p-2 rounded-lg hover:bg-zinc-800 transition-colors" title={t("agentsTitle")}>
          <Bot className="w-5 h-5 text-zinc-400" />
        </Link>
        <Link href="/settings" className="p-2 rounded-lg hover:bg-zinc-800 transition-colors" title={t("settingsTitle")}>
          <Settings className="w-5 h-5 text-zinc-400" />
        </Link>
      </div>

      {/* ── Hero: Create Project ── */}
      <section className="relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div
            className={`absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] rounded-full blur-[140px] transition-colors duration-500 ${
              isAgentMode
                ? "bg-emerald-500/[0.07]"
                : "bg-blue-500/[0.07]"
            }`}
          />
        </div>

        <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-14">
          {/* Logo + title */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2.5 mb-6">
              <div
                className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-colors duration-300 ${
                  isAgentMode
                    ? "bg-emerald-500/10 border-emerald-500/20"
                    : "bg-blue-500/10 border-blue-500/20"
                }`}
              >
                <Bot
                  className={`w-5 h-5 transition-colors duration-300 ${
                    isAgentMode ? "text-emerald-400" : "text-blue-400"
                  }`}
                />
              </div>
              <span className="text-lg font-semibold text-zinc-300">
                Newhorse
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3 transition-all duration-300">
              {isAgentMode
                ? t("heroTitleAgent", { name: selectedAgentInfo!.name })
                : t("heroTitle")}
            </h1>
            <p className="text-zinc-500 text-base transition-all duration-300">
              {isAgentMode
                ? t("heroSubtitleAgent")
                : t("heroSubtitle")}
            </p>
          </div>

          {/* ── Creation Card ── */}
          <div
            className={`border rounded-2xl p-5 backdrop-blur-sm shadow-xl shadow-black/20 transition-colors duration-300 ${
              isAgentMode
                ? "bg-zinc-900/80 border-emerald-500/20"
                : "bg-zinc-900/80 border-zinc-800"
            }`}
          >
            {/* Agent badge (mode 2) */}
            {isAgentMode && (
              <div className="flex items-center gap-2 mb-3 px-1">
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  <Bot className="w-3 h-3 text-emerald-400" />
                  <span className="text-xs font-medium text-emerald-400">
                    {selectedAgentInfo!.name}
                  </span>
                </div>
                <span className="text-[11px] text-zinc-600">
                  {selectedAgentInfo!.description}
                </span>
              </div>
            )}

            {/* Textarea + submit */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  isAgentMode
                    ? t("placeholderAgent", { name: selectedAgentInfo!.name })
                    : t("placeholder")
                }
                rows={3}
                className={`w-full px-4 py-3 pr-14 bg-zinc-800/60 border rounded-xl text-[15px] leading-relaxed focus:outline-none focus:ring-1 transition placeholder:text-zinc-600 resize-none ${
                  isAgentMode
                    ? "border-emerald-500/20 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                    : "border-zinc-700/60 focus:border-blue-500/50 focus:ring-blue-500/20"
                }`}
              />
              {/* Submit button */}
              <button
                onClick={createProject}
                disabled={!canCreate || creating}
                className={`absolute right-3 bottom-3 w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-200 cursor-pointer ${
                  canCreate
                    ? isAgentMode
                      ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20"
                      : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                    : "bg-zinc-700/50 text-zinc-600 cursor-not-allowed"
                }`}
              >
                {creating ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <ArrowUp className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Agent pills */}
            {templates.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap mt-3 px-1">
                {/* Built-in templates */}
                {builtinTemplates.length > 0 && (
                  <>
                    <span className="text-[11px] text-zinc-600">{t("templates")}</span>
                    {builtinTemplates.map((tpl) => (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => toggleAgent(tpl.id)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-150 cursor-pointer ${
                          selectedAgent === tpl.id
                            ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                            : "bg-zinc-800/40 border-zinc-700/30 text-zinc-500 hover:border-zinc-600 hover:text-zinc-400"
                        }`}
                        title={tpl.description}
                      >
                        <Bot className="w-3 h-3" />
                        {tpl.name}
                        {selectedAgent === tpl.id && (
                          <Check className="w-3 h-3" />
                        )}
                      </button>
                    ))}
                  </>
                )}

                {/* Divider between built-in and user agents */}
                {builtinTemplates.length > 0 && userAgents.length > 0 && (
                  <div className="w-px h-4 bg-zinc-700/50 mx-0.5" />
                )}

                {/* User-created agents */}
                {userAgents.length > 0 && (
                  <>
                    <span className="text-[11px] text-zinc-600">
                      {builtinTemplates.length > 0 ? t("mine") : t("myAgents")}
                    </span>
                    {userAgents.map((tpl) => (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => toggleAgent(tpl.id)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-150 cursor-pointer ${
                          selectedAgent === tpl.id
                            ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-400"
                            : "bg-zinc-800/40 border-zinc-700/30 text-zinc-500 hover:border-zinc-600 hover:text-zinc-400"
                        }`}
                        title={tpl.description}
                      >
                        <User className="w-3 h-3" />
                        {tpl.name}
                        {selectedAgent === tpl.id && (
                          <Check className="w-3 h-3" />
                        )}
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Keyboard hint */}
          <p className="text-center text-[11px] text-zinc-700 mt-3">
            {t("inputHint")}
          </p>
        </div>
      </section>

      {/* ── Content ── */}
      <div className="max-w-4xl mx-auto px-6 pb-10">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-4 bg-zinc-900/80 rounded-xl border border-zinc-800 animate-pulse"
              >
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
                  <span>{t("continueLastSession")}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium group-hover:text-blue-400 transition-colors">
                    {recentProject.project.name}
                  </span>
                  <span className="text-xs text-zinc-600">
                    {relativeTime(recentProject.visitedAt)}
                  </span>
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
                    placeholder={t("searchPlaceholder")}
                    className="w-full pl-9 pr-3 py-2 bg-zinc-900/80 rounded-lg border border-zinc-800 focus:outline-none focus:border-blue-500/50 text-sm transition"
                  />
                </div>
                <button
                  onClick={() =>
                    setSortBy(sortBy === "created" ? "name" : "created")
                  }
                  className="flex items-center gap-1.5 px-3 py-2 bg-zinc-900/80 rounded-lg border border-zinc-800 hover:border-zinc-700 text-sm text-zinc-400 hover:text-zinc-300 transition cursor-pointer shrink-0"
                >
                  <ArrowUpDown className="w-3.5 h-3.5" />
                  {sortBy === "created" ? t("sortRecent") : t("sortName")}
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
                    style={{
                      animation: `fadeInUp 0.3s ease-out ${index * 50}ms both`,
                    }}
                    className="group flex flex-col p-4 bg-zinc-900/80 rounded-xl border border-zinc-800 hover:border-blue-500/30 hover:shadow-lg hover:shadow-blue-500/5 transition-all duration-200 cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <Bot className="w-4 h-4 text-blue-500 shrink-0" />
                        <h3 className="font-medium truncate">{project.name}</h3>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteProject(project.id);
                        }}
                        className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-900/50 transition-all text-zinc-500 hover:text-red-400 shrink-0"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {project.description && (
                      <p className="text-sm text-zinc-500 line-clamp-2 pl-6">
                        {project.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-auto pt-3 pl-6">
                      <span className="text-xs px-2 py-0.5 bg-zinc-800 text-zinc-400 rounded-full">
                        {project.preferred_cli}
                      </span>
                      <span className="text-xs text-zinc-600">
                        {relativeTime(project.created_at)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-zinc-500 text-sm">
                {t("noMatch")}
              </div>
            )}

            {/* Recent Activity */}
            {activities.length > 0 && (
              <div className="mt-8">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-4 h-4 text-zinc-500" />
                  <h3 className="text-sm font-medium text-zinc-400">
                    {t("recentActivity")}
                  </h3>
                </div>
                <div className="space-y-1">
                  {activities.map((item, i) => (
                    <div
                      key={i}
                      onClick={() => router.push(`/chat/${item.project_id}`)}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-zinc-900/80 transition cursor-pointer group"
                    >
                      <div
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          item.role === "assistant"
                            ? "bg-blue-500"
                            : "bg-zinc-600"
                        }`}
                      />
                      <span className="text-sm text-zinc-300 font-medium shrink-0 group-hover:text-blue-400 transition-colors">
                        {item.project_name}
                      </span>
                      <span className="text-sm text-zinc-600 truncate">
                        {item.role === "user" ? tActivity("sentMessage") : tActivity("replied")}
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
