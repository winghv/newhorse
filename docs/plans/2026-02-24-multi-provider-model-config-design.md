# Multi-Provider Model Configuration Design

## Overview

Support multiple AI providers (Anthropic, OpenAI, Deepseek, Qwen, GLM) with custom provider support (base_url + api_key override). Model selection takes effect immediately in chat without session restart.

## Requirements

- Built-in providers: Anthropic, OpenAI, Deepseek, Qwen, GLM
- Custom providers: override base_url + api_key for any built-in protocol
- Immediate effect: switch model mid-conversation, next message uses new model
- API Key management: global config + project-level override
- Protocol types: `anthropic` and `openai` (extensible for `gemini` etc.)

## Data Model

### New `providers` Table

| Field | Type | Description |
|-------|------|-------------|
| `id` | String(8) | Short ID primary key |
| `name` | String(255) | Display name, e.g. "My Anthropic Proxy" |
| `protocol` | String(32) | Protocol: `anthropic` / `openai` |
| `base_url` | String(512) | API endpoint, optional (empty = SDK default) |
| `api_key` | String(512) | Encrypted API Key |
| `is_builtin` | Boolean | Built-in provider (cannot delete) |
| `enabled` | Boolean | Whether enabled |
| `created_at` / `updated_at` | DateTime | Timestamps |

