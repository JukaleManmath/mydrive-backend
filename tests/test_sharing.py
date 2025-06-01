import pytest
from fastapi import status
import io

def test_share_file(client, test_user_token, test_user2):
    # First upload a file
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

    # Share the file
    response = client.post(
        f"/files/{file_id}/share",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"shared_with_email": "test2@example.com", "permission": "read"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["file_id"] == file_id
    assert data["shared_with"] == "test2@example.com"
    assert data["permission"] == "read"

def test_share_file_no_auth(client, test_user2):
    response = client.post(
        "/files/1/share",
        json={"shared_with_email": "test2@example.com", "permission": "read"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_share_nonexistent_file(client, test_user_token, test_user2):
    response = client.post(
        "/files/999/share",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"shared_with_email": "test2@example.com", "permission": "read"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_share_with_nonexistent_user(client, test_user_token):
    # First upload a file
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

    # Try to share with nonexistent user
    response = client.post(
        f"/files/{file_id}/share",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"shared_with_email": "nonexistent@example.com", "permission": "read"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_share_file_unauthorized(client, test_user_token, test_user2_token):
    # First upload a file with test_user
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

    # Try to share with test_user2
    response = client.post(
        f"/files/{file_id}/share",
        headers={"Authorization": f"Bearer {test_user2_token}"},
        json={"shared_with_email": "test@example.com", "permission": "read"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_shared_files(client, test_user_token, test_user2_token):
    # First upload a file
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

    # Share the file
    client.post(
        f"/files/{file_id}/share",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"shared_with_email": "test2@example.com", "permission": "read"}
    )

    # Get shared files for test_user2
    response = client.get(
        "/files/shared-with-me",
        headers={"Authorization": f"Bearer {test_user2_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "test.txt"
    assert data[0]["type"] == "file"
    assert data[0]["is_shared"] == True

def test_get_shared_files_no_auth(client):
    response = client.get("/files/shared-with-me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_share_folder(client, test_user_token, test_user2_token):
    # First create a folder
    folder_response = client.post(
        "/files/folders",
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
    client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data=data
    )

    # Share the folder
    response = client.post(
        f"/files/{folder_id}/share",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"shared_with_email": "test2@example.com", "permission": "read"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["file_id"] == folder_id
    assert data["shared_with"] == "test2@example.com"
    assert data["permission"] == "read"

    # Verify test_user2 can access the file in the shared folder
    shared_files_response = client.get(
        "/files/shared-with-me",
        headers={"Authorization": f"Bearer {test_user2_token}"}
    )
    assert shared_files_response.status_code == status.HTTP_200_OK
    shared_data = shared_files_response.json()
    assert len(shared_data) == 1
    assert shared_data[0]["filename"] == "test.txt"
    assert shared_data[0]["type"] == "file"
    assert shared_data[0]["is_shared"] == True

def test_recent_shared_files(client, test_user_token, test_user2_token):
    # First upload a file
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

    # Share the file
    client.post(
        f"/files/{file_id}/share",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"shared_with_email": "test2@example.com", "permission": "read"}
    )

    # Get recent shared files for test_user2
    response = client.get(
        "/files/recent-shared",
        headers={"Authorization": f"Bearer {test_user2_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "test.txt"
    assert data[0]["type"] == "file"
    assert data[0]["is_shared"] == True 