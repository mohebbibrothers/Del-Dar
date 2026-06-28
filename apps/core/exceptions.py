import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        customized_response = {
            "success": False,
            "error": {
                "status_code": response.status_code,
                "message": _get_error_message(response.data),
                "details": response.data,
            },
        }
        response.data = customized_response
    else:
        logger.exception("Unhandled exception occurred in API request", exc_info=exc)

    return response


def _get_error_message(data):
    if isinstance(data, dict):
        for val in data.values():
            if isinstance(val, (list, tuple)) and len(val) > 0:
                return str(val[0])
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return _get_error_message(val)
    elif isinstance(data, (list, tuple)) and len(data) > 0:
        return str(data[0])
    return "خطایی در پردازش درخواست رخ داده است."
