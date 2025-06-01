import pytest
from fastapi import status

def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "newpassword"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "id" in data
    assert "hashed_password" not in data

def test_create_user_duplicate_email(client, test_user):
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "username": "differentuser",
            "password": "password"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_create_user_duplicate_username(client, test_user):
    response = client.post(
        "/users/",
        json={
            "email": "different@example.com",
            "username": "testuser",
            "password": "password"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_login_success(client, test_user):
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, test_user):
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client):
    response = client.post(
        "/token",
        data={"username": "nonexistent", "password": "password"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user(client, test_user_token):
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "hashed_password" not in data

def test_get_current_user_no_token(client):
    response = client.get("/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_user_by_id(client, test_user, test_user_token):
    response = client.get(
        f"/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "hashed_password" not in data

def test_get_nonexistent_user(client, test_user_token):
    response = client.get(
        "/users/999",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_user_unauthorized(client, test_user):
    response = client.get(f"/users/{test_user.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED 