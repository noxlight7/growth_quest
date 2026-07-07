"""Prompt-building helpers for AI interactions."""
from __future__ import annotations

import json
import os

from ..models import (
    Adventure,
    AdventureEvent,
    AdventureHistory,
    AdventureMemory,
    AdventurePlayer,
    Character,
    CharacterRelationship,
    CharacterSystem,
    CharacterTechnique,
    ConsequenceMarker,
    LearningObjective,
    PedagogicalIntervention,
    RepairOpportunity,
    SafetyReview,
    SkillSystem,
    Technique,
)
from ..services.pedagogy import get_growth_director_decision
from ..services.narrative_consequences import (
    build_narrative_consequence_context,
    get_current_entity_scope,
    get_relevant_narrative_consequences,
)


STORY_PROMPT_TEXT = {
    "ru": {
        "empty_history": "История пока пуста.",
        "main_heroes": "Главные герои: {names}.",
        "no_main_heroes": "Главные герои не заданы.",
        "unknown_location": "Текущая локация: неизвестна.",
        "current_location": "Текущая локация: {title}.",
        "available_systems": "Доступные системы: {items}",
        "party_techniques": "Приемы партии: {items}",
        "body": "Тело {value} ({progress}%)",
        "mind": "Разум {value} ({progress}%)",
        "will": "Воля {value} ({progress}%)",
        "race": "Раса: {value}",
        "age": "Возраст: {value}",
        "systems": "Системы: {items}",
        "system_progress": "{title} (уровень {level}, прогресс {progress}%)",
        "techniques": "Приемы: {items}",
        "party_heroes": "Герои партии:\n{items}",
        "no_party_heroes": "Герои партии отсутствуют.",
        "status": "Статус: {value}",
        "description": "Описание: {value}",
        "location_characters": "Персонажи локации:\n{items}",
        "no_location_characters": "Персонажи локации отсутствуют.",
        "active_events": "Активные события:\n{items}",
        "no_active_events": "Активные события отсутствуют.",
        "repair_opportunities": "Открытые repair opportunities:\n{items}",
        "no_repair_opportunities": "Открытые repair opportunities отсутствуют.",
        "latest_consequences": "Последние игровые последствия:\n{items}",
        "no_latest_consequences": "Последние игровые последствия отсутствуют.",
        "skill_scaling": (
            "Важно: уровень владения системой повышает эффективность по геометрической прогрессии. "
            "То же относится к рангам/кругам приемов."
        ),
        "scenario_instructions": "Специальные инструкции сценария:\n{instructions}\n\n",
        "growth_header": "Ограничения growth director:",
        "growth_embedded": (
            "- Встраивай growth guidance в игровую сцену. Показывай последствия через состояние "
            "мира, доверие NPC, отношения и доступные варианты выбора."
        ),
        "growth_harm": (
            "- Если игроки делают вредящий другим или эгоистичный выбор, покажи последствия и "
            "оставь путь к исправлению там, где он уместен в истории."
        ),
        "growth_explicit_state": (
            "- Если игрок явно написал о чувствах, настроении, страхе, сомнениях или намерениях "
            "героя, считай это заявленным состоянием героя и учитывай его в реакциях и выборе."
        ),
        "growth_no_inference": (
            "- Не приписывай игроку эмоции, внутреннее состояние или черты личности, которые он "
            "не указал явно."
        ),
        "growth_focus": "- Текущий порядок growth focus: {items}.",
        "growth_signals": "- Текущие сигналы состояния: {items}.",
        "growth_note_open_repair": "открытый путь исправления: {value}",
        "growth_note_recent_opportunity": "недавняя growth-возможность: {value}",
        "growth_note_active_consequence": "активное последствие: {value}",
        "growth_note_active_event": "активное сюжетное событие: {value}",
        "safety_header": "Работа с чувствительными сюжетными темами:",
        "safety_bullying": (
            "при травле или исключении показывай социальные последствия через реакции NPC, не "
            "поощряй унижение и оставляй доступными поддержку свидетелей и пути исправления"
        ),
        "safety_violence": (
            "при насилии избегай графической эскалации, показывай реалистичные последствия и "
            "предлагай деэскалацию, отступление или обращение за помощью"
        ),
        "safety_self_harm": (
            "при сигналах самоповреждения избегай подробностей методов и направляй к немедленной "
            "поддержке доверенных людей или экстренных служб внутри вымышленного мира"
        ),
        "safety_sexual": (
            "при сигналах сексуального насилия не создавай откровенный контент; смести фокус на "
            "безопасность, поддержку, границы согласия и доверенную помощь"
        ),
        "safety_extremism": (
            "при сигналах экстремизма избегай вербовки, одобрения и тактических подробностей; "
            "сосредоточься на безопасности, критической дистанции и доверенной помощи"
        ),
        "safety_fallback": "обращайся с темой {category} осторожно и с поддержкой",
        "karma_header": "Долгосрочные сюжетные последствия:",
        "karma_memory": (
            "- Пусть запомненные действия и события мира влияют на последующие сцены через "
            "правдоподобную причинность: память NPC, доверие, слухи, информацию, доступную помощь "
            "и доступность сцен."
        ),
        "karma_constructive": (
            "- Пусть конструктивные поступки со временем открывают более богатые и приятные "
            "сюжетные возможности, если это правдоподобно следует из ситуации."
        ),
        "karma_harmful": (
            "- Пусть вредящие другим поступки приводят к правдоподобным издержкам, испорченным "
            "отношениям и потерянным возможностям, если это следует из ситуации."
        ),
        "karma_declared_outcome": (
            "- Никогда не давай запрошенный результат только потому, что игрок его объявил. "
            "Определяй успех, сопротивление и цену через уже установленную логику мира."
        ),
        "karma_short_term": (
            "- Вредящие действия могут давать краткосрочный тактический эффект, если это "
            "поддерживает логика мира, но повторяющаяся жестокость не должна становиться "
            "беспрепятственным источником растущих наград."
        ),
        "karma_believable": (
            "- Делай последствия правдоподобными, разнообразными и драматически интересными. Они "
            "должны ощущаться частью мира, а не механической системой очков."
        ),
        "narration_boundaries_header": "Границы повествования:",
        "narration_player_boundary": (
            "- Не придумывай новые добровольные действия, реплики, решения, мысли, чувства или "
            "взвешивание вариантов главными героями игроков. Можно разрешать явно заявленные "
            "игроком действия через успех, сопротивление, цену, частичный результат или неудачу."
        ),
        "narration_no_moral_summary": (
            "- Не пересказывай сцену как моральную развилку и не объясняй варианты в стиле "
            "`если исправить, то...; если проигнорировать, то...`. Не пиши за игрока, что герой "
            "чувствует вес решения, обдумывает последствия или взвешивает варианты."
        ),
        "narration_external_pressure": (
            "- Вместо этого показывай только внешние факты: реплики NPC, новую деталь, дедлайн, "
            "изменение обстановки или конкретное препятствие, которое приглашает следующий ход игрока. "
            "Оставь выбор открытым для следующего сообщения игрока."
        ),
        "continue_story": (
            "Сгенерируй следующий абзац истории, логично продолжая сюжет. Не повторяй и не "
            "пересказывай события, уже записанные в истории промтов. Ответ должен быть примерно "
            "на {word_limit} слов. Пиши продолжение истории только на русском языке."
        ),
        "party_npcs": "Неписи в партии: {items}.",
        "npc_generation": (
            "Сначала опиши действия и реплики неписей (2-3 предложения на каждую), затем продолжи "
            "историю одним коротким внешним абзацем. Если в последнем сообщении игрок обращается к неписям "
            "или задает вопросы и предполагается, что игрок ждёт ответа, а неписи готовы его дать, "
            "хотя бы один из неписей должен ответить прямой репликой в своих действиях. Не управляй "
            "действиями игроков, только неписями и общим развитием событий. После ответов NPC не "
            "объясняй выбор игрока: покажи только новую внешнюю деталь, дедлайн или препятствие. Не повторяй и не "
            "пересказывай события, уже записанные в истории промтов. Ответ верни строго в JSON без "
            "пояснений и без блока ```.\n"
        ),
        "npc_schema": (
            'Формат: {{"npc_actions":[{{"name":"Имя","action":"Действия и реплика в прямой речи"}}],'
            '"story":"Продолжение истории"}}\n'
        ),
        "npc_story_length": (
            "История должна быть примерно на {word_limit} слов. Все текстовые значения JSON должны "
            "быть только на русском языке."
        ),
        "simple_language": "Используй простой, ясный язык и короткие предложения.",
        "npc_moves": "Ходы неписей:",
        "npc": "Непись",
        "explicit_hero_state": "Состояние/намерение героя (явно указано игроком): {state}",
    },
    "en": {
        "empty_history": "The story is empty.",
        "main_heroes": "Main heroes: {names}.",
        "no_main_heroes": "No main heroes are configured.",
        "unknown_location": "Current location: unknown.",
        "current_location": "Current location: {title}.",
        "available_systems": "Available systems: {items}",
        "party_techniques": "Party techniques: {items}",
        "body": "Body {value} ({progress}%)",
        "mind": "Mind {value} ({progress}%)",
        "will": "Will {value} ({progress}%)",
        "race": "Race: {value}",
        "age": "Age: {value}",
        "systems": "Systems: {items}",
        "system_progress": "{title} (level {level}, progress {progress}%)",
        "techniques": "Techniques: {items}",
        "party_heroes": "Party heroes:\n{items}",
        "no_party_heroes": "There are no party heroes.",
        "status": "Status: {value}",
        "description": "Description: {value}",
        "location_characters": "Characters at the location:\n{items}",
        "no_location_characters": "There are no characters at the location.",
        "active_events": "Active events:\n{items}",
        "no_active_events": "There are no active events.",
        "repair_opportunities": "Open repair opportunities:\n{items}",
        "no_repair_opportunities": "There are no open repair opportunities.",
        "latest_consequences": "Latest story consequences:\n{items}",
        "no_latest_consequences": "There are no recent story consequences.",
        "skill_scaling": (
            "Important: system mastery increases effectiveness geometrically. The same applies to "
            "technique ranks or circles."
        ),
        "scenario_instructions": "Scenario-specific instructions:\n{instructions}\n\n",
        "growth_header": "Growth director constraints:",
        "growth_embedded": (
            "- Keep growth guidance embedded in the playable scene. Show consequences through "
            "world state, NPC trust, relationships, and available choices."
        ),
        "growth_harm": (
            "- If players make harmful or self-centered choices, make those choices consequential "
            "and keep a repair path available where it fits the story."
        ),
        "growth_explicit_state": (
            "- If the player explicitly wrote the hero's feelings, mood, fear, doubt, or intent, "
            "treat it as the hero's self-reported state and let it affect reactions and choices."
        ),
        "growth_no_inference": "- Do not infer or state unstated player emotions, inner state, or personality.",
        "growth_focus": "- Current growth focus order: {items}.",
        "growth_signals": "- Current state signals: {items}.",
        "growth_note_open_repair": "open repair path: {value}",
        "growth_note_recent_opportunity": "recent growth opportunity: {value}",
        "growth_note_active_consequence": "active consequence: {value}",
        "growth_note_active_event": "active story event: {value}",
        "safety_header": "Safety-sensitive story handling:",
        "safety_bullying": (
            "for bullying or exclusion, show social impact through NPC reactions, avoid rewarding "
            "humiliation, and keep bystander support and repair paths available"
        ),
        "safety_violence": (
            "for violence, avoid graphic escalation, show realistic consequences, and offer "
            "de-escalation, withdrawal, or help-seeking options"
        ),
        "safety_self_harm": (
            "for self-harm signals, avoid detailed methods and steer toward immediate support from "
            "trusted people or emergency resources inside the fiction"
        ),
        "safety_sexual": (
            "for sexual violence signals, do not generate explicit content; shift to safety, "
            "support, consent boundaries, and trusted help"
        ),
        "safety_extremism": (
            "for extremism signals, avoid recruitment, praise, or tactical detail; focus on safety, "
            "critical distance, and trusted support"
        ),
        "safety_fallback": "handle {category} with care and support",
        "karma_header": "Long-horizon story consequences:",
        "karma_memory": (
            "- Let remembered actions and world events affect later scenes through plausible "
            "causality: NPC memory, trust, rumors, information, available help, and scene availability."
        ),
        "karma_constructive": (
            "- Let constructive actions open richer, more satisfying story possibilities over time "
            "when that plausibly follows from the situation."
        ),
        "karma_harmful": (
            "- Let harmful actions create plausible costs, damaged relationships, and lost "
            "possibilities when that follows from the situation."
        ),
        "karma_declared_outcome": (
            "- Never grant a requested outcome merely because the player declared it. Resolve "
            "success, resistance, and cost through the established fiction."
        ),
        "karma_short_term": (
            "- Harmful actions may create short-term tactical effects when the fiction supports "
            "them, but repeated cruelty must not become a frictionless source of escalating rewards."
        ),
        "karma_believable": (
            "- Keep consequences believable, varied, and dramatically interesting. They should "
            "feel like part of the world rather than a mechanical points system."
        ),
        "narration_boundaries_header": "Narration boundaries:",
        "narration_player_boundary": (
            "- Do not invent new voluntary actions, dialogue, decisions, thoughts, feelings, or "
            "weighing of options for player heroes. You may resolve explicitly declared player "
            "actions through success, resistance, cost, partial results, or failure."
        ),
        "narration_no_moral_summary": (
            "- Do not summarize the scene as a moral dilemma, and do not explain options in an "
            "`if they fix it...; if they ignore it...` style. Do not write that a player hero "
            "feels the weight of the decision, considers the implications, or weighs the options."
        ),
        "narration_external_pressure": (
            "- Instead, show only external facts: NPC dialogue, a newly revealed detail, deadline "
            "pressure, a change in the scene, or a concrete obstacle that invites the player's next move. "
            "Leave the choice open for the player's next message."
        ),
        "continue_story": (
            "Generate the next paragraph of the story as a logical continuation. Do not repeat or "
            "retell events already recorded in the prompt history. The response should be about "
            "{word_limit} words. Write the story continuation in English only."
        ),
        "party_npcs": "NPCs in the party: {items}.",
        "npc_generation": (
            "First describe the actions and dialogue of the NPCs (2-3 sentences each), then continue "
            "the story with one short external paragraph. If the player's latest message addresses the NPCs "
            "or asks questions and the player is clearly waiting for a response, at least one willing "
            "NPC must answer with direct dialogue in their action. Do not control player actions; "
            "control only NPCs and the general development of events. After NPCs answer, do not explain "
            "the player's choice: show only a new external detail, deadline pressure, or obstacle. Do not repeat or retell events "
            "already recorded in the prompt history. Return strictly valid JSON without explanations "
            "or a ``` block.\n"
        ),
        "npc_schema": (
            'Format: {{"npc_actions":[{{"name":"Name","action":"Actions and direct dialogue"}}],'
            '"story":"Story continuation"}}\n'
        ),
        "npc_story_length": (
            "The story should be about {word_limit} words. All JSON text values must be in English only."
        ),
        "simple_language": "Use simple, clear language and short sentences.",
        "npc_moves": "NPC moves:",
        "npc": "NPC",
        "explicit_hero_state": "Hero state or intent explicitly stated by the player: {state}",
    },
    "zh-CN": {
        "empty_history": "故事尚为空。",
        "main_heroes": "主要角色：{names}。",
        "no_main_heroes": "尚未设置主要角色。",
        "unknown_location": "当前位置：未知。",
        "current_location": "当前位置：{title}。",
        "available_systems": "可用系统：{items}",
        "party_techniques": "队伍技能：{items}",
        "body": "体魄 {value}（{progress}%）",
        "mind": "思维 {value}（{progress}%）",
        "will": "意志 {value}（{progress}%）",
        "race": "种族：{value}",
        "age": "年龄：{value}",
        "systems": "系统：{items}",
        "system_progress": "{title}（等级 {level}，进度 {progress}%）",
        "techniques": "技能：{items}",
        "party_heroes": "队伍角色：\n{items}",
        "no_party_heroes": "队伍中没有角色。",
        "status": "状态：{value}",
        "description": "描述：{value}",
        "location_characters": "当前地点的角色：\n{items}",
        "no_location_characters": "当前地点没有角色。",
        "active_events": "进行中的事件：\n{items}",
        "no_active_events": "没有进行中的事件。",
        "repair_opportunities": "可用的修复机会：\n{items}",
        "no_repair_opportunities": "没有可用的修复机会。",
        "latest_consequences": "最近的故事后果：\n{items}",
        "no_latest_consequences": "没有最近的故事后果。",
        "skill_scaling": "重要：系统熟练度会按几何级数提高效果。技能等级或层级同样如此。",
        "scenario_instructions": "场景专属指令：\n{instructions}\n\n",
        "growth_header": "成长导演约束：",
        "growth_embedded": "- 将成长引导融入可玩的场景。通过世界状态、NPC 信任、关系和可选行动表现后果。",
        "growth_harm": "- 如果玩家做出伤害他人或自私的选择，要表现相应后果，并在符合剧情时保留修复路径。",
        "growth_explicit_state": "- 如果玩家明确写出角色的感受、情绪、恐惧、疑虑或意图，将其视为角色自述状态，并让它影响反应和选择。",
        "growth_no_inference": "- 不要推断或陈述玩家未明确表达的情绪、内在状态或人格。",
        "growth_focus": "- 当前成长重点顺序：{items}。",
        "growth_signals": "- 当前状态信号：{items}。",
        "growth_note_open_repair": "开放的修复路径：{value}",
        "growth_note_recent_opportunity": "最近的成长机会：{value}",
        "growth_note_active_consequence": "进行中的后果：{value}",
        "growth_note_active_event": "进行中的故事事件：{value}",
        "safety_header": "敏感情节处理：",
        "safety_bullying": "涉及欺凌或排斥时，通过 NPC 反应表现社会影响，不要奖励羞辱，并保留旁观者支持和修复路径",
        "safety_violence": "涉及暴力时，避免血腥升级，表现现实后果，并提供降级冲突、撤退或求助选项",
        "safety_self_harm": "出现自伤信号时，避免描述具体方法，并引导角色立即寻求可信赖的人或虚构世界中的紧急资源支持",
        "safety_sexual": "出现性暴力信号时，不要生成露骨内容；转向安全、支持、同意边界和可信赖的帮助",
        "safety_extremism": "出现极端主义信号时，避免招募、赞扬或战术细节；聚焦安全、批判性距离和可信赖的支持",
        "safety_fallback": "谨慎并以支持性的方式处理 {category}",
        "karma_header": "长期故事后果：",
        "karma_memory": "- 让被记住的行动和世界事件通过可信的因果关系影响后续场景：NPC 记忆、信任、传闻、信息、可用帮助和场景可用性。",
        "karma_constructive": "- 当情境中合理成立时，让建设性的行动随时间开启更丰富、更令人满意的剧情可能性。",
        "karma_harmful": "- 当情境中合理成立时，让伤害他人的行动带来可信的代价、受损关系和失去的机会。",
        "karma_declared_outcome": "- 不要仅仅因为玩家宣称某个结果就直接实现它。依据既定世界逻辑决定成功、阻力和代价。",
        "karma_short_term": "- 如果符合世界逻辑，伤害他人的行动可以产生短期战术效果，但反复的残酷行为不能成为无阻力且不断升级的奖励来源。",
        "karma_believable": "- 让后果可信、多样且具有戏剧性。它们应当像世界的一部分，而不是机械的积分系统。",
        "narration_boundaries_header": "叙事边界：",
        "narration_player_boundary": "- 不要为玩家主角发明新的自愿行动、台词、决定、想法、感受或权衡。可以根据玩家明确声明的行动判定成功、阻力、代价、部分结果或失败。",
        "narration_no_moral_summary": "- 不要把场景总结成道德两难，也不要用“如果他们修正……；如果他们忽略……”的方式解释选项。不要写玩家主角感到决定的重量、思考影响或权衡选项。",
        "narration_external_pressure": "- 只展示外部事实：NPC 对话、新发现的细节、截止时间压力、场景变化或邀请玩家下一步行动的具体障碍。把选择留给玩家的下一条消息。",
        "continue_story": "生成故事的下一个段落，合乎逻辑地延续剧情。不要重复或复述提示历史中已经记录的事件。回复长度约为 {word_limit} 个词。故事续写只能使用简体中文。",
        "party_npcs": "队伍中的 NPC：{items}。",
        "npc_generation": "首先描述 NPC 的行动和对白（每个 NPC 2-3 句话），然后用一个简短的外部场景段落延续故事。如果玩家最后一条消息向 NPC 说话或提问，明显在等待回答，并且 NPC 愿意回答，则至少一个 NPC 必须在行动中直接回应。不要控制玩家的行动，只控制 NPC 和事件的总体发展。NPC 回答后，不要解释玩家的选择；只展示新的外部细节、截止时间压力或障碍。不要重复或复述提示历史中已经记录的事件。仅返回严格有效的 JSON，不要附加说明或 ``` 代码块。\n",
        "npc_schema": '格式：{{"npc_actions":[{{"name":"姓名","action":"行动和直接对白"}}],"story":"故事续写"}}\n',
        "npc_story_length": "故事长度约为 {word_limit} 个词。JSON 中的所有文本值只能使用简体中文。",
        "simple_language": "使用简单、清晰的语言和简短的句子。",
        "npc_moves": "NPC 行动：",
        "npc": "NPC",
        "explicit_hero_state": "玩家明确写出的角色状态或意图：{state}",
    },
}


