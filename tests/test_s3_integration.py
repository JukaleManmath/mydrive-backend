import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.s3_service import S3Service
import os
from dotenv import load_dotenv
from app.auth import create_access_token
from app.models import User
from app.database import get_db, Base, engine
from app.auth import get_password_hash
import uuid
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

# Initialize test client and S3 service
client = TestClient(app)
s3_service = S3Service()

# Create test database tables
Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def cleanup_s3():
    """Cleanup S3 bucket after each test"""
    yield
    try:
        # List all objects in the bucket
        response = s3_service.s3_client.list_objects_v2(Bucket=s3_service.bucket_name)
        if 'Contents' in response:
            # Delete all objects
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            if objects_to_delete:
                s3_service.s3_client.delete_objects(
                    Bucket=s3_service.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

@pytest.fixture
def test_user():
    # Create a test user with a unique username/email
    db = next(get_db())
    unique_id = str(uuid.uuid4())[:8]
    test_user = User(
        email=f"test_{unique_id}@example.com",
        username=f"testuser_{unique_id}",
        hashed_password=get_password_hash("testpassword")
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    return test_user

@pytest.fixture
def test_user_token(test_user):
    # Create a token for the test user
    return create_access_token({"sub": test_user.id})

def test_s3_service_initialization():
    """Test if S3 service is properly initialized"""
    assert s3_service.bucket_name == os.getenv('S3_BUCKET_NAME')
    assert s3_service.s3_client is not None

def test_s3_bucket_exists():
    """Test if S3 bucket exists"""
    try:
        s3_service.s3_client.head_bucket(Bucket=s3_service.bucket_name)
        assert True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            assert False, "Bucket does not exist"
        elif error_code == '403':
            assert False, "Access denied to bucket"
        else:
            assert False, f"Unexpected error: {str(e)}"

def test_file_upload_to_s3(test_user_token):
    """Test file upload to S3"""
    # Create a test file
    test_content = "This is a test file for S3 integration"
    test_file_path = "test_upload.txt"
    
    try:
        # Upload file to S3
        with open(test_file_path, "w") as f:
            f.write(test_content)
        
        with open(test_file_path, "rb") as f:
            response = client.post(
                "/files/upload",
                files={"file": ("test_upload.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_upload.txt"
        assert data["file_url"].startswith("https://")
        
        # Clean up test file
        os.remove(test_file_path)
        
    except Exception as e:
        print(f"Error in test_file_upload_to_s3: {str(e)}")
        raise

def test_file_download_from_s3(test_user_token):
    """Test file download from S3"""
    try:
        # First upload a file
        test_content = "Test content for download"
        test_file_path = "test_download.txt"
        
        with open(test_file_path, "w") as f:
            f.write(test_content)
        
        with open(test_file_path, "rb") as f:
            upload_response = client.post(
                "/files/upload",
                files={"file": ("test_download.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
        
        file_id = upload_response.json()["id"]
        
        # Now test download
        download_response = client.get(
            f"/files/{file_id}/download",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert download_response.status_code == 200
        assert download_response.content.decode() == test_content
        
        # Clean up
        os.remove(test_file_path)
        
    except Exception as e:
        print(f"Error in test_file_download_from_s3: {str(e)}")
        raise

def test_file_delete_from_s3(test_user_token):
    """Test file deletion from S3"""
    try:
        # First upload a file
        test_content = "Test content for deletion"
        test_file_path = "test_delete.txt"
        
        with open(test_file_path, "w") as f:
            f.write(test_content)
        
        with open(test_file_path, "rb") as f:
            upload_response = client.post(
                "/files/upload",
                files={"file": ("test_delete.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
        
        file_id = upload_response.json()["id"]
        
        # Now test deletion
        delete_response = client.delete(
            f"/files/{file_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "File deleted successfully"
        
        # Verify file is actually deleted
        try:
            s3_service.s3_client.head_object(
                Bucket=s3_service.bucket_name,
                Key=f"uploads/{test_user_token}/test_delete.txt"
            )
            assert False, "File still exists in S3"
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                pass  # File should not exist
            else:
                raise
        
        # Clean up
        os.remove(test_file_path)
        
    except Exception as e:
        print(f"Error in test_file_delete_from_s3: {str(e)}")
        raise

def test_list_files(test_user_token):
    """Test listing files from S3"""
    try:
        # Upload multiple test files
        test_files = [
            ("test_file1.txt", "Content 1"),
            ("test_file2.txt", "Content 2"),
            ("test_file3.txt", "Content 3")
        ]
        
        for filename, content in test_files:
            with open(filename, "w") as f:
                f.write(content)
            
            with open(filename, "rb") as f:
                client.post(
                    "/files/upload",
                    files={"file": (filename, f, "text/plain")},
                    headers={"Authorization": f"Bearer {test_user_token}"}
                )
            
            os.remove(filename)
        
        # Test listing files
        list_response = client.get(
            "/files",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert list_response.status_code == 200
        data = list_response.json()
        assert isinstance(data, list)
        assert len(data) >= len(test_files)
        
        # Verify file names are in the response
        file_names = [item["name"] for item in data]
        for filename, _ in test_files:
            assert filename in file_names
            
    except Exception as e:
        print(f"Error in test_list_files: {str(e)}")
        raise
