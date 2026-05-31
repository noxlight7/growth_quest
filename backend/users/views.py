"""
Views for the users app.

This module defines API endpoints for registering a new user. It uses
Django REST Framework's generic views to handle common logic and leverages
the serializers defined in `serializers.py` for validation and object creation.
"""
from __future__ import annotations

from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Administrator
from .serializers import (
    AdministratorCreateSerializer,
    AdministratorSerializer,
    AdministratorUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)
from django.contrib.auth import get_user_model

User = get_user_model()


def get_admin_level(user) -> int | None:
    if not user or not user.is_authenticated:
        return None
    try:
        return user.administrator_profile.level
    except Administrator.DoesNotExist:
        return None


class RegisterView(generics.CreateAPIView):
    """API endpoint that allows users to register for a new account."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # After successful registration, return the created user (without password fields)
        user_data = UserSerializer(user).data
        return Response(user_data, status=status.HTTP_201_CREATED)


class CurrentUserView(generics.RetrieveAPIView):
    """API endpoint to retrieve the authenticated user's information."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Allow login by username or email in the same field."""

    def validate(self, attrs):
        identifier = (attrs.get(self.username_field) or "").strip()
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).only(self.username_field).first()
            if user:
                attrs[self.username_field] = getattr(user, self.username_field)
        return super().validate(attrs)


class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


class AdministratorListCreateView(generics.ListCreateAPIView):
    serializer_class = AdministratorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        admin_level = get_admin_level(self.request.user)
        if admin_level is None:
            raise PermissionDenied("Недостаточно прав для просмотра администраторов.")
        return Administrator.objects.select_related("user").order_by("-level", "user__username")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdministratorCreateSerializer
        return AdministratorSerializer

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = self._create_admin(serializer.validated_data)
        output = AdministratorSerializer(admin)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def _create_admin(self, validated_data):
        admin_level = get_admin_level(self.request.user)
        if admin_level is None or admin_level < 2:
            raise PermissionDenied("Недостаточно прав для добавления администраторов.")

        username = validated_data["username"].strip()
        level = validated_data["level"]

        if level >= admin_level:
            raise ValidationError({"level": "Новый уровень должен быть ниже вашего."})

        user = User.objects.filter(username__iexact=username).first()
        if not user:
            raise ValidationError({"username": "Пользователь с таким именем не найден."})
        if hasattr(user, "administrator_profile"):
            raise ValidationError({"username": "Пользователь уже является администратором."})

        return Administrator.objects.create(user=user, level=level)


class AdministratorDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Administrator.objects.select_related("user")
    serializer_class = AdministratorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in {"PATCH", "PUT"}:
            return AdministratorUpdateSerializer
        return AdministratorSerializer

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        admin_level = get_admin_level(self.request.user)
        if admin_level is None:
            raise PermissionDenied("Недостаточно прав для изменения уровня.")

        instance = self.get_object()
        if instance.level >= admin_level:
            raise PermissionDenied("Можно изменить только администратора с уровнем ниже вашего.")

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_level = serializer.validated_data["level"]
        if new_level >= admin_level:
            raise ValidationError({"level": "Новый уровень должен быть ниже вашего."})

        instance.level = new_level
        instance.save(update_fields=["level"])
        output = AdministratorSerializer(instance)
        return Response(output.data)

    def perform_destroy(self, instance):
        admin_level = get_admin_level(self.request.user)
        if admin_level is None:
            raise PermissionDenied("Недостаточно прав для удаления администраторов.")
        if instance.level >= admin_level:
            raise PermissionDenied("Можно удалить только администратора с уровнем ниже вашего.")
        instance.delete()
