"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Folder,
  FolderOpen,
  File,
  FileCode,
  FileText,
  FileJson,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  X,
} from "lucide-react";

interface FileNode {
  name: string;
  type: "file" | "directory";
  path: string;
  children?: FileNode[];
}

interface FileTreeProps {
  projectId: string;
  onFileSelect?: (path: string, content: string) => void;
  className?: string;
}

interface FileContentViewerProps {
  path: string;
  content: string;
  onClose: () => void;
}

function getFileIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase();

  switch (ext) {
    case "js":
    case "jsx":
    case "ts":
    case "tsx":
    case "py":
    case "go":
    case "rs":
    case "java":
    case "cpp":
    case "c":
    case "h":
      return <FileCode className="w-4 h-4 text-blue-400" />;
    case "json":
    case "yaml":
    case "yml":
    case "toml":
      return <FileJson className="w-4 h-4 text-yellow-400" />;
    case "md":
    case "txt":
    case "log":
      return <FileText className="w-4 h-4 text-zinc-400" />;
    case "html":
    case "htm":
    case "css":
    case "scss":
      return <FileCode className="w-4 h-4 text-orange-400" />;
    default:
      return <File className="w-4 h-4 text-zinc-500" />;
  }
}

function FileContentViewer({ path, content, onClose }: FileContentViewerProps) {
  const filename = path.split("/").pop() || path;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-700 bg-zinc-800/50">
        <div className="flex items-center gap-2 min-w-0">
          {getFileIcon(filename)}
          <span className="text-sm font-medium truncate">{filename}</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-zinc-700 rounded transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        <pre className="p-3 text-sm font-mono text-zinc-300 whitespace-pre-wrap break-words">
          {content}
        </pre>
      </div>
    </div>
  );
}

function TreeNode({
  node,
  onSelect,
  level = 0,
}: {
  node: FileNode;
  onSelect: (path: string) => void;
  level?: number;
}) {
  const [isOpen, setIsOpen] = useState(level < 2);

  const handleClick = () => {
    if (node.type === "directory") {
      setIsOpen(!isOpen);
    } else {
      onSelect(node.path);
    }
  };

  return (
    <div>
      <div
        className="flex items-center gap-1 py-1 px-2 hover:bg-zinc-800 cursor-pointer rounded text-sm"
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        {node.type === "directory" ? (
          <>
            {isOpen ? (
              <ChevronDown className="w-3 h-3 text-zinc-500" />
            ) : (
              <ChevronRight className="w-3 h-3 text-zinc-500" />
            )}
            {isOpen ? (
              <FolderOpen className="w-4 h-4 text-yellow-500" />
            ) : (
              <Folder className="w-4 h-4 text-yellow-500" />
            )}
          </>
        ) : (
          <>
            <span className="w-3" />
            {getFileIcon(node.name)}
          </>
        )}
        <span className="ml-1 truncate">{node.name}</span>
      </div>

      {node.type === "directory" && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              onSelect={onSelect}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileTree({ projectId, onFileSelect, className }: FileTreeProps) {
  const [tree, setTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<{
    path: string;
    content: string;
  } | null>(null);

  const fetchTree = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`/api/projects/${projectId}/files`);
      if (!res.ok) {
        if (res.status === 404) {
          setTree([]);
          return;
        }
        throw new Error("Failed to fetch file tree");
      }
      const data = await res.json();
      setTree(data.tree || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  const handleFileSelect = async (path: string) => {
    try {
      const res = await fetch(`/api/projects/${projectId}/files/${path}`);
      if (!res.ok) throw new Error("Failed to fetch file");
      const data = await res.json();
      setSelectedFile({ path, content: data.content });
      onFileSelect?.(path, data.content);
    } catch (err) {
      console.error("Error loading file:", err);
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <RefreshCw className="w-5 h-5 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 text-red-400 text-sm ${className}`}>
        <p>Error: {error}</p>
        <button
          onClick={fetchTree}
          className="mt-2 text-blue-400 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-700">
        <span className="text-sm font-medium text-zinc-300">Files</span>
        <button
          onClick={fetchTree}
          className="p-1 hover:bg-zinc-700 rounded transition"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* File tree */}
        <div className="w-48 overflow-y-auto border-r border-zinc-700 py-2">
          {tree.length === 0 ? (
            <div className="px-3 py-2 text-sm text-zinc-500">
              No files yet
            </div>
          ) : (
            tree.map((node) => (
              <TreeNode
                key={node.path}
                node={node}
                onSelect={handleFileSelect}
              />
            ))
          )}
        </div>

        {/* File content viewer */}
        <div className="flex-1 min-w-0">
          {selectedFile ? (
            <FileContentViewer
              path={selectedFile.path}
              content={selectedFile.content}
              onClose={() => setSelectedFile(null)}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-zinc-500">
              Select a file to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default FileTree;
