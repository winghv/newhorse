"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Puzzle,
  Plus,
  Trash2,
  Search,
  Upload,
  X,
  FileArchive,
  Globe,
  FolderOpen,
  Sparkles,
  Eye,
  Package,
  Layers,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

/* ── Types ── */

interface Skill {
  id: string;
  name: string;
  description: string;
  version: string;
  scope: "global" | "project";
  body?: string;
  files?: string[];
}

type ScopeFilter = "all" | "global" | "project";

/* ── Component ── */

export default function SkillsPage() {
  const t = useTranslations("skillMarket");

  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>("all");

  // Upload state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadScope, setUploadScope] = useState<"global" | "project">("global");
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Detail state
  const [detailSkill, setDetailSkill] = useState<Skill | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  /* ── Data fetching ── */

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch("/api/skills");
      if (res.ok) {
        const data = await res.json();
        setSkills(data.skills || []);
      }
    } catch {
      toast.error(t("loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  /* ── Actions ── */

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const params = new URLSearchParams({ scope: uploadScope, overwrite: "true" });
      const res = await fetch(`/api/skills/upload?${params}`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        toast.success(t("uploadSuccess"));
        setUploadOpen(false);
        setSelectedFile(null);
        fetchSkills();
      } else {
        const err = await res.json();
        toast.error(err.detail || t("uploadFailed"));
      }
    } catch {
      toast.error(t("uploadFailed"));
    } finally {
      setUploading(false);
    }
  };

  const deleteSkill = async (skill: Skill) => {
    if (!confirm(t("deleteConfirm", { name: skill.name }))) return;

    try {
      const params = new URLSearchParams({ scope: skill.scope });
      const res = await fetch(`/api/skills/${skill.id}?${params}`, {
        method: "DELETE",
      });
      if (res.ok) {
        toast.success(t("deleted"));
        if (detailSkill?.id === skill.id) setDetailSkill(null);
        fetchSkills();
      } else {
        toast.error(t("deleteFailed"));
      }
    } catch {
      toast.error(t("deleteFailed"));
    }
  };

  const openDetail = async (skill: Skill) => {
    setDetailLoading(true);
    setDetailSkill(skill);
    try {
      const params = new URLSearchParams({ scope: skill.scope });
      const res = await fetch(`/api/skills/${skill.id}?${params}`);
      if (res.ok) {
        const data = await res.json();
        setDetailSkill(data.skill);
      }
    } catch {
      // Use basic info
    } finally {
      setDetailLoading(false);
    }
  };

  /* ── Drag & Drop ── */

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.toLowerCase().endsWith(".zip")) {
      setSelectedFile(file);
    } else {
      toast.error(t("zipOnly"));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  /* ── Derived ── */

  const filteredSkills = skills
    .filter((s) => {
      if (scopeFilter !== "all" && s.scope !== scopeFilter) return false;
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  const globalCount = skills.filter((s) => s.scope === "global").length;
  const projectCount = skills.filter((s) => s.scope === "project").length;

  /* ── Render ── */

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* ── Hero Section ── */}
      <section className="relative overflow-hidden border-b border-zinc-800/50">
        {/* Background effects */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[400px] rounded-full blur-[160px] bg-violet-500/[0.06]" />
          <div className="absolute top-20 left-1/4 w-[300px] h-[300px] rounded-full blur-[120px] bg-blue-500/[0.04]" />
          <div className="absolute top-10 right-1/4 w-[250px] h-[250px] rounded-full blur-[100px] bg-fuchsia-500/[0.03]" />
        </div>

        {/* Header bar */}
        <div className="relative">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
            <Link
              href="/"
              className="p-2 rounded-lg hover:bg-zinc-800/80 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-zinc-400" />
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
                <Puzzle className="w-4 h-4 text-violet-400" />
              </div>
              <h1 className="text-lg font-medium">{t("title")}</h1>
            </div>
            <span className="text-sm text-zinc-500">{t("subtitle")}</span>
          </div>
        </div>

        {/* Hero content */}
        <div className="relative max-w-6xl mx-auto px-6 pb-8">
          <div className="flex items-end justify-between gap-4">
            {/* Stats */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-sm text-zinc-400">
                  {t("totalSkills", { count: skills.length })}
                </span>
              </div>
              {globalCount > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-zinc-500">
                  <Globe className="w-3.5 h-3.5" />
                  {globalCount} {t("globalLabel")}
                </div>
              )}
              {projectCount > 0 && (
                <div className="flex items-center gap-1.5 text-sm text-zinc-500">
                  <FolderOpen className="w-3.5 h-3.5" />
                  {projectCount} {t("projectLabel")}
                </div>
              )}
            </div>

            {/* Upload button */}
            <button
              onClick={() => {
                setSelectedFile(null);
                setUploadOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl bg-violet-600 hover:bg-violet-500 text-white transition-all duration-200 shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              {t("uploadSkill")}
            </button>
          </div>
        </div>
      </section>

      {/* ── Toolbar ── */}
      <div className="sticky top-0 z-20 bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-800/50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("searchPlaceholder")}
              className="w-full pl-9 pr-3 py-2 bg-zinc-900/60 rounded-lg border border-zinc-800 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 text-sm transition"
            />
          </div>

          {/* Scope filter tabs */}
          <div className="flex items-center bg-zinc-900/60 rounded-lg border border-zinc-800 p-0.5">
            {(["all", "global", "project"] as ScopeFilter[]).map((scope) => (
              <button
                key={scope}
                onClick={() => setScopeFilter(scope)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 cursor-pointer ${
                  scopeFilter === scope
                    ? "bg-violet-500/15 text-violet-400 shadow-sm"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {scope === "all"
                  ? t("filterAll")
                  : scope === "global"
                    ? t("filterGlobal")
                    : t("filterProject")}
              </button>
            ))}
          </div>

          {/* Refresh */}
          <button
            onClick={() => {
              setLoading(true);
              fetchSkills();
            }}
            className="p-2 rounded-lg hover:bg-zinc-800/80 text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
            title={t("refresh")}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ── Content ── */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        {loading ? (
          /* Loading skeleton */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="p-5 bg-zinc-900/60 rounded-2xl border border-zinc-800/60 animate-pulse"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-zinc-800 rounded-xl" />
                  <div className="flex-1">
                    <div className="h-4 w-2/3 bg-zinc-800 rounded mb-2" />
                    <div className="h-3 w-1/3 bg-zinc-800/60 rounded" />
                  </div>
                </div>
                <div className="h-3 w-full bg-zinc-800/40 rounded mb-2" />
                <div className="h-3 w-2/3 bg-zinc-800/30 rounded mb-4" />
                <div className="flex gap-2">
                  <div className="h-6 w-16 bg-zinc-800/30 rounded-full" />
                  <div className="h-6 w-12 bg-zinc-800/30 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredSkills.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-24">
            <div className="relative mb-6">
              <div className="w-20 h-20 rounded-2xl bg-violet-500/5 border border-violet-500/10 flex items-center justify-center">
                <Package className="w-10 h-10 text-violet-400/30" />
              </div>
              <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-zinc-900 border border-zinc-700 flex items-center justify-center">
                <Sparkles className="w-3 h-3 text-violet-400" />
              </div>
            </div>
            <h3 className="text-lg font-medium text-zinc-300 mb-2">
              {searchQuery ? t("noMatch") : t("emptyTitle")}
            </h3>
            <p className="text-sm text-zinc-500 mb-6 text-center max-w-sm">
              {searchQuery ? t("noMatchHint") : t("emptyHint")}
            </p>
            {!searchQuery && (
              <button
                onClick={() => {
                  setSelectedFile(null);
                  setUploadOpen(true);
                }}
                className="flex items-center gap-2 px-5 py-2.5 text-sm rounded-xl bg-violet-600 hover:bg-violet-500 text-white transition-all shadow-lg shadow-violet-500/20 cursor-pointer"
              >
                <Upload className="w-4 h-4" />
                {t("uploadFirst")}
              </button>
            )}
          </div>
        ) : (
          /* Skills grid */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill, i) => (
              <SkillCard
                key={`${skill.scope}-${skill.id}`}
                skill={skill}
                index={i}
                isActive={detailSkill?.id === skill.id && detailSkill?.scope === skill.scope}
                onView={() => openDetail(skill)}
                onDelete={() => deleteSkill(skill)}
                t={t}
              />
            ))}

            {/* Add new card */}
            <button
              onClick={() => {
                setSelectedFile(null);
                setUploadOpen(true);
              }}
              className="flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed border-zinc-800/60 hover:border-violet-500/30 hover:bg-violet-500/[0.02] transition-all duration-300 cursor-pointer group min-h-[180px]"
            >
              <div className="w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 group-hover:border-violet-500/30 group-hover:bg-violet-500/5 flex items-center justify-center transition-all duration-300 mb-3">
                <Plus className="w-5 h-5 text-zinc-600 group-hover:text-violet-400 transition-colors duration-300" />
              </div>
              <span className="text-sm text-zinc-600 group-hover:text-zinc-400 transition-colors">
                {t("uploadSkill")}
              </span>
            </button>
          </div>
        )}
      </div>

      {/* ── Detail Panel ── */}
      {detailSkill && (
        <div className="fixed bottom-0 right-0 w-full max-w-lg h-[65vh] bg-zinc-900/95 backdrop-blur-xl border-l border-t border-zinc-800 rounded-tl-2xl shadow-2xl shadow-black/60 z-40 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-medium">{t("skillDetail")}</span>
            </div>
            <button
              onClick={() => setDetailSkill(null)}
              className="p-1.5 rounded-lg hover:bg-zinc-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-5 space-y-4">
            {detailLoading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-5 h-5 text-violet-400 animate-spin" />
              </div>
            ) : (
              <>
                {/* Name & meta */}
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      detailSkill.scope === "global"
                        ? "bg-violet-500/10 border border-violet-500/20"
                        : "bg-sky-500/10 border border-sky-500/20"
                    }`}>
                      <Puzzle className={`w-5 h-5 ${
                        detailSkill.scope === "global" ? "text-violet-400" : "text-sky-400"
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-base">{detailSkill.name}</h3>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                          detailSkill.scope === "global"
                            ? "bg-violet-500/10 text-violet-400"
                            : "bg-sky-500/10 text-sky-400"
                        }`}>
                          {detailSkill.scope === "global" ? t("filterGlobal") : t("filterProject")}
                        </span>
                        {detailSkill.version && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500">
                            v{detailSkill.version}
                          </span>
                        )}
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500">
                          {detailSkill.id}
                        </span>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-zinc-400 mt-3 leading-relaxed">
                    {detailSkill.description}
                  </p>
                </div>

                {/* Files */}
                {detailSkill.files && detailSkill.files.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                      {t("filesLabel")}
                    </h4>
                    <div className="space-y-1">
                      {detailSkill.files.map((f) => (
                        <div
                          key={f}
                          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800/40 text-sm text-zinc-400 font-mono"
                        >
                          <FileArchive className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                          <span className="truncate">{f}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Body content */}
                {detailSkill.body && (
                  <div>
                    <h4 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">
                      {t("contentLabel")}
                    </h4>
                    <div className="rounded-xl bg-zinc-950 border border-zinc-800 p-4 overflow-auto max-h-[30vh]">
                      <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">
                        {detailSkill.body}
                      </pre>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Upload Modal ── */}
      {uploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div
            className="w-full max-w-xl mx-4 rounded-2xl bg-zinc-900 border border-zinc-800 shadow-2xl shadow-black/50 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
                  <Upload className="w-4 h-4 text-violet-400" />
                </div>
                <h2 className="text-lg font-medium">{t("uploadTitle")}</h2>
              </div>
              <button
                onClick={() => setUploadOpen(false)}
                className="p-2 rounded-lg hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4 text-zinc-400" />
              </button>
            </div>

            {/* Modal body */}
            <div className="p-6 space-y-5">
              {/* Scope selector */}
              <div>
                <label className="block text-sm text-zinc-400 mb-2">
                  {t("scopeLabel")}
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setUploadScope("global")}
                    className={`flex items-center gap-3 p-3 rounded-xl border transition-all duration-200 cursor-pointer ${
                      uploadScope === "global"
                        ? "bg-violet-500/10 border-violet-500/30 shadow-sm"
                        : "bg-zinc-800/40 border-zinc-700/50 hover:border-zinc-600"
                    }`}
                  >
                    <Globe className={`w-5 h-5 ${
                      uploadScope === "global" ? "text-violet-400" : "text-zinc-500"
                    }`} />
                    <div className="text-left">
                      <div className={`text-sm font-medium ${
                        uploadScope === "global" ? "text-violet-300" : "text-zinc-300"
                      }`}>
                        {t("filterGlobal")}
                      </div>
                      <div className="text-xs text-zinc-500">{t("globalHint")}</div>
                    </div>
                  </button>
                  <button
                    onClick={() => setUploadScope("project")}
                    className={`flex items-center gap-3 p-3 rounded-xl border transition-all duration-200 cursor-pointer ${
                      uploadScope === "project"
                        ? "bg-sky-500/10 border-sky-500/30 shadow-sm"
                        : "bg-zinc-800/40 border-zinc-700/50 hover:border-zinc-600"
                    }`}
                  >
                    <FolderOpen className={`w-5 h-5 ${
                      uploadScope === "project" ? "text-sky-400" : "text-zinc-500"
                    }`} />
                    <div className="text-left">
                      <div className={`text-sm font-medium ${
                        uploadScope === "project" ? "text-sky-300" : "text-zinc-300"
                      }`}>
                        {t("filterProject")}
                      </div>
                      <div className="text-xs text-zinc-500">{t("projectHint")}</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Drop zone */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center py-12 px-6 rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer ${
                  dragActive
                    ? "border-violet-500/60 bg-violet-500/5 scale-[1.01]"
                    : selectedFile
                      ? "border-emerald-500/40 bg-emerald-500/[0.03]"
                      : "border-zinc-700/50 hover:border-zinc-600 hover:bg-zinc-800/20"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  onChange={handleFileSelect}
                  className="hidden"
                />

                {selectedFile ? (
                  <>
                    <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-3">
                      <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                    </div>
                    <p className="text-sm font-medium text-emerald-300">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                      className="mt-3 text-xs text-zinc-500 hover:text-zinc-300 underline underline-offset-2 cursor-pointer"
                    >
                      {t("changeFile")}
                    </button>
                  </>
                ) : (
                  <>
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-3 transition-all duration-300 ${
                      dragActive
                        ? "bg-violet-500/15 border border-violet-500/30 scale-110"
                        : "bg-zinc-800/60 border border-zinc-700/50"
                    }`}>
                      <FileArchive className={`w-7 h-7 transition-colors ${
                        dragActive ? "text-violet-400" : "text-zinc-500"
                      }`} />
                    </div>
                    <p className="text-sm text-zinc-300 mb-1">
                      {t("dropzoneTitle")}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {t("dropzoneHint")}
                    </p>
                  </>
                )}
              </div>

              {/* Format hint */}
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-zinc-800/30 border border-zinc-800/50">
                <AlertCircle className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />
                <div className="text-xs text-zinc-500 leading-relaxed">
                  {t("formatHint")}
                </div>
              </div>
            </div>

            {/* Modal footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-800">
              <button
                onClick={() => setUploadOpen(false)}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-300 transition cursor-pointer"
              >
                {t("cancel")}
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                className="flex items-center gap-2 px-5 py-2 text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:hover:bg-violet-600 text-white rounded-xl transition cursor-pointer"
              >
                {uploading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                {t("uploadAction")}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </div>
  );
}

/* ── Skill Card Sub-Component ── */

function SkillCard({
  skill,
  index,
  isActive,
  onView,
  onDelete,
  t,
}: {
  skill: Skill;
  index: number;
  isActive: boolean;
  onView: () => void;
  onDelete: () => void;
  t: (key: string, values?: Record<string, string | number>) => string;
}) {
  const isGlobal = skill.scope === "global";

  return (
    <div
      onClick={onView}
      style={{ animation: `fadeInUp 0.35s ease-out ${index * 50}ms both` }}
      className={`group relative flex flex-col p-5 rounded-2xl border transition-all duration-200 cursor-pointer ${
        isActive
          ? "bg-zinc-800/60 border-violet-500/30 shadow-lg shadow-violet-500/5"
          : "bg-zinc-900/60 border-zinc-800/60 hover:border-zinc-700 hover:bg-zinc-900/80 hover:shadow-lg hover:shadow-black/20"
      }`}
    >
      {/* Icon + info */}
      <div className="flex items-start gap-3 mb-3">
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
            isGlobal
              ? "bg-violet-500/10 border border-violet-500/20"
              : "bg-sky-500/10 border border-sky-500/20"
          }`}
        >
          <Puzzle
            className={`w-5 h-5 ${
              isGlobal ? "text-violet-400" : "text-sky-400"
            }`}
          />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-sm truncate group-hover:text-white transition-colors">
            {skill.name}
          </h3>
          <p className="text-xs text-zinc-500 mt-1 line-clamp-2 leading-relaxed">
            {skill.description || t("noDescription")}
          </p>
        </div>
      </div>

      {/* Tags */}
      <div className="flex items-center gap-2 mt-auto pt-3">
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
            isGlobal
              ? "bg-violet-500/10 text-violet-400"
              : "bg-sky-500/10 text-sky-400"
          }`}
        >
          {isGlobal ? t("filterGlobal") : t("filterProject")}
        </span>
        {skill.version && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800/60 text-zinc-500">
            v{skill.version}
          </span>
        )}
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800/40 text-zinc-600 font-mono">
          {skill.id}
        </span>
      </div>

      {/* Hover actions */}
      <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onView();
          }}
          className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
            isActive
              ? "bg-violet-500/20 text-violet-400"
              : "hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300"
          }`}
          title={t("viewDetail")}
        >
          <Eye className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1.5 rounded-lg hover:bg-red-900/50 text-zinc-500 hover:text-red-400 transition-colors cursor-pointer"
          title={t("deleteSkill")}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