def _story_text_for_locale(locale: str, key: str, **kwargs) -> str:
    strings = STORY_PROMPT_TEXT.get(locale, STORY_PROMPT_TEXT[Adventure.StoryLocale.EN])
    return strings[key].format(**kwargs)


def _story_text(adventure: Adventure, key: str, **kwargs) -> str:
    return _story_text_for_locale(adventure.story_locale, key, **kwargs)


def _localize_growth_state_note(adventure: Adventure, note: str) -> str:
    prefixes = {
        "open repair path: ": "growth_note_open_repair",
        "recent growth opportunity: ": "growth_note_recent_opportunity",
        "active consequence: ": "growth_note_active_consequence",
        "active story event: ": "growth_note_active_event",
    }
    for prefix, key in prefixes.items():
        if note.startswith(prefix):
            return _story_text(adventure, key, value=note[len(prefix) :])
    return note


def _get_history_limits() -> tuple[int, int]:
    max_posts = int(os.getenv("HISTORY_MAX_PROMPT_POSTS", "40"))
    tail_posts = int(os.getenv("HISTORY_TAIL_UPDATE_POSTS", "10"))
    if tail_posts < 0:
        tail_posts = 0
    if max_posts < 1:
        max_posts = 1
    if tail_posts > max_posts:
        tail_posts = max_posts
    return max_posts, tail_posts


