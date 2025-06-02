import boto3
import os
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')
        logger.info(f"Initialized S3 service with bucket: {self.bucket_name}")
        
        # Configure CORS for the bucket
        cors_configuration = {
            'CORSRules': [{
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedOrigins': [
                    'https://mydrive-frontend.vercel.app',
                    'https://mydrive-frontend-git-main-jukalemanmath.vercel.app',
                    'https://mydrive-frontend-jukalemanmath.vercel.app',
                    'http://localhost:3000'
                ],
                'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type', 'Content-Disposition'],
                'MaxAgeSeconds': 3600
            }]
        }
        logger.info(f"Configuring CORS for S3 bucket with origins: {cors_configuration['CORSRules'][0]['AllowedOrigins']}")
        try:
            self.s3_client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_configuration
            )
            logger.info("CORS configuration applied successfully")
        except Exception as e:
            logger.error(f"Error configuring CORS: {str(e)}")

    def upload_file(self, file: BinaryIO, file_name: str, user_id: str) -> str:
        """Upload a file to S3"""
        try:
            key = f"uploads/{user_id}/{file_name}"
            logger.info(f"Uploading file to S3: {key}")
            self.s3_client.upload_fileobj(file, self.bucket_name, key)
            logger.info(f"File uploaded successfully to S3: {key}")
            return key
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise Exception(f"Error uploading file to S3: {str(e)}")

    def download_file(self, key: str) -> bytes:
        """Download a file from S3"""
        try:
            logger.info(f"Downloading file from S3: {key}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read()
            logger.info(f"File downloaded successfully from S3: {key}")
            return content
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            raise Exception(f"Error downloading file from S3: {str(e)}")

    def delete_file(self, key: str) -> bool:
        """Delete a file from S3"""
        try:
            logger.info(f"Deleting file from S3: {key}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File deleted successfully from S3: {key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            raise Exception(f"Error deleting file from S3: {str(e)}")

    def get_file_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for a file"""
        try:
            logger.info(f"Generating presigned URL for file: {key}")
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ResponseContentDisposition': f'inline; filename="{os.path.basename(key)}"',
                    'ResponseContentType': self._get_content_type(key)
                },
                ExpiresIn=expires_in
            )
            logger.info(f"Generated presigned URL successfully for file: {key}")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise Exception(f"Error generating presigned URL: {str(e)}")

    def _get_content_type(self, key: str) -> str:
        """Get the content type based on file extension"""
        ext = os.path.splitext(key)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.py': 'text/x-python',
            '.java': 'text/x-java',
            '.cpp': 'text/x-c++',
            '.c': 'text/x-c',
            '.php': 'text/x-php',
            '.rb': 'text/x-ruby',
            '.swift': 'text/x-swift'
        }
        return content_types.get(ext, 'application/octet-stream')

    def get_file_size(self, key: str) -> int:
        """Get file size in bytes from S3"""
        try:
            logger.info(f"Getting file size from S3: {key}")
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            size = response['ContentLength']
            logger.info(f"File size: {size} bytes")
            return size
        except ClientError as e:
            logger.error(f"Error getting file size from S3: {str(e)}")
            raise Exception(f"Error getting file size from S3: {str(e)}")

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3"""
        try:
            logger.info(f"Checking if file exists in S3: {key}")
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Error checking file existence in S3: {str(e)}") 