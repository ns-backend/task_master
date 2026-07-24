import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Category, User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
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

@pytest.mark.django_db
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