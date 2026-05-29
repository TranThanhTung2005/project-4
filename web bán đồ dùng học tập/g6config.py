import os
import secrets
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "edustore-dev-secret-key")
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    RUNTIME_SESSION_TOKEN = secrets.token_hex(16)

    # DB config
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_SERVER = os.getenv("DB_SERVER", r"localhost\SQLEXPRESS01")
    DB_DATABASE = os.getenv("DB_DATABASE", "EduStore")

    # Không dùng username/password
    DB_TRUSTED_CONNECTION = os.getenv("DB_TRUSTED_CONNECTION", "yes")

    # QUAN TRỌNG: tắt encrypt
    DB_ENCRYPT = os.getenv("DB_ENCRYPT", "no")
    DB_TRUST_SERVER_CERTIFICATE = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")

    # Auth bằng Windows
    AUTH_PART = f"Trusted_Connection={DB_TRUSTED_CONNECTION};"

    ENCRYPT_PART = f"Encrypt={DB_ENCRYPT};TrustServerCertificate={DB_TRUST_SERVER_CERTIFICATE};"

    CONN_STR = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        f"{AUTH_PART}"
        f"{ENCRYPT_PART}"
    )

    # Account demo
    USER_LOGIN_EMAIL = os.getenv("USER_LOGIN_EMAIL", "user@edustore.local")
    USER_LOGIN_PASSWORD = os.getenv("USER_LOGIN_PASSWORD", "user123")
    USER_LOGIN_NAME = os.getenv("USER_LOGIN_NAME", "Khách hàng")

    ADMIN_LOGIN_EMAIL = os.getenv("ADMIN_LOGIN_EMAIL", "admin@edustore.local")
    ADMIN_LOGIN_PASSWORD = os.getenv("ADMIN_LOGIN_PASSWORD", "admin123")
    ADMIN_LOGIN_NAME = os.getenv("ADMIN_LOGIN_NAME", "Quản trị viên")

    # MB Bank QR payment config. Thay các giá trị này bằng tài khoản nhận tiền thật khi triển khai.
    MB_BANK_ACCOUNT_NUMBER = os.getenv("MB_BANK_ACCOUNT_NUMBER", "0123456789")
    MB_BANK_ACCOUNT_NAME = os.getenv("MB_BANK_ACCOUNT_NAME", "EDUSTORE")
