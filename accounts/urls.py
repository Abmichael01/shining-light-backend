# urls.py
from django.urls import path, include
from .views import *

from rest_framework.routers import SimpleRouter
from .views import BiodataViewSet

router = SimpleRouter()
router.register('biodata', BiodataViewSet, basename='biodata')

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('refresh-token/', RefreshTokenView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view()),
    path('', include('dj_rest_auth.urls')),
    
    path('', include(router.urls)),
]