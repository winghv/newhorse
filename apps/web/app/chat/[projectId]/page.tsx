"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, Send, Bot, User, Loader2, PanelLeftClose, PanelLeft, Settings, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { FileTree } from "@/components/FileTree";
import { AgentConfig } from "@/components/AgentConfig";

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
  const [showFilePanel, setShowFilePanel] = useState(true);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Connect WebSocket
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/api/chat/${projectId}`);

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
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

      // Stop loading when session completes
      if (message.type === "session_complete") {
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
    wsRef.current.send(JSON.stringify({ content: input }));
    setInput("");
    setIsLoading(true);
  };

  return (
    <main className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center gap-4 p-4 border-b border-zinc-800">
        <Link href="/" className="p-2 hover:bg-zinc-800 rounded-lg transition">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <button
          onClick={() => setShowFilePanel(!showFilePanel)}
          className="p-2 hover:bg-zinc-800 rounded-lg transition"
          title={showFilePanel ? "Hide files" : "Show files"}
        >
          {showFilePanel ? (
            <PanelLeftClose className="w-5 h-5" />
          ) : (
            <PanelLeft className="w-5 h-5" />
          )}
        </button>
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-blue-500" />
          <span className="font-medium truncate">Project: {projectId}</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
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

      {/* Main content area with file panel and chat */}
      <div className="flex flex-1 min-h-0">
        {/* File Panel - hidden on mobile by default */}
        {showFilePanel && (
          <div className="hidden md:block w-80 border-r border-zinc-800 bg-zinc-900/50 flex-shrink-0">
            <FileTree projectId={projectId} />
          </div>
        )}

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
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

          {/* Input */}
          <div className="p-4 border-t border-zinc-800">
            <div className="flex gap-2 max-w-4xl mx-auto">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder="Type a message..."
                className="flex-1 px-4 py-3 bg-zinc-900 rounded-lg border border-zinc-800 focus:outline-none focus:border-blue-500"
                disabled={!isConnected || isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={!isConnected || isLoading || !input.trim()}
                className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Agent Config Panel */}
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
    </main>
  );
}
