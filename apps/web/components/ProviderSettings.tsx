"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  CheckCircle,
  XCircle,
  Plus,
  Trash2,
  Pencil,
  Loader2,
  ChevronDown,
  ChevronRight,
  Shield,
} from "lucide-react";
import { toast } from "sonner";

/* ── Types ── */

interface Model {
  id: string;
  model_id: string;
  display_name: string;
  is_default: boolean;
}

interface Provider {
  id: string;
  name: string;
  protocol: string;
  base_url: string;
  is_builtin: boolean;
  is_enabled: boolean;
  has_api_key: boolean;
  models: Model[];
  created_at: string;
  updated_at?: string;
}

interface ModelFormState {
  model_id: string;
  display_name: string;
  is_default: boolean;
}

const emptyModelForm: ModelFormState = {
  model_id: "",
  display_name: "",
  is_default: false,
};

/* ── Component ── */

export default function ProviderSettings() {
  const t = useTranslations('providers');

  const [providers, setProviders] = useState<Provider[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verifyResults, setVerifyResults] = useState<Record<string, boolean>>({});
  const [editingKey, setEditingKey] = useState<Record<string, string>>({});
  const [editingUrl, setEditingUrl] = useState<Record<string, string>>({});

  // Add provider form
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [newProvider, setNewProvider] = useState({
    name: "",
    protocol: "openai",
    base_url: "",
    api_key: "",
  });

  // Model editing
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [modelForm, setModelForm] = useState<ModelFormState>(emptyModelForm);
  const [modelDialogProvider, setModelDialogProvider] = useState<string | null>(null);

  /* ── Fetch providers ── */

  const fetchProviders = async () => {
    try {
      const res = await fetch("/api/providers");
      if (res.ok) {
        const data = await res.json();
        setProviders(data);
      }
    } catch {
      toast.error(t('loadFailed'));
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  /* ── Provider CRUD ── */

  const createProvider = async () => {
    if (!newProvider.name.trim() || !newProvider.base_url.trim()) {
      toast.error(t('nameRequired'));
      return;
    }
    try {
      const res = await fetch("/api/providers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newProvider),
      });
      if (res.ok) {
        toast.success(t('providerCreated'));
        setShowAddProvider(false);
        setNewProvider({ name: "", protocol: "openai", base_url: "", api_key: "" });
        fetchProviders();
      } else {
        const err = await res.json();
        toast.error(err.detail || t('createFailed'));
      }
    } catch {
      toast.error(t('createFailed'));
    }
  };

  const updateProvider = async (id: string, patch: Record<string, unknown>) => {
    try {
      const res = await fetch(`/api/providers/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (res.ok) {
        toast.success(t('providerUpdated'));
        fetchProviders();
      } else {
        const err = await res.json();
        toast.error(err.detail || t('updateFailed'));
      }
    } catch {
      toast.error(t('updateFailed'));
    }
  };

  const deleteProvider = async (id: string) => {
    if (!confirm(t('deleteProviderConfirm'))) return;
    try {
      const res = await fetch(`/api/providers/${id}`, { method: "DELETE" });
      if (res.ok) {
        toast.success(t('providerDeleted'));
        if (expandedId === id) setExpandedId(null);
        fetchProviders();
      } else {
        toast.error(t('deleteFailed'));
      }
    } catch {
      toast.error(t('deleteFailed'));
    }
  };

  const verifyProvider = async (id: string) => {
    setVerifying(id);
    try {
      const res = await fetch(`/api/providers/${id}/verify`, { method: "POST" });
      const data = await res.json();
      setVerifyResults((prev) => ({ ...prev, [id]: data.success }));
      if (data.success) {
        toast.success(t('connectionVerified'));
      } else {
        toast.error(data.error || t('verificationFailed'));
      }
    } catch {
      setVerifyResults((prev) => ({ ...prev, [id]: false }));
      toast.error(t('verificationFailed'));
    } finally {
      setVerifying(null);
    }
  };

  /* ── Model CRUD ── */

  const openModelDialog = (providerId: string, model?: Model) => {
    setModelDialogProvider(providerId);
    if (model) {
      setEditingModel(model);
      setModelForm({
        model_id: model.model_id,
        display_name: model.display_name,
        is_default: model.is_default,
      });
    } else {
      setEditingModel(null);
      setModelForm(emptyModelForm);
    }
  };

  const closeModelDialog = () => {
    setModelDialogProvider(null);
    setEditingModel(null);
    setModelForm(emptyModelForm);
  };

  const saveModel = async () => {
    if (!modelDialogProvider || !modelForm.model_id.trim()) {
      toast.error(t('modelIdRequired'));
      return;
    }

    try {
      if (editingModel) {
        // Update existing model
        const res = await fetch(
          `/api/providers/${modelDialogProvider}/models/${editingModel.id}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(modelForm),
          }
        );
        if (res.ok) {
          toast.success(t('modelUpdated'));
        } else {
          const err = await res.json();
          toast.error(err.detail || t('modelUpdateFailed'));
          return;
        }
      } else {
        // Create new model
        const res = await fetch(
          `/api/providers/${modelDialogProvider}/models`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(modelForm),
          }
        );
        if (res.ok) {
          toast.success(t('modelAdded'));
        } else {
          const err = await res.json();
          toast.error(err.detail || t('modelAddFailed'));
          return;
        }
      }
      closeModelDialog();
      fetchProviders();
    } catch {
      toast.error(t('modelSaveFailed'));
    }
  };

  const deleteModel = async (providerId: string, modelId: string) => {
    if (!confirm(t('deleteModelConfirm'))) return;
    try {
      const res = await fetch(`/api/providers/${providerId}/models/${modelId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        toast.success(t('modelDeleted'));
        fetchProviders();
      } else {
        toast.error(t('modelDeleteFailed'));
      }
    } catch {
      toast.error(t('modelDeleteFailed'));
    }
  };

  /* ── Helpers ── */

  const maskKey = (hasKey: boolean) => (hasKey ? "sk-••••••••" : t('notSet'));

  const toggleExpanded = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  /* ── Render ── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t('title')}</h2>
        <button
          onClick={() => setShowAddProvider(!showAddProvider)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('addCustom')}
        </button>
      </div>

      {/* Add provider form */}
      {showAddProvider && (
        <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800 space-y-3">
          <h3 className="text-sm font-medium text-zinc-300">{t('newProvider')}</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-zinc-500 mb-1">{t('nameLabel')}</label>
              <input
                type="text"
                value={newProvider.name}
                onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                placeholder="My Provider"
                className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">{t('protocolLabel')}</label>
              <select
                value={newProvider.protocol}
                onChange={(e) => setNewProvider({ ...newProvider, protocol: e.target.value })}
                className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
              >
                <option value="openai">{t('protocolOpenAI')}</option>
                <option value="anthropic">{t('protocolAnthropic')}</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">{t('baseUrlLabel')}</label>
            <input
              type="text"
              value={newProvider.base_url}
              onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
              placeholder="https://api.example.com/v1"
              className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">{t('apiKeyLabel')}</label>
            <input
              type="password"
              value={newProvider.api_key}
              onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
              placeholder="sk-..."
              className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowAddProvider(false)}
              className="px-3 py-1.5 text-sm text-zinc-400 hover:text-zinc-300 transition"
            >
              {t('cancel')}
            </button>
            <button
              onClick={createProvider}
              className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition"
            >
              {t('create')}
            </button>
          </div>
        </div>
      )}

      {/* Provider list */}
      <div className="space-y-2">
        {providers.map((provider) => (
          <div
            key={provider.id}
            className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden"
          >
            {/* Provider row */}
            <div
              className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-800/50 transition"
              onClick={() => toggleExpanded(provider.id)}
            >
              {/* Expand icon */}
              {expandedId === provider.id ? (
                <ChevronDown className="w-4 h-4 text-zinc-500 shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-zinc-500 shrink-0" />
              )}

              {/* Enabled checkbox */}
              <input
                type="checkbox"
                checked={provider.is_enabled}
                onChange={(e) => {
                  e.stopPropagation();
                  updateProvider(provider.id, { is_enabled: !provider.is_enabled });
                }}
                onClick={(e) => e.stopPropagation()}
                className="w-4 h-4 rounded bg-zinc-700 border-zinc-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 shrink-0"
              />

              {/* Name + builtin badge */}
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-medium text-sm truncate">{provider.name}</span>
                {provider.is_builtin && (
                  <Shield className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                )}
              </div>

              {/* Masked key */}
              <span className="ml-auto text-xs text-zinc-600 shrink-0">
                {maskKey(provider.has_api_key)}
              </span>

              {/* Verify status icon */}
              {verifyResults[provider.id] !== undefined && (
                <span className="shrink-0">
                  {verifyResults[provider.id] ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400" />
                  )}
                </span>
              )}
            </div>

            {/* Expanded area */}
            {expandedId === provider.id && (
              <div className="px-4 pb-4 pt-2 border-t border-zinc-800 space-y-4">
                {/* API Key */}
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">{t('apiKeyLabel')}</label>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={editingKey[provider.id] ?? ""}
                      onChange={(e) =>
                        setEditingKey({ ...editingKey, [provider.id]: e.target.value })
                      }
                      placeholder={provider.has_api_key ? "Enter new key to replace" : "sk-..."}
                      className="flex-1 px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
                    />
                    <button
                      onClick={() => {
                        const key = editingKey[provider.id];
                        if (key?.trim()) {
                          updateProvider(provider.id, { api_key: key.trim() });
                          setEditingKey({ ...editingKey, [provider.id]: "" });
                        }
                      }}
                      className="px-3 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 rounded-lg transition"
                    >
                      {t('save')}
                    </button>
                  </div>
                </div>

                {/* Base URL (non-builtin only) */}
                {!provider.is_builtin && (
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">{t('baseUrlLabel')}</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editingUrl[provider.id] ?? provider.base_url}
                        onChange={(e) =>
                          setEditingUrl({ ...editingUrl, [provider.id]: e.target.value })
                        }
                        placeholder="https://api.example.com/v1"
                        className="flex-1 px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
                      />
                      <button
                        onClick={() => {
                          const url = editingUrl[provider.id];
                          if (url?.trim()) {
                            updateProvider(provider.id, { base_url: url.trim() });
                          }
                        }}
                        className="px-3 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 rounded-lg transition"
                      >
                        {t('save')}
                      </button>
                    </div>
                  </div>
                )}

                {/* Models */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs text-zinc-500">{t('models')}</label>
                    <button
                      onClick={() => openModelDialog(provider.id)}
                      className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition"
                    >
                      <Plus className="w-3 h-3" />
                      {t('addModel')}
                    </button>
                  </div>
                  {provider.models.length === 0 ? (
                    <div className="text-sm text-zinc-600 py-2">{t('noModels')}</div>
                  ) : (
                    <div className="space-y-1">
                      {provider.models.map((model) => (
                        <div
                          key={model.id}
                          className="flex items-center justify-between px-3 py-2 bg-zinc-800/50 rounded-lg"
                        >
                          <div className="min-w-0">
                            <span className="text-sm text-zinc-300">{model.display_name}</span>
                            <span className="ml-2 text-xs text-zinc-600">{model.model_id}</span>
                            {model.is_default && (
                              <span className="ml-2 text-xs bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded">
                                default
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => openModelDialog(provider.id, model)}
                              className="p-1.5 hover:bg-zinc-700 rounded transition text-zinc-500 hover:text-zinc-300"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => deleteModel(provider.id, model.id)}
                              className="p-1.5 hover:bg-red-900/50 rounded transition text-zinc-500 hover:text-red-400"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t border-zinc-800">
                  <button
                    onClick={() => verifyProvider(provider.id)}
                    disabled={verifying === provider.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 rounded-lg transition disabled:opacity-50"
                  >
                    {verifying === provider.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5" />
                    )}
                    {t('verifyConnection')}
                  </button>
                  {!provider.is_builtin && (
                    <button
                      onClick={() => deleteProvider(provider.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:bg-red-900/30 rounded-lg transition ml-auto"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      {t('deleteProvider')}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {providers.length === 0 && (
          <div className="text-center py-8 text-zinc-500 text-sm">
            {t('noProviders')}
          </div>
        )}
      </div>

      {/* Model edit modal */}
      {modelDialogProvider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md mx-4 rounded-xl bg-zinc-900 border border-zinc-700 p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-medium">
              {editingModel ? t('editModel') : t('addModel')}
            </h3>

            <div>
              <label className="block text-xs text-zinc-500 mb-1">{t('modelIdLabel')}</label>
              <input
                type="text"
                value={modelForm.model_id}
                onChange={(e) => setModelForm({ ...modelForm, model_id: e.target.value })}
                placeholder="e.g. gpt-4o, claude-sonnet-4-20250514"
                className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="block text-xs text-zinc-500 mb-1">{t('displayNameLabel')}</label>
              <input
                type="text"
                value={modelForm.display_name}
                onChange={(e) => setModelForm({ ...modelForm, display_name: e.target.value })}
                placeholder="e.g. GPT-4o, Claude Sonnet"
                className="w-full px-3 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-blue-500 transition"
              />
            </div>

            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={modelForm.is_default}
                onChange={(e) => setModelForm({ ...modelForm, is_default: e.target.checked })}
                className="w-4 h-4 rounded bg-zinc-700 border-zinc-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              {t('setDefault')}
            </label>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={closeModelDialog}
                className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-300 transition"
              >
                {t('cancel')}
              </button>
              <button
                onClick={saveModel}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition"
              >
                {editingModel ? t('saveChanges') : t('addModel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
