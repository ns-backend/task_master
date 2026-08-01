from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Booking, Category, Service, User
from .permissions import IsAdminOrReadOnly, IsProviderOrReadOnly
from .serializers import (
    BookingSerializer,
    CategorySerializer,
    ServiceReadSerializer,
    ServiceWriteSerializer,
    UserReadSerializer,
    UserRegistrationSerializer,
    UserUpdateSerializer,
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
    permission_classes = [IsAdminOrReadOnly]


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Booking.objects.select_related(
            'client',
            'service',
            'service__provider',
        )

        if user.is_provider:
            return queryset.filter(service__provider=user)

        return queryset.filter(client=user)

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

    @action(
        detail=True,
        methods=['post'],
    )
    def confirm(self, request, pk=None):
        booking = self.get_object()

        if booking.service.provider != request.user:
            return Response(
                {'detail': 'Подтвердить бронирование может только провайдер услуги.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status != 'pending':
            return Response(
                {'detail': 'Подтвердить можно только ожидающее бронирование.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = 'confirmed'
        booking.save(update_fields=['status'])

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
    )
    def complete(self, request, pk=None):
        booking = self.get_object()

        if booking.service.provider != request.user:
            return Response(
                {'detail': 'Завершить бронирование может только провайдер услуги.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status != 'confirmed':
            return Response(
                {'detail': 'Завершить можно только подтверждённое бронирование.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = 'completed'
        booking.save(update_fields=['status'])

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
    )
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.client != request.user:
            return Response(
                {'detail': 'Отменить бронирование может только клиент.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_statuses = [
            'pending',
            'confirmed',
        ]

        if booking.status not in allowed_statuses:
            return Response(
                {'detail': 'Это бронирование уже нельзя отменить.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = 'canceled'
        booking.save(update_fields=['status'])

        serializer = self.get_serializer(booking)
        return Response(serializer.data)


class UserViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Регистрация пользователя и управление собственным профилем.
    """

    queryset = User.objects.all()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer

        if self.action == 'me' and self.request.method == 'PATCH':
            return UserUpdateSerializer

        return UserReadSerializer

    @action(
        detail=False,
        methods=['get', 'patch'],
        url_path='me',
    )
    def me(self, request):
        user = request.user

        if request.method == 'GET':
            serializer = UserReadSerializer(user)
            return Response(serializer.data)

        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = UserReadSerializer(user)
        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )