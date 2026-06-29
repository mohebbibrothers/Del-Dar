import logging
from celery import shared_task
from .client import SMS_OTP_PATTERN, SMS_WELCOME_PATTERN, IranPayamakClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_otp_sms_task(self, mobile: str, otp_code: str):
    logger.info("Celery task initiated: sending OTP to %s", mobile)
    attributes = {"code": str(otp_code)}
    success = IranPayamakClient.send_pattern(
        recipient=mobile, pattern_code=SMS_OTP_PATTERN, attributes=attributes
    )
    if not success:
        if getattr(self.request, "is_eager", False):
            logger.error(
                "[EAGER TASK FALLBACK] External SMS gateway delivery failed for mobile %s. Eager mode prevented crash. OTP Code was [%s]",
                mobile,
                otp_code,
            )
            return False
        logger.warning("Retrying OTP delivery for %s", mobile)
        raise self.retry()
    return True


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_welcome_sms_task(self, mobile: str):
    logger.info("Celery task initiated: sending Welcome SMS to %s", mobile)
    success = IranPayamakClient.send_pattern(
        recipient=mobile, pattern_code=SMS_WELCOME_PATTERN, attributes={}
    )
    if not success:
        if getattr(self.request, "is_eager", False):
            logger.error(
                "[EAGER TASK FALLBACK] External Welcome SMS delivery failed for mobile %s. Eager mode prevented crash",
                mobile,
            )
            return False
        logger.warning("Retrying Welcome SMS delivery for %s", mobile)
        raise self.retry()
    return True
