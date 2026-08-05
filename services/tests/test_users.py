import pytest
from rest_framework import status

from services.models import User

pytestmark = pytest.mark.django_db


def test_anonymous_user_can_register(api_client):
    payload = {
        "username": "new_client",
        "email": "new-client@example.com",
        "password": "strong-password-123",
        "is_provider": False,
        "phone_number": "+49444444444",
    }

    response = api_client.post(
        "/api/users/",
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username="new_client").exists()
    assert "password" not in response.data

    user = User.objects.get(username="new_client")

    assert user.password != payload["password"]
    assert user.check_password(payload["password"])


def test_me_endpoint_requires_authentication(api_client):
    response = api_client.get("/api/users/me/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_can_read_own_profile(api_client, client_user):
    api_client.force_authenticate(user=client_user)

    response = api_client.get("/api/users/me/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == client_user.id
    assert response.data["username"] == client_user.username
    assert response.data["email"] == client_user.email


def test_user_can_update_own_profile(api_client, client_user):
    api_client.force_authenticate(user=client_user)

    response = api_client.patch(
        "/api/users/me/",
        {
            "email": "updated@example.com",
            "phone_number": "+49555555555",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    client_user.refresh_from_db()

    assert client_user.email == "updated@example.com"
    assert client_user.phone_number == "+49555555555"


def test_user_cannot_change_provider_role(
    api_client,
    client_user,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.patch(
        "/api/users/me/",
        {
            "is_provider": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    client_user.refresh_from_db()

    assert client_user.is_provider is False


def test_user_list_is_not_available(api_client, client_user):
    api_client.force_authenticate(user=client_user)

    response = api_client.get("/api/users/")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_user_detail_endpoint_is_not_available(
    api_client,
    client_user,
    provider_user,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.get(
        f"/api/users/{provider_user.id}/",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_cannot_update_another_user(
    api_client,
    client_user,
    provider_user,
):
    api_client.force_authenticate(user=client_user)

    response = api_client.patch(
        f"/api/users/{provider_user.id}/",
        {
            "email": "hacked@example.com",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    provider_user.refresh_from_db()

    assert provider_user.email == "provider@example.com"
