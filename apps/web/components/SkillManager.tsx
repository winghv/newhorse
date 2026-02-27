"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Upload, Trash2, Check, RefreshCw, Globe, FolderOpen } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

interface Skill {
  id: string;
  name: string;
  description: string;
  version: string;
  scope: "global" | "project";
}

interface SkillManagerProps {
  projectId: string;
  selectedSkills: string[];
  onToggleSkill: (skillId: string) => void;
}

export function SkillManager({ projectId, selectedSkills, onToggleSkill }: SkillManagerProps) {
  const t = useTranslations('skills');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadScope, setUploadScope] = useState<"project" | "global">("project");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch(`/api/skills?project_id=${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setSkills(data.skills || []);
      }
    } catch (err) {
      console.error("Failed to fetch skills:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(
        `/api/skills/upload?scope=${uploadScope}&project_id=${projectId}`,
        { method: "POST", body: form }
      );

      if (res.ok) {
        toast.success(t('uploadSuccess'));
        await fetchSkills();
      } else {
        const err = await res.json().catch(() => ({ detail: t('uploadFailed') }));
        toast.error(err.detail || t('uploadFailed'));
      }
    } catch {
      toast.error(t('uploadFailed'));
    } finally {
      setUploading(false);
      // Reset so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (skill: Skill) => {
    if (!confirm(t('deleteConfirm', { name: skill.name }))) return;
    try {
      const res = await fetch(
        `/api/skills/${skill.id}?scope=project&project_id=${projectId}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        toast.success(t('deleted'));
        await fetchSkills();
      } else {
        const err = await res.json().catch(() => ({ detail: t('deleteFailed') }));
        toast.error(err.detail || t('deleteFailed'));
      }
    } catch {
      toast.error(t('deleteFailed'));
    }
  };

  const globalSkills = skills.filter((s) => s.scope === "global");
  const projectSkills = skills.filter((s) => s.scope === "project");

  return (
    <div>
      <label className="block text-sm text-zinc-400 mb-2">{t('label')}</label>

      {loading ? (
        <div className="flex items-center gap-2 text-zinc-500 text-sm py-2">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          {t('loading')}
        </div>
      ) : (
        <>
          {/* Global skills */}
          {globalSkills.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-1.5">
                <Globe className="w-3 h-3" />
                {t('global')}
              </div>
              <div className="flex flex-wrap gap-2">
                {globalSkills.map((skill) => (
                  <button
                    key={`global-${skill.id}`}
                    onClick={() => onToggleSkill(skill.id)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition flex items-center gap-1.5 ${
                      selectedSkills.includes(skill.id)
                        ? "bg-blue-600 text-white"
                        : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                    title={skill.description}
                  >
                    {selectedSkills.includes(skill.id) && <Check className="w-3 h-3" />}
                    {skill.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Project skills */}
          {projectSkills.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-1.5">
                <FolderOpen className="w-3 h-3" />
                {t('project')}
              </div>
              <div className="flex flex-wrap gap-2">
                {projectSkills.map((skill) => (
                  <div key={`project-${skill.id}`} className="flex items-center gap-1">
                    <button
                      onClick={() => onToggleSkill(skill.id)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition flex items-center gap-1.5 ${
                        selectedSkills.includes(skill.id)
                          ? "bg-blue-600 text-white"
                          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                      }`}
                      title={skill.description}
                    >
                      {selectedSkills.includes(skill.id) && <Check className="w-3 h-3" />}
                      {skill.name}
                    </button>
                    <button
                      onClick={() => handleDelete(skill)}
                      className="p-1 text-zinc-600 hover:text-red-400 transition"
                      title={t('deleteTitle')}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {skills.length === 0 && (
            <p className="text-sm text-zinc-600 mb-3">{t('empty')}</p>
          )}
        </>
      )}

      {/* Upload area */}
      <div className="flex items-center gap-3 mt-1">
        <input
          ref={fileInputRef}
          type="file"
          accept=".zip"
          className="hidden"
          onChange={handleUpload}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition disabled:opacity-50"
        >
          {uploading ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Upload className="w-3.5 h-3.5" />
          )}
          {t('uploadButton')}
        </button>

        {/* Scope toggle */}
        <div className="flex items-center gap-1 text-xs">
          <button
            onClick={() => setUploadScope("project")}
            className={`px-2 py-1 rounded transition ${
              uploadScope === "project"
                ? "bg-zinc-700 text-zinc-200"
                : "text-zinc-500 hover:text-zinc-400"
            }`}
          >
            {t('projectScope')}
          </button>
          <button
            onClick={() => setUploadScope("global")}
            className={`px-2 py-1 rounded transition ${
              uploadScope === "global"
                ? "bg-zinc-700 text-zinc-200"
                : "text-zinc-500 hover:text-zinc-400"
            }`}
          >
            {t('globalScope')}
          </button>
        </div>
      </div>
    </div>
  );
}

export default SkillManager;
