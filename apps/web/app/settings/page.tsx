"use client";

import Link from "next/link";
import { ArrowLeft, Settings } from "lucide-react";
import ProviderSettings from "@/components/ProviderSettings";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link href="/" className="p-2 rounded-lg hover:bg-zinc-800 transition-colors">
            <ArrowLeft className="w-5 h-5 text-zinc-400" />
          </Link>
          <Settings className="w-5 h-5 text-zinc-400" />
          <h1 className="text-lg font-medium">Settings</h1>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <ProviderSettings />
      </div>
    </div>
  );
}
