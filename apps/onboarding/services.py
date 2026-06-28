import logging
import uuid

from django.core.cache import cache

logger = logging.getLogger(__name__)

DRAFT_CACHE_PREFIX = "onboarding:draft:"
DRAFT_TTL_SECONDS = 86400  # 24 hours


class DraftOnboardingService:
    @classmethod
    def get_draft(cls, draft_token: str) -> dict:
        if not draft_token:
            return cls._empty_draft_structure()

        key = f"{DRAFT_CACHE_PREFIX}{draft_token}"
        data = cache.get(key)
        if not data:
            return cls._empty_draft_structure()
        return data

    @classmethod
    def init_or_update_draft(cls, draft_token: str | None, update_fields: dict) -> tuple[str, dict]:
        token = draft_token if draft_token else str(uuid.uuid4())
        key = f"{DRAFT_CACHE_PREFIX}{token}"

        current_draft = cache.get(key)
        if not current_draft:
            current_draft = cls._empty_draft_structure()

        for field_name, field_value in update_fields.items():
            current_draft[field_name] = field_value

        cache.set(key, current_draft, timeout=DRAFT_TTL_SECONDS)
        logger.debug("Draft updated in Redis cache for token [%s]", token)
        return token, current_draft

    @classmethod
    def add_work(cls, draft_token: str, work_item: dict) -> dict:
        draft = cls.get_draft(draft_token)
        works_list = draft.get("works", [])
        works_list.append(work_item)
        _, updated_draft = cls.init_or_update_draft(draft_token, {"works": works_list})
        return updated_draft

    @classmethod
    def remove_work(cls, draft_token: str, work_id: str) -> dict:
        draft = cls.get_draft(draft_token)
        works_list = [w for w in draft.get("works", []) if str(w.get("id")) != str(work_id)]
        _, updated_draft = cls.init_or_update_draft(draft_token, {"works": works_list})
        return updated_draft

    @classmethod
    def clear_draft(cls, draft_token: str) -> None:
        if draft_token:
            cache.delete(f"{DRAFT_CACHE_PREFIX}{draft_token}")
            logger.info("Draft cache purged for finalized token [%s]", draft_token)

    @staticmethod
    def _empty_draft_structure() -> dict:
        return {
            "personal_info": {},
            "supplementary_info": {},
            "works": [],
        }
