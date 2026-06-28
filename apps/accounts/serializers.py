from rest_framework import serializers


class AuthLoginRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=20)


class AuthLoginVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=10)