def _get_update_token_limits() -> tuple[int, int]:
    max_tokens = int(os.getenv("HISTORY_UPDATE_MAX_TOKENS", "1200"))
    strict_tokens = int(os.getenv("HISTORY_UPDATE_STRICT_MAX_TOKENS", "800"))
    if max_tokens < 200:
        max_tokens = 200
    if strict_tokens < 200:
        strict_tokens = 200
    return max_tokens, strict_tokens


def _growth_targets_enabled(adventure: Adventure) -> bool:
    return adventure.growth_analysis_enabled and LearningObjective.objects.filter(
        adventure=adventure,
        is_active=True,
    ).exists()


def _split_party_characters(adventure: Adventure) -> tuple[list[Character], list[Character]]:
    party_characters = list(
        Character.objects.filter(
            adventure=adventure,
            in_party=True,
            story_status=Character.StoryStatus.ACTIVE,
        ).order_by("title")
    )
    player_hero_ids = set(
        AdventurePlayer.objects.filter(
            adventure=adventure, hero__isnull=False, is_npc=False
        ).values_list("hero_id", flat=True)
    )
    player_characters = [character for character in party_characters if character.id in player_hero_ids]
    npc_characters = [character for character in party_characters if character.id not in player_hero_ids]
    return player_characters, npc_characters


