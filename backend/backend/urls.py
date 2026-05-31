"""
URL configuration for the Django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import EmailOrUsernameTokenObtainPairView
from adventures.views.learning_views import AccessibilityProfileView, LearnerProfileView


urlpatterns = [
    path('admin/', admin.site.urls),
    # JWT endpoints
    path('api/auth/token/', EmailOrUsernameTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # User registration endpoint
    path('api/users/', include('users.urls')),
    path('api/accessibility/profile/', AccessibilityProfileView.as_view(), name='accessibility_profile'),
    path('api/player/profile/', LearnerProfileView.as_view(), name='player_profile'),
    path('api/learner/profile/', LearnerProfileView.as_view(), name='learner_profile'),
    path('api/adventures/', include('adventures.urls')),
]
