import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data

def test_create_user_duplicate_email(client):
    # First create a user
    client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "username": "testuser1",
            "password": "testpass123"
        }
    )
    
    # Try to create another user with the same email
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "username": "testuser2",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_create_user_duplicate_username(client):
    # First create a user
    client.post(
        "/users/",
        json={
            "email": "test1@example.com",
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    # Try to create another user with the same username
    response = client.post(
        "/users/",
        json={
            "email": "test2@example.com",
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_get_user_by_id(client, test_user, test_user_token):
    user_id = test_user.id
    response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id

def test_get_nonexistent_user(client, test_user_token):
    response = client.get(
        "/users/999",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_user_unauthorized(client, test_user, test_user2_token):
    user_id = test_user.id
    response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user2_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_update_user(client, test_user, test_user_token):
    user_id = test_user.id
    response = client.put(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "email": "updated@example.com",
            "username": "updateduser"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id

def test_update_user_no_auth(client, test_user):
    response = client.put(
        f"/users/{test_user.id}",
        json={
            "email": "updated@example.com",
            "username": "updateduser"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_user_unauthorized(client, test_user, test_user2_token):
    user_id = test_user.id
    response = client.put(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user2_token}"},
        json={
            "email": "updated@example.com",
            "username": "updateduser"
        }
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_update_user_duplicate_email(client, test_user, test_user_token):
    # First create another user
    client.post(
        "/users/",
        json={
            "email": "other@example.com",
            "username": "otheruser",
            "password": "testpass123"
        }
    )
    
    # Try to update test_user with the other user's email
    response = client.put(
        f"/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "email": "other@example.com",
            "username": "testuser"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_update_user_duplicate_username(client, test_user, test_user_token):
    # First create another user
    client.post(
        "/users/",
        json={
            "email": "other@example.com",
            "username": "otheruser",
            "password": "testpass123"
        }
    )
    
    # Try to update test_user with the other user's username
    response = client.put(
        f"/users/{test_user.id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "email": "test@example.com",
            "username": "otheruser"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_delete_user(client, test_user, test_user_token, test_admin_token):
    user_id = test_user.id
    response = client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    # Verify user is deleted using admin token
    get_response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_admin_token}"}
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_user_no_auth(client, test_user):
    response = client.delete(f"/users/{test_user.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_delete_user_unauthorized(client, test_user, test_user2_token):
    user_id = test_user.id
    response = client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_user2_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_admin_get_all_users(client, test_admin_token):
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {test_admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)

def test_non_admin_get_all_users(client, test_user_token):
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_admin_delete_user(client, test_user, test_admin_token):
    user_id = test_user.id
    response = client.delete(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {test_admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    # Verify user is deleted
    get_response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {test_admin_token}"}
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND 