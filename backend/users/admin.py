"""
Admin configuration for the users app.

This module registers the custom User model with the Django admin site so
that administrators can manage user accounts through the admin interface.
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Administrator

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define the admin pages for the custom user model."""

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Game', {'fields': ('credits',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'email', 'is_staff', 'credits')
    search_fields = ('username', 'email')
    ordering = ('username',)


@admin.register(Administrator)
class AdministratorAdmin(admin.ModelAdmin):
    list_display = ("user", "level")
    search_fields = ("user__username", "user__email")
    ordering = ("-level", "user__username")
