from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, national_code, mobile, password=None, **extra_fields):
        if not national_code:
            raise ValueError("کد ملی الزامی است.")
        if not mobile:
            raise ValueError("شماره همراه الزامی است.")

        user = self.model(
            national_code=national_code,
            mobile=mobile,
            **extra_fields,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, national_code, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_mobile_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(national_code, mobile, password, **extra_fields)
