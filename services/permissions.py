from rest_framework import permissions


class IsProviderOrReadOnly(permissions.BasePermission):
    """
    Разрешает создание только пользователям с флагом is_provider.
    Редактирование — только владельцу (provider).
    Просмотр — всем (SAFE_METHODS).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_provider

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.provider == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Читать объект может любой пользователь.
    Создавать, изменять и удалять может только администратор.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.is_staff
