from apps.sms.services import OTPService


class TestOTPService:
    def test_generate_otp_length(self):
        code = OTPService.generate_otp()
        assert len(code) == 4
        assert code.isdigit()

    def test_set_and_verify_otp(self):
        mobile = "09121111111"
        code = "9876"
        purpose = "test_flow"

        OTPService.set_otp(mobile, code, purpose)
        assert OTPService.get_otp(mobile, purpose) == code

        # Wrong code
        assert OTPService.verify_otp(mobile, "0000", purpose) is False

        # Correct code
        assert OTPService.verify_otp(mobile, code, purpose) is True
        # Verified code should be deleted immediately
        assert OTPService.get_otp(mobile, purpose) is None
