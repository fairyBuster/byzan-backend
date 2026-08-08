from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "full_name",
            "username",
            "email",
            "phone",
            "password",
            "confirm_password",
        ]
        extra_kwargs = {
            "phone": {"required": True, "allow_blank": False},
            "full_name": {"required": True, "allow_blank": False},
            "username": {"required": True, "allow_blank": False},
            "email": {"required": True, "allow_blank": False},
            "password": {"required": True},
            "confirm_password": {"required": True},
        }

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        user = User.objects.create_user(
            full_name=validated_data.get("full_name", ""),
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            phone=validated_data.get("phone", ""),
            address="",
            city="",
            state="",
            country="",
            pincode="",
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "gender",
            "first_name",
            "last_name",
            "email",
            "email_verified",
            "phone",
            "birthday",
            "country",
            "address",
            "city",
            "instagram_link",
            "facebook_link",
            "username",
            "full_name",
            "balance",
        ]
        read_only_fields = ["id", "email_verified", "username", "balance"]
        extra_kwargs = {
            "gender": {"required": True, "allow_blank": False},
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "email": {"required": True, "allow_blank": False},
            "phone": {"required": True, "allow_blank": False},
            "birthday": {"required": True, "allow_null": False},
            "country": {"required": True, "allow_blank": False},
            "city": {"required": True, "allow_blank": False},
            "address": {"required": False, "allow_blank": True},
            "instagram_link": {"required": False, "allow_blank": True},
            "facebook_link": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        first_name = attrs.get(
            "first_name",
            getattr(self.instance, "first_name", "") if self.instance else "",
        )
        last_name = attrs.get(
            "last_name",
            getattr(self.instance, "last_name", "") if self.instance else "",
        )
        if first_name or last_name:
            attrs["full_name"] = f"{first_name} {last_name}".strip()
        return attrs

    def validate_email(self, value):
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Email sudah digunakan")
        return value
