from rest_framework import viewsets
from .models import Service, Category, Booking, User
from .serializers import ServiceSerializer, CategorySerializer, BookingSerializer, UserSerializer
from .permissions import IsProviderOrReadOnly

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsProviderOrReadOnly]

    def perform_create(self, serializer):
        # Это магия DRF: когда мы сохраняем новую услугу, 
        # мы автоматически назначаем текущего пользователя провайдером.
        serializer.save(provider=self.request.user)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        # Аналогично для бронирования: текущий юзер = клиент
        serializer.save(client=self.request.user)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
