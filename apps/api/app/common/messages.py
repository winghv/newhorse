"""
Internationalized message catalog for user-facing backend messages.

Only user-visible messages (WebSocket system messages, chat notifications) are
localized here. Developer-facing messages (terminal UI, HTTPException details)
stay in English.
"""

MESSAGES = {
    "en": {
        "agent_created": 'Agent "{name}" has been created',
        "execution_stopped": "Execution stopped",
        "session_cleared": "Conversation cleared, new session started",
        "agent_initialized": "Agent initialized (Model: {model})",
        "session_complete": "Session complete",
    },
    "zh": {
        "agent_created": 'Agent「{name}」已创建',
        "execution_stopped": "执行已停止",
        "session_cleared": "对话已清空，新会话已开始",
        "agent_initialized": "Agent 已初始化（模型：{model}）",
        "session_complete": "会话完成",
    },
}


def get_message(key: str, locale: str = "en", **kwargs) -> str:
    """Get a localized message by key with optional string interpolation."""
    catalog = MESSAGES.get(locale, MESSAGES["en"])
    msg = catalog.get(key, MESSAGES["en"].get(key, key))
    return msg.format(**kwargs) if kwargs else msg
