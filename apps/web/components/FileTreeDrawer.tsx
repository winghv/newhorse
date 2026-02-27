"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
  Eye,
  X,
} from "lucide-react";
import { isPreviewable } from "./FilePreview";
import { useTranslations } from "next-intl";

interface FileNode {
  name: string;
  type: "file" | "directory";
  path: string;
  children?: FileNode[];
}

interface FileTreeDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onFileSelect: (path: string) => void;
}

function getFileIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "js": case "jsx": case "ts": case "tsx":
    case "py": case "go": case "rs": case "java":
      return <FileCode className="w-4 h-4 text-blue-400" />;
    case "json": case "yaml": case "yml": case "toml":
      return <FileJson className="w-4 h-4 text-yellow-400" />;
    case "md": case "txt": case "log":
      return <FileText className="w-4 h-4 text-zinc-400" />;
    case "html": case "htm":
      return <FileCode className="w-4 h-4 text-orange-400" />;
    case "css": case "scss":
      return <FileCode className="w-4 h-4 text-pink-400" />;
    case "svg":
      return <Eye className="w-4 h-4 text-green-400" />;
    default:
      return <File className="w-4 h-4 text-zinc-500" />;
  }
}

function DrawerTreeNode({
  node,
  onSelect,
  level = 0,
}: {
  node: FileNode;
  onSelect: (path: string) => void;
  level?: number;
}) {
  const [isOpen, setIsOpen] = useState(level < 1);
  const canPreview = node.type === "file" && isPreviewable(node.name);

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
        className={`flex items-center gap-1.5 py-1.5 px-2 rounded-md cursor-pointer text-sm transition-colors ${
          canPreview
            ? "hover:bg-blue-500/10 text-zinc-200"
            : "hover:bg-zinc-800 text-zinc-400"
        }`}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={handleClick}
      >
        {node.type === "directory" ? (
          <>
            {isOpen ? (
              <ChevronDown className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
            )}
            {isOpen ? (
              <FolderOpen className="w-4 h-4 text-yellow-500 flex-shrink-0" />
            ) : (
              <Folder className="w-4 h-4 text-yellow-500 flex-shrink-0" />
            )}
          </>
        ) : (
          <>
            <span className="w-3.5 flex-shrink-0" />
            {getFileIcon(node.name)}
          </>
        )}
        <span className="truncate flex-1">{node.name}</span>
        {canPreview && (
          <Eye className="w-3.5 h-3.5 text-green-400 flex-shrink-0 opacity-50" />
        )}
      </div>

      {node.type === "directory" && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <DrawerTreeNode
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

export function FileTreeDrawer({
  projectId,
  isOpen,
  onClose,
  onFileSelect,
}: FileTreeDrawerProps) {
  const t = useTranslations('fileTree');
  const [tree, setTree] = useState<FileNode[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTree = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/projects/${projectId}/files`);
      if (!res.ok) {
        setTree([]);
        return;
      }
      const data = await res.json();
      setTree(data.tree || []);
    } catch {
      setTree([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (isOpen) fetchTree();
  }, [isOpen, fetchTree]);

  const handleSelect = (path: string) => {
    onFileSelect(path);
    onClose();
  };

  const [visible, setVisible] = useState(false);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    if (isOpen) {
      // Trigger enter animation on next frame
      animFrameRef.current = requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
    }
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop - only over chat area */}
      <div
        className={`absolute inset-0 bg-black/40 z-20 transition-opacity duration-150 ${
          visible ? "opacity-100" : "opacity-0"
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={`absolute top-0 left-0 bottom-0 w-[280px] bg-zinc-900 border-r border-zinc-800 z-30 flex flex-col shadow-2xl transition-transform duration-200 ease-out ${
          visible ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-zinc-800">
          <span className="text-sm font-medium text-zinc-200">{t('title')}</span>
          <div className="flex items-center gap-1">
            <button
              onClick={fetchTree}
              className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
              title={t('refresh')}
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
              title={t('close')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tree content */}
        <div className="flex-1 overflow-y-auto py-2">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-5 h-5 animate-spin text-zinc-500" />
            </div>
          ) : tree.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-zinc-500">
              {t('noFiles')}
            </div>
          ) : (
            tree.map((node) => (
              <DrawerTreeNode
                key={node.path}
                node={node}
                onSelect={handleSelect}
              />
            ))
          )}
        </div>
      </div>
    </>
  );
}
