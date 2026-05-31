"""Locale-aware strings for the growth-oriented narrative MVP."""
from __future__ import annotations

SUPPORTED_LOCALES = ("ru", "en", "zh-CN")

STRINGS = {
    "ru": {
        "blocked": "Этот ход нельзя продолжить безопасно. Попробуйте описать безопасное действие, обращение за помощью или восстановление доверия.",
        "reflection_fallback": "Заметка героя: какой шаг поможет лучше учесть другого участника ситуации?",
    },
    "en": {
        "blocked": "This move cannot continue safely. Try a safe action, help-seeking, or trust repair.",
        "reflection_fallback": "Hero note: what step could better include another person's point of view?",
    },
    "zh-CN": {
        "blocked": "这个行动无法安全继续。请尝试安全行动、寻求帮助或修复信任。",
        "reflection_fallback": "角色笔记：下一步怎样更好地考虑另一位参与者的视角？",
    },
}

TEXT_TRANSLATIONS = {
    "What might Lin Yue be feeling, and what evidence in the scene supports your guess?": {
        "ru": "Дневник героя: какая деталь показывает, что перед следующим выбором важно учесть точку зрения Линь Юэ?",
        "en": "Hero journal: what clue suggests Lin Yue's perspective should matter before the next choice?",
        "zh-CN": "角色日记：哪个线索说明下一次选择前应该考虑林悦的视角？",
    },
    "Hero journal: what clue suggests Lin Yue's perspective should matter before the next choice?": {
        "ru": "Дневник героя: какая деталь показывает, что перед следующим выбором важно учесть точку зрения Линь Юэ?",
        "en": "Hero journal: what clue suggests Lin Yue's perspective should matter before the next choice?",
        "zh-CN": "角色日记：哪个线索说明下一次选择前应该考虑林悦的视角？",
    },
    "If the group made a harmful choice, what repair step could rebuild trust?": {
        "ru": "Если группа сделала вредный выбор, какой шаг поможет восстановить доверие?",
        "en": "If the group made a harmful choice, what repair step could rebuild trust?",
        "zh-CN": "如果小组做出了伤害他人的选择，什么补救行动可以重建信任？",
    },
    "What small accommodation would let everyone contribute without making anyone feel singled out?": {
        "ru": "Какая небольшая адаптация поможет каждому участвовать, не выделяя никого отдельно?",
        "en": "What small accommodation would let everyone contribute without making anyone feel singled out?",
        "zh-CN": "什么小调整能让每个人都能参与，同时不让任何人感到被特别对待？",
    },
}


def normalize_locale(locale: str | None) -> str:
    if locale in SUPPORTED_LOCALES:
        return locale
    normalized = (locale or "").lower()
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("zh"):
        return "zh-CN"
    if normalized.startswith("ru"):
        return "ru"
    return "ru"


def get_string(locale: str | None, key: str) -> str:
    normalized = normalize_locale(locale)
    return STRINGS.get(normalized, STRINGS["ru"]).get(key, STRINGS["ru"][key])


def localize_text(locale: str | None, text: str) -> str:
    normalized = normalize_locale(locale)
    translations = TEXT_TRANSLATIONS.get(text)
    if not translations:
        return text
    return translations.get(normalized) or translations.get("ru") or text


def get_user_locale(user) -> str:
    if not getattr(user, "is_authenticated", False):
        return "ru"
    try:
        return normalize_locale(user.accessibility_profile.locale)
    except Exception:
        return "ru"
