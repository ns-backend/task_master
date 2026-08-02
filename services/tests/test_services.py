import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from services.models import Category, User
from services.models import Service


pytestmark = pytest.mark.django_db


def api_client():
    return APIClient()


def test_create_service_unauthenticated(api_client):
    """Тест: аноним не может создать услугу."""
    url = reverse('service-list') # Автоматически найдет '/api/services/'
    data = {
        "name": "Test Service",
        "price": "100.00",
        "category": 1
    }
    response = api_client.post(url, data)
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


def test_create_service_authenticated_provider(api_client):
    """Тест: авторизованный провайдер может создать услугу."""
    # 1. Подготовка данных
    user = User.objects.create_user(
        username='pro_user', 
        password='password123', 
        is_provider=True
    )
    category = Category.objects.create(name='Cleaning', slug='cleaning')
    
    # 2. Авторизация
    api_client.force_authenticate(user=user)
    
    # 3. Действие
    url = reverse('service-list')
    data = {
        "name": "Professional Cleaning",
        "description": "Best cleaning in town",
        "price": "500.00",
        "category": category.id
    }
    response = api_client.post(url, data)
    
    # 4. Проверка результатов
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == "Professional Cleaning"


def test_client_cannot_create_service(
    api_client,
    client_user,
    category,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        '/api/services/',
        {
            'name': 'Новая услуга',
            'description': 'Описание услуги',
            'price': '100.00',
            'category': category.id,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Service.objects.filter(name='Новая услуга').exists()


def test_provider_can_create_service(
    api_client,
    provider_user,
    category,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.post(
        '/api/services/',
        {
            'name': 'Новая услуга',
            'description': 'Описание услуги',
            'price': '100.00',
            'category': category.id,
        },
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED

    created_service = Service.objects.get(
        name='Новая услуга',
    )

    assert created_service.provider == provider_user


def test_provider_can_update_own_service(
    api_client,
    provider_user,
    service,
):
    api_client.force_authenticate(user=provider_user)

    response = api_client.patch(
        f'/api/services/{service.id}/',
        {
            'price': '150.00',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK

    service.refresh_from_db()

    assert str(service.price) == '150.00'


def test_provider_cannot_update_another_provider_service(
    api_client,
    another_provider,
    service,
):
    original_price = service.price

    api_client.force_authenticate(user=another_provider)

    response = api_client.patch(
        f'/api/services/{service.id}/',
        {
            'price': '999.00',
        },
        format='json',
    )

    assert response.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    }

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
        f'/api/services/{service.id}/',
        {
            'price': '999.00',
        },
        format='json',
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
        f'/api/services/{service.id}/',
    )

    assert response.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    }

    assert Service.objects.filter(id=service.id).exists()