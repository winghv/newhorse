"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  RefreshCw,
  ExternalLink,
  Maximize2,
  Minimize2,
  X,
  Eye,
  Code,
  FileCode,
  Save,
  Circle,
} from "lucide-react";
import { MonacoEditor, getLanguageFromFilename } from "./MonacoEditor";
import { toast } from "sonner";
import { useTranslations } from "next-intl";

interface PreviewPanelProps {
  projectId: string;
  filePath: string;
  onClose: () => void;
  isDragging?: boolean;
  defaultMode?: "preview" | "edit";
}

const PREVIEWABLE_EXTENSIONS = [".html", ".htm", ".svg"];

export function isPreviewable(filename: string): boolean {
  const ext = filename.toLowerCase().slice(filename.lastIndexOf("."));
  return PREVIEWABLE_EXTENSIONS.includes(ext);
}

export function PreviewPanel({ projectId, filePath, onClose, isDragging, defaultMode }: PreviewPanelProps) {
  const t = useTranslations('preview');
  const [tabMode, setTabMode] = useState<"preview" | "edit">(defaultMode || "preview");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [code, setCode] = useState<string>("");
  const [originalCode, setOriginalCode] = useState<string>("");
  const [codeLoading, setCodeLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [iframeLoading, setIframeLoading] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const filename = filePath.split("/").pop() || filePath;
  const previewUrl = `/api/preview/${projectId}/${filePath}`;
  const isFilePreviewable = isPreviewable(filename);
  const language = getLanguageFromFilename(filename);
  const isDirty = code !== originalCode;

  // 决定默认模式
  useEffect(() => {
    if (defaultMode) {
      setTabMode(defaultMode);
    } else if (!isFilePreviewable) {
      // 非可视化文件默认进入编辑模式
      setTabMode("edit");
    }
  }, [filePath]);

  // 文件切换时清空内容，重新加载
  useEffect(() => {
    setCode("");
    setOriginalCode("");
  }, [filePath]);

  // 加载文件内容
  const loadFileContent = useCallback(async () => {
    if (code) return; // 当前文件已加载过
    setCodeLoading(true);
    try {
      const res = await fetch(`/api/projects/${projectId}/files/${filePath}`);
      const data = await res.json();
      const content = data.content || "";
      setCode(content);
      setOriginalCode(content);
    } catch (err) {
      console.error("Failed to load code:", err);
      toast.error(t('loadFailed'));
    } finally {
      setCodeLoading(false);
    }
  }, [projectId, filePath, code]);

  // 加载内容后，切换 tab 时确保加载
  useEffect(() => {
    if (tabMode === "edit" && !code) {
      loadFileContent();
    }
  }, [tabMode, code, loadFileContent]);

  // 保存文件
  const handleSave = useCallback(async () => {
    if (!isDirty) return;
    setSaveLoading(true);
    try {
      const res = await fetch(`/api/projects/${projectId}/files/${filePath}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: code }),
      });
      if (!res.ok) throw new Error("Save failed");
      setOriginalCode(code);
      toast.success(t('fileSaved'));
    } catch (err) {
      console.error("Failed to save:", err);
      toast.error(t('saveFailed'));
    } finally {
      setSaveLoading(false);
    }
  }, [projectId, filePath, code, isDirty]);

  // Tab 切换
  const handleTabChange = (newTab: "preview" | "edit") => {
    if (newTab === "edit" && !code) {
      loadFileContent();
    }
    setTabMode(newTab);
  };

  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
    setIframeLoading(true);
  };

  const handleOpenExternal = () => {
    window.open(previewUrl, "_blank");
  };

  const handleToggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleEditorChange = (newValue: string) => {
    setCode(newValue);
  };

  const containerClass = isFullscreen
    ? "fixed inset-0 z-50 flex flex-col bg-zinc-900"
    : "flex flex-col h-full";

  return (
    <div className={containerClass}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm">
        {/* Left: file info */}
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <span className="text-sm text-zinc-300 truncate">{filename}</span>
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-0.5">
          {/* Tab toggle */}
          <div className="flex bg-zinc-800 rounded-md p-0.5 mr-1">
            <button
              onClick={() => handleTabChange("preview")}
              disabled={!isFilePreviewable}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
                tabMode === "preview"
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-500 hover:text-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed"
              }`}
              title={t('preview')}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{t('preview')}</span>
            </button>
            <button
              onClick={() => handleTabChange("edit")}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
                tabMode === "edit"
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
              title={t('edit')}
            >
              <Code className="w-3.5 h-3.5" />
              <span>{t('edit')}</span>
              {isDirty && <Circle className="w-2 h-2 fill-blue-500 text-blue-500" />}
            </button>
          </div>

          {/* Save button - only show in edit mode when dirty */}
          {tabMode === "edit" && isDirty && (
            <button
              onClick={handleSave}
              disabled={saveLoading}
              className="p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors disabled:opacity-50"
              title={t('save')}
            >
              {saveLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
            </button>
          )}

          <button
            onClick={handleRefresh}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title={t('refresh')}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleOpenExternal}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title={t('openNewTab')}
          >
            <ExternalLink className="w-4 h-4" />
          </button>
          <button
            onClick={handleToggleFullscreen}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title={isFullscreen ? t('exitFullscreen') : t('fullscreen')}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title={t('closePreview')}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 relative">
        {tabMode === "preview" ? (
          <>
            {/* Loading skeleton */}
            {iframeLoading && (
              <div className="absolute inset-0 bg-zinc-900 flex items-center justify-center z-10">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin" />
                  <span className="text-sm text-zinc-500">{t('loadingPreview')}</span>
                </div>
              </div>
            )}
            <iframe
              key={refreshKey}
              ref={iframeRef}
              src={previewUrl}
              className="w-full h-full border-0 bg-white"
              title={`Preview: ${filename}`}
              sandbox="allow-scripts allow-same-origin"
              onLoad={() => setIframeLoading(false)}
            />
            {isDragging && (
              <div className="absolute inset-0 z-10" />
            )}
          </>
        ) : (
          <div className="h-full min-h-0">
            {codeLoading ? (
              <div className="flex items-center justify-center h-full bg-zinc-950">
                <div className="flex flex-col items-center gap-2">
                  <RefreshCw className="w-6 h-6 animate-spin text-zinc-500" />
                  <span className="text-sm text-zinc-500">{t('loadingFile')}</span>
                </div>
              </div>
            ) : (
              <MonacoEditor
                value={code}
                language={language}
                onChange={handleEditorChange}
                onSave={handleSave}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
