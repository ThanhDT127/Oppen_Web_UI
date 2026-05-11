"""
Smart Routing — Complexity-based model tier selection.

Maps "auto" model names (e.g. openai-auto) to concrete model names
based on request complexity scoring. Integrates with quota-based downgrade.
"""

import re
from config import logger

# ── Provider tier mappings ──────────────────────────────────────
# Each provider maps: tier → concrete model name
# Tiers: SIMPLE (cheapest), MEDIUM, COMPLEX, REASONING (most capable)

PROVIDER_TIERS = {
    "openai-auto": {
        "SIMPLE": "chat-gpt-5",
        "MEDIUM": "chat-gpt-5.2",
        "COMPLEX": "chat-gpt-5.4",
        "REASONING": "chat-gpt-5.4",
    },
    "gemini-auto": {
        "SIMPLE": "chat-gemini-2.5-flash",
        "MEDIUM": "chat-gemini-3.1-flash-lite-preview",
        "COMPLEX": "chat-gemini-3.1-pro-preview",
        "REASONING": "chat-gemini-3.1-pro-preview",
    },
    "grok-auto": {
        "SIMPLE": "chat-grok-4.1-fast-lite",
        "MEDIUM": "chat-grok-4.1-fast",
        "COMPLEX": "chat-grok-4.20",
        "REASONING": "chat-grok-4.20",
    },
    "claude-auto": {
        "SIMPLE": "chat-claude-haiku-4.5",
        "MEDIUM": "chat-claude-sonnet-4.6",
        "COMPLEX": "chat-claude-opus-4.6",
        "REASONING": "chat-claude-opus-4.6",
    },
    "deepseek-auto": {
        "SIMPLE": "chat-deepseek-v4-flash",
        "MEDIUM": "chat-deepseek-v4-flash",
        "COMPLEX": "chat-deepseek-v4-pro",
        "REASONING": "chat-deepseek-v4-pro",
    },
}

# ── Complexity keywords (Vietnamese + English) ──────────────────
_BOOST_KEYWORDS = re.compile(
    r"(?i)\b("
    r"phân tích|so sánh|đánh giá|giải thích chi tiết|chứng minh|tóm tắt dài|"
    r"viết báo cáo|thiết kế|kiến trúc|tối ưu|debug|refactor|"
    r"analyze|compare|evaluate|explain in detail|prove|summarize|"
    r"write a report|design|architect|optimize|step by step|"
    r"code review|implement|algorithm|complexity"
    r")\b"
)

_REASONING_KEYWORDS = re.compile(
    r"(?i)\b("
    r"chứng minh rằng|tại sao|why does|prove that|"
    r"step by step reasoning|chain of thought|think carefully|"
    r"mathematical proof|logical deduction"
    r")\b"
)

# Quota downgrade threshold
QUOTA_DOWNGRADE_PERCENT = 60


def is_auto_model(model: str) -> bool:
    """Check if model is an auto-routing model name."""
    return isinstance(model, str) and model in PROVIDER_TIERS


def score_complexity(messages: list, has_vision: bool = False, has_files: bool = False) -> str:
    """
    Score request complexity and return tier name.

    Scoring heuristic:
    - Base score from message length and conversation depth
    - Keyword boost for analytical/reasoning terms
    - Vision/file attachment boost
    - Reasoning keyword detection forces REASONING tier

    Returns: "SIMPLE", "MEDIUM", "COMPLEX", or "REASONING"
    """
    score = 0

    if not isinstance(messages, list):
        return "SIMPLE"

    # --- Conversation depth ---
    user_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
    num_turns = len(user_messages)

    if num_turns >= 6:
        score += 3
    elif num_turns >= 3:
        score += 1

    # --- Last message length ---
    last_text = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                last_text = content
            elif isinstance(content, list):
                last_text = " ".join(
                    item.get("text", "") for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            break

    char_count = len(last_text)
    if char_count > 2000:
        score += 3
    elif char_count > 500:
        score += 2
    elif char_count > 100:
        score += 1

    # --- Total conversation token estimate ---
    total_chars = sum(
        len(m.get("content", "")) if isinstance(m.get("content"), str) else 0
        for m in messages if isinstance(m, dict)
    )
    if total_chars > 10000:
        score += 2
    elif total_chars > 3000:
        score += 1

    # --- Keyword boost ---
    boost_hits = len(_BOOST_KEYWORDS.findall(last_text))
    score += min(boost_hits, 3)  # Cap at +3

    # --- Reasoning detection (force tier) ---
    if _REASONING_KEYWORDS.search(last_text):
        return "REASONING"

    # --- Vision/file boost ---
    if has_vision:
        score += 2
    if has_files:
        score += 1

    # --- Map score to tier ---
    if score >= 6:
        return "COMPLEX"
    elif score >= 3:
        return "MEDIUM"
    else:
        return "SIMPLE"


def resolve_auto_model(
    model: str,
    messages: list,
    quota_percent: float,
    has_vision: bool = False,
    has_files: bool = False,
) -> tuple[str, str, bool]:
    """
    Resolve an auto-model name to a concrete model.

    Args:
        model: Auto model name (e.g. "openai-auto")
        messages: Chat messages for complexity scoring
        quota_percent: User's quota usage percentage (0-100+)
        has_vision: Whether request contains vision/image content
        has_files: Whether request contains file attachments

    Returns:
        Tuple of (resolved_model, tier, was_downgraded)
        - resolved_model: concrete model name
        - tier: tier that was selected
        - was_downgraded: True if forced to SIMPLE due to quota
    """
    tiers = PROVIDER_TIERS.get(model)
    if not tiers:
        return model, "UNKNOWN", False

    was_downgraded = False

    # Quota-based downgrade: >=60% → force SIMPLE
    if quota_percent >= QUOTA_DOWNGRADE_PERCENT:
        tier = "SIMPLE"
        was_downgraded = True
    else:
        tier = score_complexity(messages, has_vision, has_files)

    resolved = tiers.get(tier, tiers.get("SIMPLE", model))

    logger.info(
        "smart_route model=%s tier=%s resolved=%s quota=%.0f%% downgraded=%s",
        model, tier, resolved, quota_percent, was_downgraded,
    )

    return resolved, tier, was_downgraded
