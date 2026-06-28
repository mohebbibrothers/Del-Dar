import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

TEMP_MOBILE_VERIFIED_PREFIX = "user_temp_verified_mobile:"
TEMP_MOBILE_TTL_SECONDS = 3600  # 1 hour


class DashboardProfileService:
    @classmethod
    def mark_mobile_as_verified(cls, user_id: int, new_mobile: str) -> None:
        key = f"{TEMP_MOBILE_VERIFIED_PREFIX}{user_id}"
        cache.set(key, new_mobile, timeout=TEMP_MOBILE_TTL_SECONDS)
        logger.info("Temporarily cached verified mobile [%s] for user ID %s", new_mobile, user_id)

    @classmethod
    def is_mobile_change_verified(cls, user_id: int, target_mobile: str) -> bool:
        key = f"{TEMP_MOBILE_VERIFIED_PREFIX}{user_id}"
        cached_mobile = cache.get(key)
        return cached_mobile == target_mobile

    @classmethod
    def clear_verified_mobile_cache(cls, user_id: int) -> None:
        cache.delete(f"{TEMP_MOBILE_VERIFIED_PREFIX}{user_id}")
