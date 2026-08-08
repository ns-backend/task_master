from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from services.booking_services import (
    cancel_booking,
    complete_booking,
    confirm_booking,
)

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

    queryset = Service.objects.select_related(
        "category",
        "provider",
    )
    permission_classes = [IsProviderOrReadOnly]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = {
        "category": ["exact"],
        "price": ["gte", "lte"],
    }
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return ServiceReadSerializer
        return ServiceWriteSerializer

    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Справочник категорий услуг.
    """

    queryset = Category.objects.all().order_by("id")
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
            "client",
            "service",
            "service__provider",
        )

        if user.is_provider:
            return queryset.filter(service__provider=user)

        return queryset.filter(client=user)

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = confirm_booking(
            queryset=self.get_queryset(),
            booking_id=pk,
            actor=request.user,
        )

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = complete_booking(
            queryset=self.get_queryset(),
            booking_id=pk,
            actor=request.user,
        )

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = cancel_booking(
            queryset=self.get_queryset(),
            booking_id=pk,
            actor=request.user,
        )

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
        if self.action == "create":
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer

        if self.action == "me" and self.request.method == "PATCH":
            return UserUpdateSerializer

        return UserReadSerializer

    @action(
        detail=False,
        methods=["get", "patch"],
        url_path="me",
    )
    def me(self, request):
        user = request.user

        if request.method == "GET":
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
