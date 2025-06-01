import pytest
from fastapi import status
import io

def test_create_version(client, test_user_token):
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

    # Create a new version
    new_content = b"Updated test file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    response = client.post(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data={"comment": "Updated version"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["version_number"] == 2
    assert data["comment"] == "Updated version"

def test_create_version_no_auth(client):
    files = {
        "file": ("test.txt", io.BytesIO(b"Test content"), "text/plain")
    }
    response = client.post(
        "/files/1/versions",
        files=files
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_version_nonexistent_file(client, test_user_token):
    new_content = b"Updated file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    response = client.post(
        "/files/999/versions",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_create_version_unauthorized(client, test_user_token, test_user2_token):
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

    # Try to create version with test_user2
    new_content = b"Updated test file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    response = client.post(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user2_token}"},
        files=files
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_versions(client, test_user_token):
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

    # Create a new version
    new_content = b"Updated test file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    client.post(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data={"comment": "Updated version"}
    )

    # Get versions
    response = client.get(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["version_number"] == 1
    assert data[1]["version_number"] == 2
    assert data[1]["comment"] == "Updated version"

def test_get_versions_no_auth(client):
    response = client.get("/files/1/versions")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_versions_nonexistent_file(client, test_user_token):
    response = client.get(
        "/files/999/versions",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_version_content(client, test_user_token):
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

    # Create a new version
    new_content = b"Updated test file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    client.post(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data={"comment": "Updated version"}
    )

    # Get version content
    response = client.get(
        f"/files/{file_id}/versions/1/content",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.content == file_content

def test_get_version_content_no_auth(client):
    response = client.get("/files/1/versions/1/content")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_version_content_nonexistent_file(client, test_user_token):
    response = client.get(
        "/files/999/versions/1/content",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_version_content_nonexistent_version(client, test_user_token):
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

    # Try to get nonexistent version
    response = client.get(
        f"/files/{file_id}/versions/2/content",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_restore_version(client, test_user_token):
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

    # Create a new version
    new_content = b"Updated test file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    client.post(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data={"comment": "Updated version"}
    )

    # Restore to version 1
    response = client.post(
        f"/files/versions/1/restore",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["version_number"] == 3  # New version created from restore

def test_delete_version(client, test_user_token):
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

    # Create a new version
    new_content = b"Updated test file content"
    files = {
        "file": ("test.txt", io.BytesIO(new_content), "text/plain")
    }
    version_response = client.post(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"},
        files=files,
        data={"comment": "Updated version"}
    )
    version_number = version_response.json()["version_number"]

    # Delete version
    response = client.delete(
        f"/files/{file_id}/versions/{version_number}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == status.HTTP_200_OK

    # Verify version is deleted
    versions_response = client.get(
        f"/files/{file_id}/versions",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert versions_response.status_code == status.HTTP_200_OK
    versions = versions_response.json()
    assert len(versions) == 1  # Only initial version remains 