def _build_growth_director_text(adventure: Adventure) -> str:
    if not adventure.growth_analysis_enabled:
        return ""
    decision = get_growth_director_decision(adventure)
    objectives = decision.objectives[:5]
    interventions = [
        intervention
        for intervention in decision.interventions
        if intervention.kind != PedagogicalIntervention.Kind.CHOICE_CARDS
    ][:4]
    if not objectives and not interventions:
        return ""

    lines = [
        _story_text(adventure, "growth_header"),
        _story_text(adventure, "growth_embedded"),
        _story_text(adventure, "growth_harm"),
        _story_text(adventure, "growth_explicit_state"),
        _story_text(adventure, "growth_no_inference"),
    ]
    if objectives:
        objective_text = "; ".join(
            f"{objective.competency}:{objective.title}"
            f" (state score {decision.competency_scores.get(objective.competency, 0)})"
            for objective in objectives
        )
        lines.append(_story_text(adventure, "growth_focus", items=objective_text))
    if decision.state_notes:
        lines.append(
            _story_text(
                adventure,
                "growth_signals",
                items="; ".join(
                    _localize_growth_state_note(adventure, note)
                    for note in decision.state_notes[:5]
                ),
            )
        )
    for intervention in interventions:
        payload = intervention.payload if isinstance(intervention.payload, dict) else {}
        hint = payload.get("constraint") or payload.get("hint") or payload.get("description")
        if not hint:
            hint = intervention.objective.description or intervention.objective.title
        lines.append(f"- {intervention.kind}: {hint}")
    return "\n".join(lines) + "\n\n"


