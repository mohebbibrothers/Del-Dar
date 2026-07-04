import logging

from celery import shared_task

from .client import SMS_OTP_PATTERN, SMS_WELCOME_PATTERN, IranPayamakClient

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_otp_sms_task(self, mobile: str, otp_code: str, attempt: int = 1):
    logger.info("SMS task [%s/%s]: sending OTP to %s", attempt, 3, mobile)
    attributes = {"code": str(otp_code)}
    success = IranPayamakClient.send_pattern(
        recipient=mobile, pattern_code=SMS_OTP_PATTERN, attributes=attributes
    )
    if not success:
        if attempt < 3:
            logger.warning(
                "SMS gateway failed for %s. Retrying in 5s (attempt %s/%s)",
                mobile,
                attempt + 1,
                3,
            )
            return send_otp_sms_task.apply_async(
                args=[mobile, otp_code],
                kwargs={"attempt": attempt + 1},
                countdown=5,
            )
        logger.error(
            "SMS gateway failed after 3 attempts for mobile %s. OTP Code was [%s]. "
            "Check IranPayamak pattern approval and API key validity.",
            mobile,
            otp_code,
        )
        return False
    logger.info("SMS successfully delivered to %s", mobile)
    return True


@shared_task(bind=True)
def send_welcome_sms_task(self, mobile: str, attempt: int = 1):
    logger.info("Welcome SMS task [%s/%s]: sending to %s", attempt, 3, mobile)
    success = IranPayamakClient.send_pattern(
        recipient=mobile, pattern_code=SMS_WELCOME_PATTERN, attributes={}
    )
    if not success:
        if attempt < 3:
            logger.warning(
                "Welcome SMS gateway failed for %s. Retrying in 10s (attempt %s/%s)",
                mobile,
                attempt + 1,
                3,
            )
            return send_welcome_sms_task.apply_async(
                args=[mobile],
                kwargs={"attempt": attempt + 1},
                countdown=10,
            )
        logger.error(
            "Welcome SMS gateway failed after 3 attempts for mobile %s.",
            mobile,
        )
        return False
    logger.info("Welcome SMS successfully delivered to %s", mobile)
    return True
