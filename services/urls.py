from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, CategoryViewSet, BookingViewSet, UserViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Просто подключаем все маршруты из роутера
    path('', include(router.urls)), 
]