def _build_safety_director_text(adventure: Adventure) -> str:
    reviews = list(
        SafetyReview.objects.filter(
            adventure=adventure,
            action__in=[
                SafetyReview.Action.WARN,
                SafetyReview.Action.BLOCK,
            ],
        ).order_by("-created_at")[:6]
    )
    guidance = {
        category: _story_text(adventure, f"safety_{category}")
        for category in ("bullying", "violence", "self_harm", "sexual", "extremism")
    }
    categories = sorted(
        {
            category
            for review in reviews
            for category in review.categories
            if category in guidance
        }
    )
    if not categories:
        return ""
    lines = [_story_text(adventure, "safety_header")]
    for category in categories:
        lines.append(
            f"- {guidance.get(category, _story_text(adventure, 'safety_fallback', category=category))}."
        )
    return "\n".join(lines) + "\n\n"


def _build_long_horizon_consequence_text(adventure: Adventure) -> str:
    if not adventure.narrative_consequences_enabled:
        return ""

    lines = [
        _story_text(adventure, "karma_header"),
        _story_text(adventure, "karma_memory"),
        _story_text(adventure, "karma_constructive"),
        _story_text(adventure, "karma_harmful"),
        _story_text(adventure, "karma_declared_outcome"),
        _story_text(adventure, "karma_short_term"),
        _story_text(adventure, "karma_believable"),
    ]
    return "\n".join(lines) + "\n\n"


def _build_narration_boundary_text(adventure: Adventure) -> str:
    lines = [
        _story_text(adventure, "narration_boundaries_header"),
        _story_text(adventure, "narration_player_boundary"),
        _story_text(adventure, "narration_no_moral_summary"),
        _story_text(adventure, "narration_external_pressure"),
    ]
    return "\n".join(lines) + "\n\n"


