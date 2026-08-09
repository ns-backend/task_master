import pytest
from django.urls import reverse
from rest_framework import status

from services.models import Category, Service, User

pytestmark = pytest.mark.django_db


def test_create_service_unauthenticated(api_client):
    """Тест: аноним не может создать услугу."""
    url = reverse("service-list")  # Автоматически найдет '/api/services/'
    data = {"name": "Test Service", "price": "100.00", "category": 1}
    response = api_client.post(url, data)
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


def test_create_service_authenticated_provider(api_client):
    """Тест: авторизованный провайдер может создать услугу."""
    # 1. Подготовка данных
    user = User.objects.create_user(
        username="pro_user", password="password123", is_provider=True
    )
    category = Category.objects.create(name="Cleaning", slug="cleaning")

    # 2. Авторизация
    api_client.force_authenticate(user=user)

    # 3. Действие
    url = reverse("service-list")
    data = {
        "name": "Professional Cleaning",
        "description": "Best cleaning in town",
        "price": "500.00",
        "category": category.id,
    }
    response = api_client.post(url, data)

    # 4. Проверка результатов
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Professional Cleaning"


def test_client_cannot_create_service(
    api_client,
    client_user,
    category,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        "/api/services/",
        {
            "name": "Новая услуга",
            "description": "Описание услуги",
            "price": "100.00",
            "category": category.id,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Service.objects.filter(name="Новая услуга").exists()


def test_provider_can_create_service(
    api_client,
    provider_user,
    category,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        "/api/services/",
        {
            "name": "Новая услуга",
            "description": "Описание услуги",
            "price": "100.00",
            "category": category.id,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    created_service = Service.objects.get(
        name="Новая услуга",
    )

    assert created_service.provider == provider_user


def test_provider_can_update_own_service(
    api_client,
    provider_user,
    service,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.patch(
        f"/api/services/{service.id}/",
        {
            "price": "150.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    service.refresh_from_db()

    assert str(service.price) == "150.00"


def test_provider_cannot_update_another_provider_service(
    api_client,
    another_provider,
    service,
):
    original_price = service.price

    api_client.force_authenticate(user=another_provider)

    response = api_client.patch(
        f"/api/services/{service.id}/",
        {
            "price": "999.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    service.refresh_from_db()

    assert service.price == original_price


def test_client_cannot_update_service(
    api_client,
    client_user,
    service,
):
    original_price = service.price

    api_client.force_authenticate(user=client_user)

    response = api_client.patch(
        f"/api/services/{service.id}/",
        {
            "price": "999.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    service.refresh_from_db()

    assert service.price == original_price


def test_provider_cannot_delete_another_provider_service(
    api_client,
    another_provider,
    service,
):
    api_client.force_authenticate(user=another_provider)

    response = api_client.delete(
        f"/api/services/{service.id}/",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN

    assert Service.objects.filter(id=service.id).exists()


def test_service_list_has_no_n_plus_one(
    api_client,
    provider_user,
    category,
    django_assert_max_num_queries,
):
    Service.objects.bulk_create(
        [
            Service(
                name=f"Service {index}",
                description="Description",
                price=100,
                provider=provider_user,
                category=category,
            )
            for index in range(10)
        ]
    )

    with django_assert_max_num_queries(5):
        response = api_client.get("/api/services/")

    assert response.status_code == status.HTTP_200_OK


def test_service_filter_by_category(
    api_client,
    service,
    provider_user,
):
    other_category = Category.objects.create(
        name="Cleaning",
        slug="cleaning-filter",
    )

    Service.objects.create(
        name="Cleaning service",
        description="Cleaning",
        price=100,
        provider=provider_user,
        category=other_category,
    )

    response = api_client.get(
        "/api/services/",
        {"category": service.category_id},
    )

    assert response.status_code == status.HTTP_200_OK

    results = response.data["results"]

    assert len(results) == 1
    assert results[0]["id"] == service.id


def test_service_search_by_name(
    api_client,
    service,
    provider_user,
    category,
):
    Service.objects.create(
        name="Уборка квартиры",
        description="Полная уборка",
        price=100,
        provider=provider_user,
        category=category,
    )

    response = api_client.get(
        "/api/services/",
        {"search": "Сборка"},
    )

    assert response.status_code == status.HTTP_200_OK

    results = response.data["results"]

    assert len(results) == 1
    assert results[0]["id"] == service.id


def test_service_ordering_by_price(
    api_client,
    provider_user,
    category,
):
    expensive = Service.objects.create(
        name="Expensive",
        description="Expensive service",
        price=200,
        provider=provider_user,
        category=category,
    )

    cheap = Service.objects.create(
        name="Cheap",
        description="Cheap service",
        price=50,
        provider=provider_user,
        category=category,
    )

    response = api_client.get(
        "/api/services/",
        {"ordering": "price"},
    )

    assert response.status_code == status.HTTP_200_OK

    result_ids = [item["id"] for item in response.data["results"]]

    assert result_ids.index(cheap.id) < result_ids.index(expensive.id)


def test_service_detail_is_public(
    api_client,
    service,
):
    response = api_client.get(
        f"/api/services/{service.id}/",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == service.id


def test_service_does_not_expose_provider_private_data(
    api_client,
    service,
):
    response = api_client.get(
        f"/api/services/{service.id}/",
    )

    assert response.status_code == status.HTTP_200_OK

    provider_data = response.data["provider"]

    assert provider_data["id"] == service.provider.id
    assert provider_data["username"] == service.provider.username
    assert "email" not in provider_data
    assert "phone_number" not in provider_data


def test_service_list_does_not_expose_provider_private_data(
    api_client,
    service,
):
    response = api_client.get("/api/services/")

    assert response.status_code == status.HTTP_200_OK

    service_data = next(
        item for item in response.data["results"] if item["id"] == service.id
    )

    provider_data = service_data["provider"]

    assert provider_data["id"] == service.provider.id
    assert provider_data["username"] == service.provider.username
    assert "email" not in provider_data
    assert "phone_number" not in provider_data
