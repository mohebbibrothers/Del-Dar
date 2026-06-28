import logging
import secrets

from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 120


class OTPService:
    @staticmethod
    def generate_otp() -> str:
        return f"{secrets.randbelow(10000):04d}"

    @classmethod
    def set_otp(cls, mobile: str, code: str, purpose: str = "onboarding") -> None:
        cache_key = cls._get_cache_key(mobile, purpose)
        cache.set(cache_key, code, timeout=OTP_TTL_SECONDS)
        logger.info("Generated OTP [%s] for mobile %s with purpose '%s'", code, mobile, purpose)

    @classmethod
    def get_otp(cls, mobile: str, purpose: str = "onboarding") -> str | None:
        cache_key = cls._get_cache_key(mobile, purpose)
        return cache.get(cache_key)

    @classmethod
    def verify_otp(cls, mobile: str, code: str, purpose: str = "onboarding") -> bool:
        cached_code = cls.get_otp(mobile, purpose)
        if cached_code and cached_code == code:
            cache.delete(cls._get_cache_key(mobile, purpose))
            return True
        return False

    @staticmethod
    def _get_cache_key(mobile: str, purpose: str) -> str:
        return f"otp:{purpose}:{mobile}"