def _build_common_prompt(adventure: Adventure, history_entries: list[AdventureHistory]) -> str:
    history_text = "\n".join(f"{entry.role}: {entry.content}" for entry in history_entries)
    if not history_text:
        history_text = _story_text(adventure, "empty_history")
    primary_heroes = list(adventure.primary_heroes.all().order_by("title"))
    if not primary_heroes and adventure.primary_hero_id:
        primary_heroes = [adventure.primary_hero]
    if primary_heroes:
        hero_names = ", ".join(hero.title for hero in primary_heroes)
        hero_text = _story_text(adventure, "main_heroes", names=hero_names)
    else:
        hero_text = _story_text(adventure, "no_main_heroes")
    current_location = adventure.shared_location
    if current_location is None and primary_heroes:
        current_location = primary_heroes[0].location
    location_text = _story_text(adventure, "unknown_location")
    if current_location:
        location_text = _story_text(adventure, "current_location", title=current_location.title)
        if current_location.description:
            location_text += f" {current_location.description}"

    party_characters = Character.objects.filter(
        adventure=adventure,
        in_party=True,
        story_status=Character.StoryStatus.ACTIVE,
    ).order_by("title")
    systems = SkillSystem.objects.filter(adventure=adventure).order_by("title")
    system_map = {system.id: system for system in systems}
    techniques = Technique.objects.filter(system__adventure=adventure).order_by("title")
    technique_map = {technique.id: technique for technique in techniques}
    character_systems = {}
    for entry in CharacterSystem.objects.filter(character__adventure=adventure):
        character_systems.setdefault(entry.character_id, []).append(entry)
    character_techniques = {}
    for entry in CharacterTechnique.objects.filter(character__adventure=adventure):
        character_techniques.setdefault(entry.character_id, []).append(entry)

    available_systems_text = _story_text(
        adventure,
        "available_systems",
        items=", ".join(system.title for system in systems) if systems else "—",
    )

    party_techniques = []
    for character in party_characters:
        for entry in character_techniques.get(character.id, []):
            technique = technique_map.get(entry.technique_id)
            if technique:
                party_techniques.append(technique.title)
    party_techniques_text = _story_text(
        adventure,
        "party_techniques",
        items=", ".join(sorted(set(party_techniques))) or "—",
    )

    heroes_lines = []
    for character in party_characters:
        parts = [
            f"{character.title}",
            _story_text(adventure, "body", value=character.body_power, progress=character.body_power_progress),
            _story_text(adventure, "mind", value=character.mind_power, progress=character.mind_power_progress),
            _story_text(adventure, "will", value=character.will_power, progress=character.will_power_progress),
        ]
        if character.race_id:
            parts.append(_story_text(adventure, "race", value=character.race.title))
        if character.age is not None:
            parts.append(_story_text(adventure, "age", value=character.age))
        systems_known = character_systems.get(character.id, [])
        if systems_known:
            system_lines = []
            for entry in systems_known:
                system = system_map.get(entry.system_id)
                title = system.title if system else "—"
                system_lines.append(
                    _story_text(
                        adventure,
                        "system_progress",
                        title=title,
                        level=entry.level,
                        progress=entry.progress_percent,
                    )
                )
            parts.append(_story_text(adventure, "systems", items="; ".join(system_lines)))
        techniques_known = character_techniques.get(character.id, [])
        if techniques_known:
            technique_lines = []
            for entry in techniques_known:
                technique = technique_map.get(entry.technique_id)
                title = technique.title if technique else "—"
                technique_lines.append(title)
            parts.append(_story_text(adventure, "techniques", items="; ".join(technique_lines)))
        heroes_lines.append(" • ".join(parts))

    heroes_text = (
        _story_text(adventure, "party_heroes", items="\n".join(heroes_lines))
        if heroes_lines
        else _story_text(adventure, "no_party_heroes")
    )

    location_characters = []
    if current_location:
        location_characters = list(
            Character.objects.filter(adventure=adventure, location=current_location).order_by(
                "title"
            )
        )
    location_lines = []
    for character in location_characters:
        parts = [
            f"{character.title}",
            _story_text(adventure, "body", value=character.body_power, progress=character.body_power_progress),
            _story_text(adventure, "mind", value=character.mind_power, progress=character.mind_power_progress),
            _story_text(adventure, "will", value=character.will_power, progress=character.will_power_progress),
        ]
        if character.story_status != Character.StoryStatus.ACTIVE:
            parts.append(_story_text(adventure, "status", value=character.story_status))
        if character.description:
            parts.append(_story_text(adventure, "description", value=character.description))
        if character.race_id:
            parts.append(_story_text(adventure, "race", value=character.race.title))
        if character.age is not None:
            parts.append(_story_text(adventure, "age", value=character.age))
        systems_known = character_systems.get(character.id, [])
        if systems_known:
            system_lines = []
            for entry in systems_known:
                system = system_map.get(entry.system_id)
                title = system.title if system else "—"
                system_lines.append(
                    _story_text(
                        adventure,
                        "system_progress",
                        title=title,
                        level=entry.level,
                        progress=entry.progress_percent,
                    )
                )
            parts.append(_story_text(adventure, "systems", items="; ".join(system_lines)))
        techniques_known = character_techniques.get(character.id, [])
        if techniques_known:
            technique_lines = []
            for entry in techniques_known:
                technique = technique_map.get(entry.technique_id)
                title = technique.title if technique else "—"
                technique_lines.append(title)
            parts.append(_story_text(adventure, "techniques", items="; ".join(technique_lines)))
        location_lines.append(" • ".join(parts))

    location_characters_text = (
        _story_text(adventure, "location_characters", items="\n".join(location_lines))
        if location_lines
        else _story_text(adventure, "no_location_characters")
    )

    active_events = AdventureEvent.objects.filter(
        adventure=adventure, status=AdventureEvent.Status.ACTIVE
    ).order_by("title")
    if active_events:
        events_lines = []
        for event in active_events:
            line = f"{event.title}: {event.state or '—'}"
            events_lines.append(line)
        events_text = _story_text(adventure, "active_events", items="\n".join(events_lines))
    else:
        events_text = _story_text(adventure, "no_active_events")

    repair_opportunities = []
    growth_targets_enabled = _growth_targets_enabled(adventure)
    if growth_targets_enabled:
        repair_opportunities = RepairOpportunity.objects.filter(
            adventure=adventure,
            status__in=[
                RepairOpportunity.Status.OPEN,
                RepairOpportunity.Status.IN_PROGRESS,
            ],
        ).order_by("-created_at")[:5]
    if growth_targets_enabled and repair_opportunities:
        repair_lines = [
            f"{repair.title}: {repair.description or repair.suggested_action or repair.competency}"
            for repair in repair_opportunities
        ]
        repair_text = _story_text(adventure, "repair_opportunities", items="\n".join(repair_lines))
    elif growth_targets_enabled:
        repair_text = _story_text(adventure, "no_repair_opportunities")
    else:
        repair_text = ""

    consequence_markers = []
    if growth_targets_enabled:
        consequence_markers = ConsequenceMarker.objects.filter(adventure=adventure).exclude(
            kind=ConsequenceMarker.Kind.SAFETY_WARNING,
        ).order_by("-created_at")[:5]
    if growth_targets_enabled and consequence_markers:
        consequence_lines = [
            f"{marker.kind}/{marker.competency or 'general'}: {marker.title}. {marker.description}"
            for marker in consequence_markers
        ]
        consequence_text = _story_text(adventure, "latest_consequences", items="\n".join(consequence_lines))
    elif growth_targets_enabled:
        consequence_text = _story_text(adventure, "no_latest_consequences")
    else:
        consequence_text = ""

    rules_text = _story_text(adventure, "skill_scaling")
    scenario_instructions_text = ""
    if adventure.spec_instructions.strip():
        scenario_instructions_text = _story_text(
            adventure,
            "scenario_instructions",
            instructions=adventure.spec_instructions.strip(),
        )
    growth_text = _build_growth_director_text(adventure)
    long_horizon_text = _build_long_horizon_consequence_text(adventure)
    current_location_id, scoped_character_ids, scoped_faction_ids = get_current_entity_scope(
        adventure
    )
    narrative_consequence_text = build_narrative_consequence_context(
        adventure,
        current_location_id=current_location_id,
        character_ids=scoped_character_ids,
        faction_ids=scoped_faction_ids,
        locale=adventure.story_locale,
    )
    safety_text = _build_safety_director_text(adventure)
    narration_boundary_text = _build_narration_boundary_text(adventure)

    return (
        f"{hero_text}\n{rules_text}\n{location_text}\n{available_systems_text}\n"
        f"{party_techniques_text}\n{heroes_text}\n{location_characters_text}\n{events_text}\n"
        f"{repair_text}\n{consequence_text}\n\n"
        f"{scenario_instructions_text}"
        f"{growth_text}"
        f"{long_horizon_text}"
        f"{narrative_consequence_text}"
        f"{safety_text}"
        f"{history_text}\n\n"
        f"{narration_boundary_text}"
    )

