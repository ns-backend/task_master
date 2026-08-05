import pytest
from rest_framework import status

from services.models import Category

pytestmark = pytest.mark.django_db


def test_anonymous_user_can_list_categories(
    api_client,
    category,
):
    response = api_client.get("/api/categories/")

    assert response.status_code == status.HTTP_200_OK


def test_regular_user_cannot_create_category(
    api_client,
    client_user,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        "/api/categories/",
        {
            "name": "Уборка",
            "slug": "cleaning",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Category.objects.filter(slug="cleaning").exists()


def test_provider_cannot_create_category(
    api_client,
    provider_user,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        "/api/categories/",
        {
            "name": "Уборка",
            "slug": "cleaning",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Category.objects.filter(slug="cleaning").exists()


def test_admin_can_create_category(
    api_client,
    admin_user,
):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post(
        "/api/categories/",
        {
            "name": "Уборка",
            "slug": "cleaning",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert Category.objects.filter(slug="cleaning").exists()


def test_regular_user_cannot_update_category(
    api_client,
    client_user,
    category,
):
    original_name = category.name

    api_client.force_authenticate(user=client_user)

    response = api_client.patch(
        f"/api/categories/{category.id}/",
        {
            "name": "Новое название",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    category.refresh_from_db()

    assert category.name == original_name


def test_admin_can_update_category(
    api_client,
    admin_user,
    category,
):
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        f"/api/categories/{category.id}/",
        {
            "name": "Домашний ремонт",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    category.refresh_from_db()

    assert category.name == "Домашний ремонт"


def test_regular_user_cannot_delete_category(
    api_client,
    client_user,
    category,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.delete(
        f"/api/categories/{category.id}/",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Category.objects.filter(id=category.id).exists()