Built-in seed data (`is_builtin=True`, user only fills api_key):
- Anthropic (protocol=anthropic)
- OpenAI (protocol=openai)
- Deepseek (protocol=openai, base_url=https://api.deepseek.com)
- Qwen (protocol=openai, base_url=https://dashscope.aliyuncs.com/compatible-mode)
- GLM (protocol=openai, base_url=https://open.bigmodel.cn/api/paas)

### New `models` Table

| Field | Type | Description |
|-------|------|-------------|
| `id` | String(8) | Short ID primary key |
| `provider_id` | String(8) | Foreign key to provider |
| `model_id` | String(128) | Model identifier, e.g. `claude-sonnet-4-5-20250929` |
| `display_name` | String(128) | Display name, e.g. "Sonnet 4.5" |
| `is_default` | Boolean | Default model for this provider |
| `created_at` | DateTime | Timestamp |

### Extended `projects` Table

| New Field | Type | Description |
|-----------|------|-------------|
| `override_provider_id` | String(8) | Optional, override global provider |
| `override_api_key` | String(512) | Optional, project-specific key |

Existing `selected_model` field retained, stores `model_id` from models table.

### Extended `messages` Table

| New Field | Type | Description |
|-----------|------|-------------|
| `model_id` | String(128) | Model used for this message |
| `provider_id` | String(8) | Provider used for this message |

## Backend Architecture — Provider Router

### Execution Flow

```
BaseCLI.execute_with_streaming()
    |
    +-- Resolve model -> query models table -> get provider_id
    |
    +-- Resolve provider -> query providers table (project override > global)
    |
    +-- protocol == "anthropic"
    |   +-- AnthropicRunner(base_url, api_key, model_id)
    |       -> Reuse existing Claude Agent SDK logic
    |
    +-- protocol == "openai"
        +-- OpenAIRunner(base_url, api_key, model_id)
            -> OpenAI SDK, streaming chat completions
```

### New Module: `apps/api/app/services/cli/runners/`

- `base_runner.py` — Abstract base class: `stream_response(messages, model, tools)`, `convert_history(internal_messages)`
- `anthropic_runner.py` — Wraps existing Claude Agent SDK call logic
- `openai_runner.py` — OpenAI SDK, streaming + tool use conversion
- `router.py` — Routes to runner based on provider protocol field

Extensibility: adding Gemini SDK = new `gemini_runner.py` + add `gemini` to ProviderProtocol enum.

### Unified Streaming Output

Both runners output same event structure: `text_delta`, `tool_use`, `error`. WebSocket layer is provider-agnostic.

### API Key Resolution Priority

Message-level provider -> Project `override_api_key` -> Provider table `api_key` -> Environment variable fallback

### History Format Conversion

```
Internal history (unified format)
    |
    +-- AnthropicRunner -> Anthropic messages format
    |   { role: "user"/"assistant", content: [...] }
    |
    +-- OpenAIRunner -> OpenAI messages format
        { role: "user"/"assistant"/"system", content: "..." }
```

## API Endpoints

### New Provider Management — `apps/api/app/api/providers.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/providers` | List all providers (mask api_key) |
| `POST` | `/api/providers` | Create custom provider |
| `PATCH` | `/api/providers/{id}` | Update provider |
| `DELETE` | `/api/providers/{id}` | Delete custom provider (built-in cannot delete) |
| `GET` | `/api/providers/{id}/models` | List models for provider |
| `POST` | `/api/providers/{id}/models` | Add model to provider |
| `PATCH` | `/api/providers/{id}/models/{model_id}` | Update model |
| `DELETE` | `/api/providers/{id}/models/{model_id}` | Remove model |
| `POST` | `/api/providers/{id}/verify` | Verify connectivity |

### New Aggregated Models — `apps/api/app/api/models.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/models` | All models from enabled providers, grouped by provider |

### Extended Existing Endpoints

| Method | Path | Change |
|--------|------|--------|
| `PATCH` | `/api/projects/{id}` | Support `override_provider_id`, `override_api_key` |
| `WebSocket` | `/api/chat/{project_id}` | Message adds `model_id` + `provider_id` fields |

### New Enum in `types.py`

```python
class ProviderProtocol(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    # Future: GEMINI = "gemini"
```

## Frontend UI

### 1. Global Settings Page — `/settings`

Entry: gear icon in top navbar. Page layout:

- Provider list: built-in + custom, with enable/disable toggle
- Each row shows: name, masked key status, verify result icon
- Expand row to edit: API Key, Base URL (custom only), Models CRUD
- Model editing: inline table with model_id + display_name + is_default, edit/add/delete
- [+ Add Custom Provider] button at bottom
- [Verify Connection] button per provider (sends short message with max_tokens=1)

### 2. Chat Model Selector — Above Input Box

- Dropdown grouped by provider, only shows enabled + configured providers
- Selection takes immediate effect, next message uses new model
- Current model name displayed on dropdown button

### 3. AgentConfig Panel — Project Default Model

- Model dropdown replaced with same grouped ModelSelector component (reused)
- Optional "Use project-specific API Key" section
- Save sets project default

### 4. Message Model Tags

- Each AI reply bubble shows small tag indicating which model was used
- Enables visual tracking in mixed-model conversations

## Verification

### Connectivity Test (unified approach)

```
Anthropic -> messages.create({ model: default_model, messages: [{ role: "user", content: "hi" }], max_tokens: 1 })
OpenAI    -> chat.completions.create({ model: default_model, messages: [{ role: "user", content: "hi" }], max_tokens: 1 })
```

`max_tokens: 1` minimizes token consumption. Normal response = pass.

Returns: `{ success: true/false, error?: "Invalid API key", latency_ms: 320 }`

## Error Handling

| Scenario | Handling |
|----------|----------|
| Invalid/expired API Key | Stream returns error event, frontend toast: "API Key invalid, check settings" |
| Provider unreachable | 10s timeout, prompt to check base_url |
| Model not found | Provider returns 404, prompt "Model ID incorrect" |
| Project references deleted model | Fallback to provider default model, toast notification |
| Project references disabled provider | Fallback to global default provider+model, toast notification |

### Fallback Chain

```
Message-specified model+provider
    -> Project default model+provider
        -> First enabled+configured provider's default model
            -> Error: "Please configure at least one provider"
```

## Security

- API Key encrypted with Fernet (key from `ENCRYPTION_KEY` env var)
- API returns masked keys only: `sk-ant-api03-xxxx...***` (first 12 chars + ***)
- Empty input on edit = no change; new value = overwrite

## File Changes

### New Files

| File | Description |
|------|-------------|
| `apps/api/app/models/provider.py` | Provider + Model data models |
| `apps/api/app/api/providers.py` | Provider management API routes |
| `apps/api/app/api/models.py` | Aggregated model list API |
| `apps/api/app/services/cli/runners/__init__.py` | Runner module |
| `apps/api/app/services/cli/runners/base_runner.py` | Runner abstract base class |
| `apps/api/app/services/cli/runners/anthropic_runner.py` | Anthropic SDK calls |
| `apps/api/app/services/cli/runners/openai_runner.py` | OpenAI SDK calls |
| `apps/api/app/services/cli/runners/router.py` | Protocol routing |
| `apps/api/app/services/crypto.py` | API Key encrypt/decrypt utility |
| `apps/web/app/settings/page.tsx` | Global settings page |
| `apps/web/components/ProviderSettings.tsx` | Provider config component |
| `apps/web/components/ModelSelector.tsx` | Grouped model dropdown (reused in chat + AgentConfig) |

### Modified Files

| File | Change |
|------|--------|
| `apps/api/app/models/__init__.py` | Import Provider, ProviderModel |
| `apps/api/app/main.py` | Register providers, models routes |
| `apps/api/app/common/types.py` | Add `ProviderProtocol` enum |
| `apps/api/app/models/projects.py` | Add `override_provider_id`, `override_api_key` fields |
| `apps/api/app/models/message.py` | Add `model_id`, `provider_id` fields |
| `apps/api/app/services/cli/base.py` | Remove `MODEL_MAPPING`, call Router |
| `apps/api/app/services/cli/adapters/hello_agent.py` | Execution logic uses Runner |
| `apps/api/app/api/chat.py` | WebSocket message adds `provider_id` param |
| `apps/web/components/AgentConfig.tsx` | Model dropdown uses ModelSelector |
| `apps/web/app/chat/[projectId]/page.tsx` | Integrate model selector above input |
| `apps/web/components/Navbar.tsx` | Add settings page entry |
| `.env.example` | Add `ENCRYPTION_KEY` |

### New Dependencies

| Package | Purpose |
|---------|---------|
| `openai` (Python) | OpenAI SDK |
| `cryptography` (Python) | Fernet encryption |
