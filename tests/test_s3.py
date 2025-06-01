import boto3
from dotenv import load_dotenv
import os
import pytest

    # Load environment variables
load_dotenv()
    
    # Initialize S3 client
s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
# Get bucket name from environment
bucket_name = os.getenv('S3_BUCKET_NAME')

def test_s3_connection():
    try:
        # List buckets to test connection
        response = s3_client.list_buckets()
        print("Successfully connected to S3!")
        print("Available buckets:", [bucket['Name'] for bucket in response['Buckets']])
        
        # Test bucket access
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Successfully accessed bucket: {bucket_name}")
        
        # Test file upload
        test_content = "Hello, S3!"
        s3_client.put_object(
            Bucket=bucket_name,
            Key='test.txt',
            Body=test_content
        )
        print("Successfully uploaded test file")
        
        # Test file download
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key='test.txt'
        )
        content = response['Body'].read().decode('utf-8')
        print(f"Successfully downloaded test file. Content: {content}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_s3_connection()