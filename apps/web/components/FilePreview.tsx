"use client";

import { useState, useRef, useEffect } from "react";
import {
  Eye,
  Code,
  RefreshCw,
  Maximize2,
  Minimize2,
  X,
  ExternalLink,
} from "lucide-react";

interface FilePreviewProps {
  projectId: string;
  filePath: string;
  onClose?: () => void;
  className?: string;
}

type ViewMode = "preview" | "code";

const PREVIEWABLE_EXTENSIONS = [".html", ".htm", ".svg"];

export function isPreviewable(filename: string): boolean {
  const ext = filename.toLowerCase().slice(filename.lastIndexOf("."));
  return PREVIEWABLE_EXTENSIONS.includes(ext);
}

export function FilePreview({
  projectId,
  filePath,
  onClose,
  className,
}: FilePreviewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("preview");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [code, setCode] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const filename = filePath.split("/").pop() || filePath;
  const previewUrl = `/api/preview/${projectId}/${filePath}`;

  // Fetch code content when switching to code view
  useEffect(() => {
    if (viewMode === "code" && !code) {
      setLoading(true);
      fetch(`/api/projects/${projectId}/files/${filePath}`)
        .then((res) => res.json())
        .then((data) => setCode(data.content || ""))
        .catch((err) => console.error("Failed to load code:", err))
        .finally(() => setLoading(false));
    }
  }, [viewMode, code, projectId, filePath]);

  const handleRefresh = () => {
    setRefreshKey((k) => k + 1);
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const handleOpenExternal = () => {
    window.open(previewUrl, "_blank");
  };

  const containerClass = isFullscreen
    ? "fixed inset-0 z-50 bg-zinc-900"
    : `flex flex-col h-full ${className}`;

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-700 bg-zinc-800/50">
        <div className="flex items-center gap-2 min-w-0">
          <Eye className="w-4 h-4 text-green-400" />
          <span className="text-sm font-medium truncate">{filename}</span>
        </div>

        <div className="flex items-center gap-1">
          {/* View mode toggle */}
          <div className="flex bg-zinc-700 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode("preview")}
              className={`px-2 py-1 text-xs rounded transition ${
                viewMode === "preview"
                  ? "bg-zinc-600 text-white"
                  : "text-zinc-400 hover:text-white"
              }`}
              title="Preview"
            >
              <Eye className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode("code")}
              className={`px-2 py-1 text-xs rounded transition ${
                viewMode === "code"
                  ? "bg-zinc-600 text-white"
                  : "text-zinc-400 hover:text-white"
              }`}
              title="Code"
            >
              <Code className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Actions */}
          <button
            onClick={handleRefresh}
            className="p-1.5 hover:bg-zinc-700 rounded transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleOpenExternal}
            className="p-1.5 hover:bg-zinc-700 rounded transition"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 hover:bg-zinc-700 rounded transition"
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-zinc-700 rounded transition"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-hidden bg-white">
        {viewMode === "preview" ? (
          <iframe
            key={refreshKey}
            ref={iframeRef}
            src={previewUrl}
            className="w-full h-full border-0"
            title={`Preview: ${filename}`}
            sandbox="allow-scripts allow-same-origin"
          />
        ) : (
          <div className="h-full overflow-auto bg-zinc-900 p-4">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <RefreshCw className="w-6 h-6 animate-spin text-zinc-500" />
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

export default FilePreview;
