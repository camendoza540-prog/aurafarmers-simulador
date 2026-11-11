from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    terms_current = serializers.BooleanField(read_only=True)
    terms_required_version = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["initial_balance", "cash_balance", "risk_profile", "experience", "bio", "description",
                  "show_in_ranking", "avatar_url", "created_at",
                  "terms_accepted_at", "terms_version", "terms_current", "terms_required_version"]
        read_only_fields = ["initial_balance", "cash_balance", "created_at", "terms_accepted_at", "terms_version"]

    def get_terms_required_version(self, obj):
        return settings.LEGAL["TERMS_VERSION"]

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "date_joined", "is_staff", "profile"]
        read_only_fields = ["id", "username", "date_joined", "is_staff"]

    def validate_email(self, value):
        qs = User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk if self.instance else None)
        if value and qs.exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    username = serializers.RegexField(
        r"^[\w.@+-]{3,30}$",
        error_messages={"invalid": "Usa entre 3 y 30 caracteres: letras, números o . @ + - _"},
    )
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    risk_profile = serializers.ChoiceField(choices=Profile.RISK_CHOICES, default="moderado")
    experience = serializers.ChoiceField(choices=Profile.EXPERIENCE_CHOICES, default="ninguna")
    accept_terms = serializers.BooleanField(
        default=False,
        help_text="Aceptación de los términos y autorización de tratamiento de datos (Ley 1581 de 2012).",
    )

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "Para crear tu cuenta debes aceptar los términos y condiciones y autorizar el tratamiento de tus datos personales.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya está en uso.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        candidate = User(username=attrs["username"], email=attrs["email"], first_name=attrs["first_name"])
        validate_password(attrs["password"], candidate)
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        validated_data.pop("accept_terms")
        risk = validated_data.pop("risk_profile")
        exp = validated_data.pop("experience")
        user = User.objects.create_user(**validated_data)
        user.profile.risk_profile = risk
        user.profile.experience = exp
        user.profile.save()
        user.profile.accept_terms()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    new_password2 = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Las contraseñas nuevas no coinciden."})
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": "La nueva contraseña debe ser distinta de la actual."})
        return attrs

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm = serializers.CharField()

    def validate_confirm(self, value):
        if value.strip().upper() != "ELIMINAR":
            raise serializers.ValidationError("Escribe ELIMINAR para confirmar.")
        return value

    def validate_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contraseña no es correcta.")
        return value
