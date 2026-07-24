from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Booking, Category, Service, User
from .permissions import IsProviderOrReadOnly
from .serializers import (
    BookingSerializer, 
    CategorySerializer, 
    ServiceReadSerializer, 
    ServiceWriteSerializer, 
    UserSerializer
)


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Управление услугами маркетплейса.
    """
    queryset = Service.objects.all()
    permission_classes = [IsProviderOrReadOnly]
    
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_fields = {
        'category': ['exact'],
        'price': ['gte', 'lte'],
    }
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ServiceReadSerializer
        return ServiceWriteSerializer

    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Справочник категорий услуг.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class BookingViewSet(viewsets.ModelViewSet):
    """
    Система бронирования услуг.
    """
    serializer_class = BookingSerializer

    def get_queryset(self):
        user = self.request.user
        # select_related ускоряет работу, подгружая связанные данные сразу
        base_queryset = Booking.objects.select_related('client', 'service', 'service__provider')
        
        if user.is_provider:
            return base_queryset.filter(service__provider=user)
        return base_queryset.filter(client=user)

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    """
    Управление профилями пользователей.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer