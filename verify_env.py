import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\nVerifying Environment Variables:")
print("-" * 30)

# Check JWT Configuration
jwt_key = os.getenv("JWT_SECRET_KEY")
secret_key = os.getenv("SECRET_KEY")
print(f"JWT_SECRET_KEY loaded: {'Yes' if jwt_key else 'No'}")
print(f"SECRET_KEY loaded: {'Yes' if secret_key else 'No'}")
print(f"Keys match: {'Yes' if jwt_key == secret_key else 'No'}")

# Check AWS Configuration
aws_access = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")
s3_bucket = os.getenv("S3_BUCKET_NAME")

print("\nAWS Configuration:")
print(f"AWS_ACCESS_KEY_ID loaded: {'Yes' if aws_access else 'No'}")
print(f"AWS_SECRET_ACCESS_KEY loaded: {'Yes' if aws_secret else 'No'}")
print(f"AWS_REGION loaded: {'Yes' if aws_region else 'No'}")
print(f"S3_BUCKET_NAME loaded: {'Yes' if s3_bucket else 'No'}")

# Check Database Configuration
db_url = os.getenv("DATABASE_URL")
print("\nDatabase Configuration:")
print(f"DATABASE_URL loaded: {'Yes' if db_url else 'No'}") 