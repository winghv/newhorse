"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, Send, Bot, User, Loader2, FolderOpen, Settings, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Panel, Group } from "react-resizable-panels";
import { PreviewPanel } from "@/components/PreviewPanel";
import { ResizeHandle } from "@/components/ResizeHandle";
import { FileTreeDrawer } from "@/components/FileTreeDrawer";
import { isPreviewable } from "@/components/PreviewPanel";
import { AgentConfig } from "@/components/AgentConfig";
import { toast } from "sonner";
import { AgentCreatedModal } from "@/components/AgentCreatedModal";
import ModelSelector from "@/components/ModelSelector";

interface Message {
  id: string;
  role: string;
  content: string;
  type: string;
  metadata?: Record<string, any>;
  created_at?: string;
}

export default function ChatPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [showFileTree, setShowFileTree] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const lastDetectedFileRef = useRef<string | null>(null);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [selectedProviderId, setSelectedProviderId] = useState<string>("");
  const [defaultLoaded, setDefaultLoaded] = useState(false);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [agentModalData, setAgentModalData] = useState<{
    name: string;
    description: string;
    model: string;
    newProjectId: string;
  } | null>(null);

  // Load default model on mount
  useEffect(() => {
    if (defaultLoaded) return;
    fetch("/api/models")
      .then((r) => r.json())
      .then((groups) => {
        for (const g of groups) {
          if (!g.has_api_key) continue;
          for (const m of g.models) {
            if (m.is_default) {
              setSelectedModel(m.model_id);
              setSelectedProviderId(g.provider_id);
              setDefaultLoaded(true);
              return;
            }
          }
        }
      })
      .catch(() => {});
  }, [defaultLoaded]);

  useEffect(() => {
    // Load message history from server
    fetch(`/api/chat/${projectId}/messages`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setMessages(data.filter((m: Message) => !m.metadata?.hidden_from_ui));
        }
      })
      .catch((err) => console.error("Failed to load messages:", err));

    // Connect WebSocket
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/api/chat/${projectId}`);

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");

      // Auto-send initial message from homepage creation
      const storageKey = `newhorse-initial-message-${projectId}`;
      const initialMessage = localStorage.getItem(storageKey);
      if (initialMessage) {
        localStorage.removeItem(storageKey);
        const userMessage: Message = {
          id: `user-${Date.now()}`,
          role: "user",
          content: initialMessage,
          type: "chat",
        };
        setMessages((prev) => [...prev, userMessage]);
        ws.send(JSON.stringify({ content: initialMessage, model: selectedModel || undefined, provider_id: selectedProviderId || undefined }));
        setIsLoading(true);
      }
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      // Skip hidden messages
      if (message.metadata?.hidden_from_ui) return;

      setMessages((prev) => {
        // Avoid duplicates
        if (prev.some((m) => m.id === message.id)) return prev;
        return [...prev, message];
      });

      // Auto-detect HTML/SVG file writes for preview
      if (message.type === "tool_use") {
        const toolName = message.metadata?.tool_name;
        const toolInput = message.metadata?.tool_input;
        if (
          (toolName === "Write" || toolName === "write_file" || toolName === "write") &&
          toolInput?.file_path
        ) {
          const filePath = toolInput.file_path;
          const relativePath = filePath.includes("/")
            ? filePath.split("/").slice(-1)[0]
            : filePath;
          if (isPreviewable(relativePath) && filePath !== lastDetectedFileRef.current) {
            lastDetectedFileRef.current = filePath;
            const pathParts = filePath.split("/");
            const workspaceIdx = pathParts.findIndex((p: string) => p === "workspace");
            const relPath = workspaceIdx >= 0
              ? pathParts.slice(workspaceIdx + 1).join("/")
              : pathParts[pathParts.length - 1];

            // Wait for file to exist before opening preview
            // (tool_use message is sent before file write completes)
            const checkFileExists = async (retries: number = 5): Promise<boolean> => {
              for (let i = 0; i < retries; i++) {
                try {
                  const res = await fetch(`/api/projects/${projectId}/files/${relPath}`, {
                    method: "HEAD",
                  });
                  if (res.ok) return true;
                } catch {
                  // File doesn't exist yet
                }
                await new Promise((resolve) => setTimeout(resolve, 300));
              }
              return false;
            };

            checkFileExists().then((exists) => {
              if (exists) {
                setPreviewFile(relPath);
              }
            });
          }
        }
      }

      // Stop loading when session completes
      if (message.type === "session_complete" || message.type === "stopped") {
        setIsLoading(false);
        setIsStopping(false);
        if (message.type === "stopped") {
          toast.info("Execution stopped. Send a message to continue.");
        }
      }

      // Handle agent_created: show confirmation modal
      if (message.type === "agent_created") {
        const newProjectId = message.metadata?.new_project_id;
        if (newProjectId) {
          setAgentModalData({
            name: message.metadata?.template_name || "",
            description: message.metadata?.template_description || "",
            model: message.metadata?.template_model || "claude-sonnet-4-5-20250929",
            newProjectId,
          });
          setShowAgentModal(true);
        }
        setIsLoading(false);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [projectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim() || !wsRef.current || !isConnected) return;

    // Add user message locally
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input,
      type: "chat",
    };
    setMessages((prev) => [...prev, userMessage]);

    // Send to server
    wsRef.current.send(JSON.stringify({ content: input, model: selectedModel || undefined, provider_id: selectedProviderId || undefined }));
    setInput("");
    setIsLoading(true);
  };

  const handleStop = () => {
    console.log("[DEBUG] handleStop called", { wsRef: !!wsRef.current, isConnected, isLoading });
    if (!wsRef.current || !isConnected || !isLoading) return;
    setIsStopping(true);
    const msg = JSON.stringify({ action: "stop" });
    console.log("[DEBUG] Sending stop action:", msg);
    wsRef.current.send(msg);
  };

  const handleAgentConfirm = async (data: { name: string; description: string; model: string }) => {
    if (!agentModalData) return;

    const hasChanges =
      data.name !== agentModalData.name ||
      data.description !== agentModalData.description ||
      data.model !== agentModalData.model;

    if (hasChanges) {
      try {
        await fetch(`/api/projects/${agentModalData.newProjectId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: data.name,
            description: data.description,
            selected_model: data.model,
          }),
        });
      } catch (error) {
        console.error("Failed to update project:", error);
      }
    }

    toast.success(`Agent "${data.name}" 已确认，正在跳转...`);
    setShowAgentModal(false);
    setTimeout(() => {
      window.location.href = `/chat/${agentModalData.newProjectId}`;
    }, 800);
  };

  const handleAgentCancel = () => {
    setShowAgentModal(false);
    setAgentModalData(null);
  };

  return (
    <main className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center gap-4 p-4 border-b border-zinc-800">
        <Link href="/" className="p-2 hover:bg-zinc-800 rounded-lg transition">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <button
          onClick={() => setShowFileTree(!showFileTree)}
          className={`p-2 rounded-lg transition ${
            showFileTree ? "bg-blue-600 text-white" : "hover:bg-zinc-800"
          }`}
          title="Project files"
        >
          <FolderOpen className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-500" />
          <span className="font-medium truncate">Project: {projectId}</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {/* Model selector in header */}
          <div className="flex items-center gap-2 px-2">
            <ModelSelector
              value={selectedModel}
              providerId={selectedProviderId}
              onChange={(modelId, providerId) => {
                setSelectedModel(modelId);
                setSelectedProviderId(providerId);
              }}
            />
          </div>
          <button
            onClick={() => setShowConfigPanel(!showConfigPanel)}
            className={`p-2 rounded-lg transition ${
              showConfigPanel ? "bg-blue-600 text-white" : "hover:bg-zinc-800"
            }`}
            title="Agent 配置"
          >
            <Settings className="w-5 h-5" />
          </button>
          <div
            className={`px-2 py-1 text-xs rounded ${
              isConnected ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"
            }`}
          >
            {isConnected ? "Connected" : "Disconnected"}
          </div>
        </div>
      </header>

      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        <Group orientation="horizontal">
          {/* Chat panel */}
          <Panel minSize={30} defaultSize={previewFile ? 50 : 100}>
            <div className="flex-1 flex flex-col h-full min-w-0 relative">
              {/* File tree drawer overlay */}
              <FileTreeDrawer
                projectId={projectId}
                isOpen={showFileTree}
                onClose={() => setShowFileTree(false)}
                onFileSelect={(path) => {
                  // 打开预览面板，可视化文件默认预览，其他默认编辑
                  setPreviewFile(path);
                }}
              />

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-4xl mx-auto space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-12 text-zinc-500">
                    <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Start a conversation with your AI agent</p>
                  </div>
                )}

                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}
                  >
                    {message.role !== "user" && (
                      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4" />
                      </div>
                    )}

                    <div
                      className={`max-w-[80%] rounded-lg p-3 ${
                        message.role === "user"
                          ? "bg-blue-600"
                          : message.type === "tool_use"
                          ? "bg-zinc-800 border border-zinc-700"
                          : message.type === "session_complete"
                          ? "bg-green-900/30 border border-green-800"
                          : "bg-zinc-900"
                      }`}
                    >
                      {message.type === "tool_use" ? (
                        <div className="text-sm font-mono">{message.content}</div>
                      ) : (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code({ node, inline, className, children, ...props }: any) {
                              const match = /language-(\w+)/.exec(className || "");
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={vscDarkPlus}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, "")}
                                </SyntaxHighlighter>
                              ) : (
                                <code className="bg-zinc-800 px-1 rounded" {...props}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      )}
                    </div>

                    {message.role !== "user" && message.metadata?.provider_name && (
                      <span className="text-xs text-zinc-600 mt-1 block">
                        {message.metadata.provider_name} · {message.metadata.model || message.metadata?.model_id || ""}
                      </span>
                    )}

                    {message.role === "user" && (
                      <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center flex-shrink-0">
                        <User className="w-4 h-4" />
                      </div>
                    )}
                  </div>
                ))}

                {isLoading && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4" />
                    </div>
                    <div className="bg-zinc-900 rounded-lg p-3">
                      <Loader2 className="w-5 h-5 animate-spin" />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Input */}
              <div className="p-4 border-t border-zinc-800">
                <div className="flex gap-2 max-w-4xl mx-auto">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && !isLoading && sendMessage()}
                    placeholder={isLoading ? "Agent is executing..." : "Type a message..."}
                    className="flex-1 px-4 py-3 bg-zinc-900 rounded-lg border border-zinc-800 focus:outline-none focus:border-blue-500"
                    disabled={!isConnected || isLoading}
                  />
                  {isLoading ? (
                    <button
                      onClick={handleStop}
                      disabled={!isConnected || isStopping}
                      className={`px-4 py-3 ${isStopping ? 'bg-zinc-600' : 'bg-red-600 hover:bg-red-700'} disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition flex items-center gap-2`}
                      title={isStopping ? "Stopping..." : "Stop execution"}
                    >
                      {isStopping ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          <span className="text-sm">Stopping...</span>
                        </>
                      ) : (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                          <rect x="6" y="6" width="12" height="12" rx="2" />
                        </svg>
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={sendMessage}
                      disabled={!isConnected || isLoading || !input.trim()}
                      className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </Panel>

          {/* Resize handle + Preview panel (conditional) */}
          {previewFile && (
            <>
              <ResizeHandle onDragging={setIsDragging} />
              <Panel minSize={25} defaultSize={50}>
                <PreviewPanel
                  projectId={projectId}
                  filePath={previewFile}
                  onClose={() => setPreviewFile(null)}
                  isDragging={isDragging}
                  defaultMode={isPreviewable(previewFile) ? "preview" : "edit"}
                />
              </Panel>
            </>
          )}
        </Group>

        {/* Agent Config Panel (unchanged, stays outside PanelGroup) */}
        {showConfigPanel && (
          <div className="w-80 md:w-96 border-l border-zinc-800 bg-zinc-900/50 flex-shrink-0 flex flex-col">
            <div className="flex items-center justify-between p-3 border-b border-zinc-800">
              <h3 className="font-medium text-sm">Agent 配置</h3>
              <button
                onClick={() => setShowConfigPanel(false)}
                className="p-1 hover:bg-zinc-800 rounded transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <AgentConfig projectId={projectId} className="" />
            </div>
          </div>
        )}
      </div>

      {/* Agent Created Confirmation Modal */}
      {agentModalData && (
        <AgentCreatedModal
          isOpen={showAgentModal}
          agentName={agentModalData.name}
          agentDescription={agentModalData.description}
          agentModel={agentModalData.model}
          newProjectId={agentModalData.newProjectId}
          onConfirm={handleAgentConfirm}
          onCancel={handleAgentCancel}
        />
      )}
    </main>
  );
}
