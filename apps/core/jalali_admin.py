"""
Jalali date field and widget for Django admin.
Converts between Jalali (input/display) and Gregorian (storage).
"""

import jdatetime
from django import forms
from django.contrib.admin import widgets


class JalaliAdminDateWidget(widgets.AdminDateWidget):
    """Widget that displays Jalali dates in YYYY-MM-DD format."""

    def format_value(self, value):
        if value is None:
            return ""
        try:
            if hasattr(value, "year"):
                if 1300 <= value.year <= 1500:
                    return f"{value.year}-{value.month:02d}-{value.day:02d}"
                jd = jdatetime.date.fromgregorian(date=value)
                return f"{jd.year}-{jd.month:02d}-{jd.day:02d}"
        except (ValueError, OverflowError, TypeError):
            pass
        return str(value)


class JalaliAdminDateField(forms.DateField):
    """
    Admin form field that:
    - Displays dates in Jalali format
    - Accepts Jalali input (YYYY-MM-DD where year is 1300-1500)
    - Converts to Gregorian before saving to database
    """

    widget = JalaliAdminDateWidget

    def prepare_value(self, value):
        if value is None:
            return ""
        try:
            if hasattr(value, "year"):
                if 1300 <= value.year <= 1500:
                    return value
                return jdatetime.date.fromgregorian(date=value)
        except (ValueError, OverflowError, TypeError):
            pass
        return value

    def to_python(self, value):
        if not value:
            return None
        value = str(value).strip()
        if "-" in value:
            parts = value.split("-")
            if len(parts) == 3:
                try:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    if 1300 <= year <= 1500:
                        jd = jdatetime.date(year, month, day)
                        return jd.togregorian()
                except (ValueError, TypeError):
                    pass
        return super().to_python(value)
