from .models import Service, Category, Booking, User
from .serializers import CategorySerializer, BookingSerializer, UserSerializer, ServiceReadSerializer, ServiceWriteSerializer
from .permissions import IsProviderOrReadOnly
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    permission_classes = [IsProviderOrReadOnly]

    def get_serializer_class(self):
        # Если метод запроса — GET, отдаем красивый сериализатор
        if self.action in ['list', 'retrieve']:
            return ServiceReadSerializer
        # Для POST, PUT, PATCH отдаем сериализатор для записи
        return ServiceWriteSerializer

    # Подключаем фильтры
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]

    # 1. Фильтрация по полям (точное совпадение или диапазон)
    filterset_fields = {
        'category': ['exact'],
        'price': ['gte', 'lte'], # gte - больше или равно, lte - меньше или равно
    }

    # 2. Поиск по тексту
    search_fields = ['name', 'description']

    # 3. Сортировка
    ordering_fields = ['price', 'created_at'] # created_at добавь в модель, если есть
    ordering = ['-id'] # Сортировка по умолчанию (сначала новые)

    def perform_create(self, serializer):
        # Это магия DRF: когда мы сохраняем новую услугу, 
        # мы автоматически назначаем текущего пользователя провайдером.
        serializer.save(provider=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        # Аналогично для бронирования: текущий юзер = клиент
        serializer.save(client=self.request.user)

    def get_queryset(self):
        user = self.request.user
        # Если это провайдер, отдаем бронирования его услуг
        if user.is_provider:
            return Booking.objects.filter(service__provider=user)
        # Если обычный клиент, отдаем только его бронирования
        return Booking.objects.filter(client=user)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
