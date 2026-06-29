import json
import logging
import sys
import urllib.error
import urllib.request

from decouple import config
from django.conf import settings

logger = logging.getLogger(__name__)

SMS_API_URL = config("SMS_API_URL", default="https://api.iranpayamak.com/ws/v1/sms/pattern")
SMS_API_KEY = config(
    "SMS_API_KEY", default="UbVzvuEiOEJR3ZZMF5cBPCPUSTNT9uuELHFHNkihi2JpCPCYE0"
)
SMS_LINE_NUMBER = config("SMS_LINE_NUMBER", default="50002178584000")
SMS_OTP_PATTERN = config("SMS_OTP_PATTERN", default="pXMLHeNMQW")
SMS_WELCOME_PATTERN = config("SMS_WELCOME_PATTERN", default="Yta6XeoECQ")


class IranPayamakClient:
    @classmethod
    def send_pattern(cls, recipient: str, pattern_code: str, attributes: dict) -> bool:
        is_testing = any("pytest" in arg or "test" == arg for arg in sys.argv)
        if getattr(settings, "MOCK_SMS_GATEWAY", False) or is_testing:
            logger.info(
                "[MOCK SMS GATEWAY] Dispatching pattern [%s] to %s with attrs: %s",
                pattern_code,
                recipient,
                attributes,
            )
            return True

        payload = {
            "code": pattern_code.strip(),
            "recipient": recipient,
            "line_number": SMS_LINE_NUMBER,
            "number_format": "persian",
        }
        if attributes:
            payload["attributes"] = attributes

        data = json.dumps(payload).encode("utf-8")

        headers = {
            "Api-Key": SMS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }

        req = urllib.request.Request(SMS_API_URL, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                response_body = response.read().decode("utf-8")
                logger.info(
                    "SMS successfully dispatched to %s. Status: %s, Response: %s",
                    recipient,
                    status_code,
                    response_body,
                )
                return True
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            logger.error(
                "HTTPError while sending SMS to %s. Code: %s, Body: %s",
                recipient,
                exc.code,
                error_body,
            )
            return False
        except urllib.error.URLError as exc:
            logger.error(
                "URLError network failure while sending SMS to %s: %s",
                recipient,
                exc.reason,
            )
            return False
        except Exception:
            logger.exception("Unexpected exception occurred during SMS delivery to %s", recipient)
            return False
