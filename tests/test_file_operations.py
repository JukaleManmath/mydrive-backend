import pytest
from fastapi import status
import io

def test_move_file(client, test_user_token):
    # First create a folder
    folder_response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"filename": "test_folder"}
    )
    folder_id = folder_response.json()["id"]

    # Upload a file
    file_content = b"Test file content"
    files = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    upload_response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )
    file_id = upload_response.json()["id"]

    # Move file to folder
    response = client.patch(
        f"/files/{file_id}/move",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"target_parent_id": folder_id}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["parent_id"] == folder_id

def test_move_file_no_auth(client):
    response = client.patch(
        "/files/1/move",
        json={"target_parent_id": 1}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_move_file_unauthorized(client, test_user_token, test_user2_token):
    # First create a folder with test_user
    folder_response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"filename": "test_folder"}
    )
    folder_id = folder_response.json()["id"]

    # Upload a file with test_user2
    file_content = b"Test file content"
    files = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    upload_response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {test_user2_token}"},
        files=files
    )
    file_id = upload_response.json()["id"]

    # Try to move file with test_user
    response = client.patch(
        f"/files/{file_id}/move",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"target_parent_id": folder_id}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_move_file_to_nonexistent_folder(client, test_user_token):
    # Upload a file
    file_content = b"Test file content"
    files = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    upload_response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )
    file_id = upload_response.json()["id"]

    # Try to move to nonexistent folder
    response = client.patch(
        f"/files/{file_id}/move",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"target_parent_id": 999}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_move_file_to_itself(client, test_user_token):
    # First create a folder
    folder_response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"filename": "test_folder"}
    )
    folder_id = folder_response.json()["id"]

    # Try to move folder into itself
    response = client.patch(
        f"/files/{folder_id}/move",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"target_parent_id": folder_id}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_move_file_to_descendant(client, test_user_token):
    # Create parent folder
    parent_folder_response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"filename": "parent_folder"}
    )
    parent_folder_id = parent_folder_response.json()["id"]

    # Create child folder
    child_folder_response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"filename": "child_folder", "parent_id": parent_folder_id}
    )
    child_folder_id = child_folder_response.json()["id"]

    # Try to move parent folder into child folder
    response = client.patch(
        f"/files/{parent_folder_id}/move",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"target_parent_id": child_folder_id}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_move_file_to_root(client, test_user_token):
    # First create a folder
    folder_response = client.post(
        "/folders/",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"filename": "test_folder"}
    )
    folder_id = folder_response.json()["id"]

    # Upload a file to the folder
    file_content = b"Test file content"
    files = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    data = {"parent_id": folder_id}
    upload_response = client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data=data
    )
    file_id = upload_response.json()["id"]

    # Move file to root
    response = client.patch(
        f"/files/{file_id}/move",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"target_parent_id": None}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["parent_id"] is None 