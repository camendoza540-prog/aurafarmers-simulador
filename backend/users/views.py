from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import permissions, status
from rest_framework.decorators import api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from config.throttles import LoginThrottle, PasswordThrottle, RegisterThrottle

from .serializers import ChangePasswordSerializer, DeleteAccountSerializer, RegisterSerializer, UserSerializer
from .services import net_worth, ranking, reset_simulation


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([RegisterThrottle])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(
        {"user": UserSerializer(user).data, "tokens": _tokens(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH"])
def me(request):
    if request.method == "PATCH":
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        from django.core.cache import cache
        cache.delete_many(["ranking:all", "ranking:stale"])  # nombre, foto o privacidad pudieron cambiar
    data = UserSerializer(request.user).data
    data["net_worth"] = net_worth(request.user)
    return Response(data)


@api_view(["POST"])
@throttle_classes([PasswordThrottle])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    request.user.set_password(serializer.validated_data["new_password"])
    request.user.save()
    return Response({"detail": "Contraseña actualizada correctamente.", "tokens": _tokens(request.user)})


@api_view(["POST", "DELETE"])
@parser_classes([MultiPartParser])
def avatar(request):
    """Sube (POST, campo «avatar») o elimina (DELETE) la foto de perfil. Se recorta a 320×320 px."""
    profile = request.user.profile
    if request.method == "DELETE":
        if profile.avatar:
            profile.avatar.delete(save=False)
        profile.avatar = None
        profile.save(update_fields=["avatar"])
        return Response(UserSerializer(request.user).data)
    file = request.FILES.get("avatar")
    if not file:
        return Response({"detail": "Selecciona una imagen."}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 5 * 1024 * 1024:
        return Response({"detail": "La imagen no puede superar 5 MB."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return Response({"detail": "El archivo no es una imagen válida (usa JPG, PNG o WebP)."}, status=status.HTTP_400_BAD_REQUEST)
    img = ImageOps.fit(img, (320, 320), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=86)
    if profile.avatar:
        profile.avatar.delete(save=False)
    profile.avatar.save(f"u{request.user.pk}.jpg", ContentFile(buf.getvalue()), save=True)
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
def leaderboard(request):
    return Response(ranking(limit=50, me=request.user))


@api_view(["POST"])
def reset(request):
    if request.data.get("confirm") != "REINICIAR":
        return Response(
            {"detail": "Escribe REINICIAR para confirmar."}, status=status.HTTP_400_BAD_REQUEST
        )
    reset_simulation(request.user)
    return Response({"detail": "Simulación reiniciada.", "net_worth": net_worth(request.user)})


@api_view(["POST"])
def accept_terms(request):
    """Registra la aceptación de la versión vigente de los términos (cuentas creadas antes de ella)."""
    if request.data.get("accept") is not True:
        return Response({"detail": "Debes marcar la casilla de aceptación."}, status=status.HTTP_400_BAD_REQUEST)
    request.user.profile.accept_terms()
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@throttle_classes([PasswordThrottle])
def delete_account(request):
    """Derecho de supresión (Ley 1581): elimina la cuenta y todos sus datos de forma definitiva."""
    serializer = DeleteAccountSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user = request.user
    if user.is_superuser:
        return Response({"detail": "La cuenta de administración no se puede eliminar desde aquí."},
                        status=status.HTTP_400_BAD_REQUEST)
    if user.profile.avatar:
        user.profile.avatar.delete(save=False)
    user.delete()  # en cascada: perfil, portafolios, ahorros, simulaciones, mensajes, tickets y progreso
    from django.core.cache import cache
    cache.delete_many(["ranking:all", "ranking:stale"])
    return Response(status=status.HTTP_204_NO_CONTENT)
