import secrets

# Generate a secure random key
secret_key = secrets.token_hex(32)
print("\nGenerated Secret Key:")
print(f"JWT_SECRET_KEY={secret_key}")
print(f"SECRET_KEY={secret_key}")
print("\nAdd these values to your .env file") 