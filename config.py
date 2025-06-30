import os
import secrets

MONGO_URI = os.environ.get("MONGO_URI")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_default_secret")

print(secrets.token_hex(24)) 