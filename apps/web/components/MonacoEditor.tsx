"use client";

import Editor, { OnMount } from "@monaco-editor/react";
import { useRef, useCallback, useEffect } from "react";
import { Loader2 } from "lucide-react";

interface MonacoEditorProps {
  value: string;
  language: string;
  onChange: (value: string) => void;
  onSave: () => void;
  readOnly?: boolean;
}

// 文件扩展名到语言的映射
const EXTENSION_TO_LANGUAGE: Record<string, string> = {
  ".ts": "typescript",
  ".tsx": "typescript",
  ".mts": "typescript",
  ".cts": "typescript",
  ".js": "javascript",
  ".jsx": "javascript",
  ".mjs": "javascript",
  ".cjs": "javascript",
  ".json": "json",
  ".html": "html",
  ".htm": "html",
  ".css": "css",
  ".scss": "scss",
  ".less": "less",
  ".md": "markdown",
  ".mdx": "markdown",
  ".py": "python",
  ".rb": "ruby",
  ".go": "go",
  ".rs": "rust",
  ".java": "java",
  ".kt": "kotlin",
  ".scala": "scala",
  ".c": "c",
  ".cpp": "cpp",
  ".cc": "cpp",
  ".cxx": "cpp",
  ".h": "c",
  ".hpp": "cpp",
  ".cs": "csharp",
  ".php": "php",
  ".sql": "sql",
  ".sh": "shell",
  ".bash": "shell",
  ".zsh": "shell",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".xml": "xml",
  ".svg": "xml",
  ".toml": "toml",
  ".ini": "ini",
  ".conf": "ini",
  ".dockerfile": "dockerfile",
  ".graphql": "graphql",
  ".gql": "graphql",
  ".vue": "vue",
  ".svelte": "html",
  ".txt": "plaintext",
};

export function getLanguageFromFilename(filename: string): string {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  return EXTENSION_TO_LANGUAGE[ext] || "plaintext";
}

export function MonacoEditor({
  value,
  language,
  onChange,
  onSave,
  readOnly = false,
}: MonacoEditorProps) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  const handleEditorMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor;

    // 设置编辑器选项
    editor.updateOptions({
      minimap: { enabled: false },
      fontSize: 13,
      lineNumbers: "on",
      scrollBeyondLastLine: false,
      wordWrap: "on",
      automaticLayout: true,
      tabSize: 2,
      padding: { top: 12, bottom: 12 },
      renderLineHighlight: "line",
      cursorBlinking: "smooth",
      smoothScrolling: true,
      readOnly,
    });

    // 添加 Cmd/Ctrl + S 保存快捷键
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      onSave();
    });

    // 设置主题
    monaco.editor.defineTheme("newhorse-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#09090b",
        "editor.foreground": "#e4e4e7",
        "editor.lineHighlightBackground": "#18181b",
        "editorLineNumber.foreground": "#71717a",
        "editorLineNumber.activeForeground": "#e4e4e7",
        "editor.selectionBackground": "#3b82f640",
        "editor.inactiveSelectionBackground": "#3b82f620",
      },
    });
    monaco.editor.setTheme("newhorse-dark");
  }, [onSave, readOnly]);

  const handleChange = useCallback((newValue: string | undefined) => {
    onChange(newValue || "");
  }, [onChange]);

  return (
    <div className="h-full w-full">
      <Editor
        height="100%"
        language={language}
        value={value}
        onChange={handleChange}
        onMount={handleEditorMount}
        loading={
          <div className="flex items-center justify-center h-full bg-zinc-950">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
              <span className="text-sm text-zinc-500">Loading editor...</span>
            </div>
          </div>
        }
        options={{
          readOnly,
        }}
      />
    </div>
  );
}
