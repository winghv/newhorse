"use client";

import { useState, useRef } from "react";
import {
  RefreshCw,
  ExternalLink,
  Maximize2,
  Minimize2,
  X,
  Eye,
  Code,
  FileCode,
} from "lucide-react";

interface PreviewPanelProps {
  projectId: string;
  filePath: string;
  onClose: () => void;
}

export function PreviewPanel({ projectId, filePath, onClose }: PreviewPanelProps) {
  const [viewMode, setViewMode] = useState<"preview" | "code">("preview");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [code, setCode] = useState<string>("");
  const [codeLoading, setCodeLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [iframeLoading, setIframeLoading] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const filename = filePath.split("/").pop() || filePath;
  const previewUrl = `/api/preview/${projectId}/${filePath}`;

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

  const handleViewCode = async () => {
    if (viewMode === "code") {
      setViewMode("preview");
      return;
    }
    setViewMode("code");
    if (!code) {
      setCodeLoading(true);
      try {
        const res = await fetch(`/api/projects/${projectId}/files/${filePath}`);
        const data = await res.json();
        setCode(data.content || "");
      } catch (err) {
        console.error("Failed to load code:", err);
      } finally {
        setCodeLoading(false);
      }
    }
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
          {/* View mode toggle */}
          <div className="flex bg-zinc-800 rounded-md p-0.5 mr-1">
            <button
              onClick={() => setViewMode("preview")}
              className={`p-1.5 rounded transition-colors ${
                viewMode === "preview"
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
              title="Preview"
            >
              <Eye className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleViewCode}
              className={`p-1.5 rounded transition-colors ${
                viewMode === "code"
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
              title="Code"
            >
              <Code className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            onClick={handleRefresh}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleOpenExternal}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
          <button
            onClick={handleToggleFullscreen}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
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
            title="Close preview"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 relative">
        {viewMode === "preview" ? (
          <>
            {/* Loading skeleton */}
            {iframeLoading && (
              <div className="absolute inset-0 bg-zinc-900 flex items-center justify-center z-10">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-zinc-700 border-t-blue-500 rounded-full animate-spin" />
                  <span className="text-sm text-zinc-500">Loading preview...</span>
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
          </>
        ) : (
          <div className="h-full overflow-auto bg-zinc-950 p-4">
            {codeLoading ? (
              <div className="flex items-center justify-center h-full">
                <RefreshCw className="w-5 h-5 animate-spin text-zinc-500" />
              </div>
            ) : (
              <pre className="text-sm font-mono text-zinc-300 whitespace-pre-wrap">
                {code}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
