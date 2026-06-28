import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.core.validators import validate_iranian_mobile, validate_national_code


@pytest.mark.django_db
class TestUserModelAndValidators:
    def test_create_user_success(self):
        user = User.objects.create_user(
            national_code="0123456789",
            mobile="09123456789",
            first_name="علی",
            last_name="محمدی",
            job="عکاس",
            birth_date="1990-01-01",
            province="تهران",
            city="تهران",
            address="خیابان آزادی",
            postal_code="1234567890",
        )
        assert user.national_code == "0123456789"
        assert user.mobile == "09123456789"
        assert user.full_name == "علی محمدی"
        assert user.is_mobile_verified is True
        assert user.check_password(None) is False

    def test_national_code_validator_invalid_length(self):
        with pytest.raises(ValidationError):
            validate_national_code("123")

    def test_national_code_validator_all_same_digits(self):
        with pytest.raises(ValidationError):
            validate_national_code("1111111111")

    def test_mobile_validator_invalid_prefix(self):
        with pytest.raises(ValidationError):
            validate_iranian_mobile("08123456789")