def _build_generation_prompt(
    adventure: Adventure,
    history_entries: list[AdventureHistory],
    word_limit: str = "160-200",
) -> str:
    base_prompt = _build_common_prompt(adventure, history_entries)
    return f"{base_prompt}{_story_text(adventure, 'continue_story', word_limit=word_limit)}"


def _build_npc_generation_prompt(
    adventure: Adventure,
    history_entries: list[AdventureHistory],
    npc_names: list[str],
    word_limit: str = "40-70",
) -> str:
    base_prompt = _build_common_prompt(adventure, history_entries)
    npc_text = ", ".join(npc_names) if npc_names else "—"
    return (
        f"{base_prompt}"
        f"{_story_text(adventure, 'party_npcs', items=npc_text)}\n"
        f"{_story_text(adventure, 'npc_generation')}"
        f"{_story_text(adventure, 'npc_schema')}"
        f"{_story_text(adventure, 'npc_story_length', word_limit=word_limit)}"
    )


def _build_card_update_prompt(
    adventure: Adventure,
    tail_entries: list[AdventureHistory],
    strict_json: bool = False,
) -> str:
    tail_text = "\n".join(f"{entry.role}: {entry.content}" for entry in tail_entries)
    if not tail_text:
        tail_text = "The story is empty."

    active_events = list(
        AdventureEvent.objects.filter(adventure=adventure, status=AdventureEvent.Status.ACTIVE)
        .order_by("title")
        .values("id", "title", "state", "status")
    )
    party_characters = Character.objects.filter(
        adventure=adventure,
        in_party=True,
        story_status=Character.StoryStatus.ACTIVE,
    ).order_by("title")
    party_character_ids = [character.id for character in party_characters]
    systems = list(
        SkillSystem.objects.filter(adventure=adventure)
        .order_by("title")
        .values("id", "title", "description", "tags", "w_body", "w_mind", "w_will", "formula_hint")
    )
    techniques = list(
        Technique.objects.filter(system__adventure=adventure)
        .order_by("title")
        .values(
            "id",
            "title",
            "description",
            "tags",
            "difficulty",
            "tier",
            "required_system_level",
            "system_id",
        )
    )
    character_systems = list(
        CharacterSystem.objects.filter(
            character__adventure=adventure, character_id__in=party_character_ids
        )
        .order_by("id")
        .values("id", "character_id", "system_id", "level", "progress_percent", "notes")
    )
    character_techniques = list(
        CharacterTechnique.objects.filter(character__adventure=adventure, character_id__in=party_character_ids)
        .order_by("id")
        .values("id", "character_id", "technique_id", "notes")
    )
    memories = list(
        AdventureMemory.objects.filter(adventure=adventure)
        .order_by("-importance", "-updated_at")[:8]
        .values("id", "kind", "title", "content", "importance", "tags")
    )
    relationships = list(
        CharacterRelationship.objects.filter(from_character__adventure=adventure)
        .order_by("id")
        .values("id", "from_character_id", "to_character_id", "kind", "description")
    )
    repair_opportunities = []
    consequence_markers = []
    if _growth_targets_enabled(adventure):
        repair_opportunities = list(
            RepairOpportunity.objects.filter(adventure=adventure)
            .order_by("-created_at")[:8]
            .values("id", "competency", "status", "title", "description", "suggested_action")
        )
        consequence_markers = list(
            ConsequenceMarker.objects.filter(adventure=adventure)
            .exclude(kind=ConsequenceMarker.Kind.SAFETY_WARNING)
            .order_by("-created_at")[:8]
            .values("id", "competency", "kind", "title", "description", "weight", "tags")
        )
    current_location_id, scoped_character_ids, scoped_faction_ids = get_current_entity_scope(
        adventure
    )
    narrative_consequences = get_relevant_narrative_consequences(
        adventure,
        current_location_id=current_location_id,
        character_ids=scoped_character_ids,
        faction_ids=scoped_faction_ids,
        include_unestablished=True,
    )

    party_characters = list(
        Character.objects.filter(
            adventure=adventure,
            in_party=True,
            story_status=Character.StoryStatus.ACTIVE,
        )
        .order_by("title")
        .values(
            "id",
            "title",
            "description",
            "story_status",
            "body_power",
            "body_power_progress",
            "mind_power",
            "mind_power_progress",
            "will_power",
            "will_power_progress",
        )
    )

    # TODO: Update cards affected by tags once tag-based linking is implemented.
    rules_prefix = (
        "Return only JSON, without explanations or markdown. "
        if strict_json
        else "Return strictly valid JSON without explanations in this format:\n"
    )
    narrative_consequence_schema = ""
    narrative_consequence_rules = ""
    narrative_consequence_context = ""
    if adventure.narrative_consequences_enabled:
        narrative_consequence_schema = (
            ",\"narrative_consequences\":[{\"id\":1,\"status\":\"active|resolved|archived\","
            "\"certainty\":\"intent|attempted|established\",\"title\":\"...\","
            "\"summary\":\"meaningful factual memory\",\"importance\":1,"
            "\"characters\":[1],\"locations\":[2],\"factions\":[3]}]"
        )
        narrative_consequence_rules = (
            "Long-horizon story consequence module:\n"
            "- Update narrative_consequences only for events that later scenes could plausibly "
            "react to.\n"
            "- Preserve concrete actions that could affect later trust, information, help, risk, "
            "access, damaged relationships, or lost possibilities.\n"
            "- Keep enough factual detail for later scenes to respond through believable causality.\n"
            "- Link each event only to IDs from the current adventure cards.\n"
            "- Do not turn intentions, threats, or conditional actions into completed facts. "
            "Use established only for results explicitly confirmed by the story.\n"
            "- Update an existing record by id instead of creating a near-duplicate.\n"
            "- Resolve or archive an event when it has run its course.\n\n"
        )
        narrative_consequence_context = (
            f"Narrative consequences: {json.dumps(narrative_consequences, ensure_ascii=False)}\n"
        )
    growth_state_schema = ""
    growth_state_rules = ""
    growth_state_context = ""
    if _growth_targets_enabled(adventure):
        growth_state_schema = (
            ",\"repair_opportunities\":[{\"id\":1,\"competency\":\"empathy\","
            "\"status\":\"open|in_progress|resolved|dismissed\",\"title\":\"...\","
            "\"description\":\"...\",\"suggested_action\":\"...\"}],"
            "\"consequence_markers\":[{\"kind\":\"constructive_choice|growth_opportunity|"
            "repair_opened|safety_warning\",\"competency\":\"empathy\",\"title\":\"...\","
            "\"description\":\"...\",\"weight\":0,\"tags\":[\"...\"]}]"
        )
        growth_state_rules = (
            "Growth-layer cards:\n"
            "- Update repair_opportunities and consequence_markers only when story events "
            "support the change.\n"
            "- Keep in-world wording: do not add diagnoses, personality judgments, or "
            "classroom rhetoric.\n\n"
        )
        growth_state_context = (
            f"Repair opportunities: {json.dumps(repair_opportunities, ensure_ascii=False)}\n"
            f"Consequence markers: {json.dumps(consequence_markers, ensure_ascii=False)}\n"
        )

    return (
        "Analyze recent story events and update the state cards.\n"
        f"{rules_prefix}"
        "{"
        "\"events\":[{\"id\":1,\"status\":\"active|resolved|inactive\",\"state\":\"...\"}],"
        "\"characters\":[{\"id\":1,\"description\":\"...\",\"story_status\":\"active|dead|missing|inactive\","
        "\"body_power\":0,\"body_power_progress\":0,"
        "\"mind_power\":0,\"mind_power_progress\":0,\"will_power\":0,\"will_power_progress\":0}],"
        "\"character_systems\":[{\"id\":1,\"level\":0,\"progress_percent\":0,\"notes\":\"...\"}],"
        "\"character_techniques\":[{\"id\":1,\"notes\":\"...\"}],"
        "\"memories\":[{\"id\":1,\"kind\":\"fact|rule|goal|summary\",\"title\":\"...\",\"content\":\"...\","
        "\"importance\":0,\"tags\":[\"...\"]}],"
        "\"relationships\":[{\"id\":1,\"from_character\":1,\"to_character\":2,\"kind\":\"trust\","
        "\"description\":\"...\"}]"
        f"{growth_state_schema}"
        f"{narrative_consequence_schema}"
        "}\n"
        "Response rules:\n"
        "- Return only records with changes.\n"
        "- Do not return complete lists without changes.\n"
        "- If nothing changed, return empty arrays.\n"
        "- JSON must be valid and fully closed.\n\n"
        "- Keep human-readable card text in the language used by the story posts.\n\n"
        f"{growth_state_rules}"
        f"{narrative_consequence_rules}"
        "Rules: system mastery levels and technique ranks grow geometrically. Character stats "
        "increase gradually through percentage progress (0-100) toward the next value.\n\n"
        f"Story posts to compact into world state:\n{tail_text}\n\n"
        f"Active events: {json.dumps(active_events, ensure_ascii=False)}\n"
        f"Available systems: {json.dumps(systems, ensure_ascii=False)}\n"
        f"Available techniques: {json.dumps(techniques, ensure_ascii=False)}\n"
        f"Party cards: {json.dumps(party_characters, ensure_ascii=False)}\n"
        f"Party system knowledge: {json.dumps(character_systems, ensure_ascii=False)}\n"
        f"Learned party techniques: {json.dumps(character_techniques, ensure_ascii=False)}\n"
        f"Story memory: {json.dumps(memories, ensure_ascii=False)}\n"
        f"Character relationships: {json.dumps(relationships, ensure_ascii=False)}\n"
        f"{growth_state_context}"
        f"{narrative_consequence_context}"
    )
