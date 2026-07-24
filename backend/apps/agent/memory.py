import json
from django.core.cache import cache

# inactivity-based expiry rather than a hard wall — feels more natural for a demo
SHORT_TERM_TTL = 3600
MAX_TURNS = 20


class ShortTermMemory:
    @staticmethod
    def _key(session_id: str) -> str:
        return f'agent:session:{session_id}'

    @staticmethod
    def get(session_id: str) -> list:
        raw = cache.get(ShortTermMemory._key(session_id))
        return json.loads(raw) if raw else []

    @staticmethod
    def append(session_id: str, messages: list):
        key = ShortTermMemory._key(session_id)
        existing = ShortTermMemory.get(session_id)
        combined = existing + messages
        # *2 because every turn contributes two messages (user + assistant)
        trimmed = combined[-(MAX_TURNS * 2):]
        cache.set(key, json.dumps(trimmed), SHORT_TERM_TTL)

    @staticmethod
    def clear(session_id: str):
        cache.delete(ShortTermMemory._key(session_id))

    @staticmethod
    def get_session_list(user_id: str) -> list:
        # would use a redis sorted set keyed by user_id in prod — skipped to keep the demo focused
        return []


class LongTermMemory:
    @staticmethod
    def get(user) -> dict:
        from .models import UserMemory
        mem = UserMemory.for_user(user)
        return mem.preferences

    @staticmethod
    def update(user, updates: dict):
        from .models import UserMemory
        mem = UserMemory.for_user(user)
        mem.preferences.update(updates)
        mem.save(update_fields=['preferences', 'updated_at'])

    @staticmethod
    def format_for_system_prompt(user) -> str:
        prefs = LongTermMemory.get(user)
        if not prefs:
            return ""
        lines = ["User preferences (learned from past conversations):"]
        for k, v in prefs.items():
            lines.append(f"  - {k}: {v}")
        return "\n".join(lines)
