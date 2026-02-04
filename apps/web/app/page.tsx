"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Plus, MessageSquare, Trash2, Bot } from "lucide-react";
import { toast } from "sonner";

interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  preferred_cli: string;
  created_at: string;
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch("/api/projects/");
      const data = await res.json();
      setProjects(data);
    } catch (error) {
      toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const createProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      const res = await fetch("/api/projects/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newProjectName }),
      });

      if (res.ok) {
        const project = await res.json();
        setProjects([project, ...projects]);
        setNewProjectName("");
        setShowNewProject(false);
        toast.success("Project created");
      }
    } catch (error) {
      toast.error("Failed to create project");
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm("Delete this project?")) return;

    try {
      const res = await fetch(`/api/projects/${id}`, { method: "DELETE" });
      if (res.ok) {
        setProjects(projects.filter((p) => p.id !== id));
        toast.success("Project deleted");
      }
    } catch (error) {
      toast.error("Failed to delete project");
    }
  };

  return (
    <main className="min-h-screen p-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8 text-blue-500" />
            <h1 className="text-2xl font-bold">Newhorse</h1>
          </div>
          <button
            onClick={() => setShowNewProject(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
          >
            <Plus className="w-4 h-4" />
            New Project
          </button>
        </div>

        {/* New Project Form */}
        {showNewProject && (
          <div className="mb-6 p-4 bg-zinc-900 rounded-lg border border-zinc-800">
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project name..."
              className="w-full px-3 py-2 bg-zinc-800 rounded-lg border border-zinc-700 focus:outline-none focus:border-blue-500 mb-3"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && createProject()}
            />
            <div className="flex gap-2">
              <button
                onClick={createProject}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
              >
                Create
              </button>
              <button
                onClick={() => {
                  setShowNewProject(false);
                  setNewProjectName("");
                }}
                className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Projects List */}
        {loading ? (
          <div className="text-center py-12 text-zinc-500">Loading...</div>
        ) : projects.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-zinc-600" />
            <p className="text-zinc-500">No projects yet. Create one to get started!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((project) => (
              <div
                key={project.id}
                className="flex items-center justify-between p-4 bg-zinc-900 rounded-lg border border-zinc-800 hover:border-zinc-700 transition"
              >
                <Link href={`/chat/${project.id}`} className="flex-1">
                  <h3 className="font-medium">{project.name}</h3>
                  <p className="text-sm text-zinc-500">
                    {project.preferred_cli} · {new Date(project.created_at).toLocaleDateString()}
                  </p>
                </Link>
                <div className="flex items-center gap-2">
                  <Link
                    href={`/chat/${project.id}`}
                    className="p-2 hover:bg-zinc-800 rounded-lg transition"
                  >
                    <MessageSquare className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={() => deleteProject(project.id)}
                    className="p-2 hover:bg-red-900/50 rounded-lg transition text-red-400"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
