"""
URL configurations for the users app.

Defines endpoints for registration and retrieving the current user's data.
"""
from django.urls import path

from .views import (
    AdministratorDestroyView,
    AdministratorListCreateView,
    RegisterView,
    CurrentUserView,
)


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('admins/', AdministratorListCreateView.as_view(), name='admin_list_create'),
    path('admins/<int:pk>/', AdministratorDestroyView.as_view(), name='admin_delete'),
]
