from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, CategoryViewSet, ServiceViewSet, UserViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)), 
]