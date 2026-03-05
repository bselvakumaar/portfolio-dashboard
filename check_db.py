import os
import secrets
from dotenv import load_dotenv
from app.config import get_settings
from app.auth_service import AuthService

load_dotenv()
settings = get_settings()

try:
    auth = AuthService(
        database_url=settings.trading_database_url,
        database_schema=settings.trading_database_schema,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
        jwt_exp_minutes=settings.jwt_exp_minutes,
        superadmin_email=settings.superadmin_email,
        superadmin_password=settings.superadmin_password,
    )
    print(f"Auth Service Initialized. Superadmin Email: {settings.superadmin_email}")
    user = auth.get_user_by_email(settings.superadmin_email)
    print("User found:")
    print(user)
except Exception as e:
    print(f"Error checking DB: {e}")
