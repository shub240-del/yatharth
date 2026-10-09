import jwt
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from app.models import now

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash('dummy-not-a-login-password')

def verify(password, encoded):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False

def token(user_id, settings):
    return jwt.encode({'sub': user_id, 'iat': now(), 'exp': now() + timedelta(minutes=settings.token_minutes), 'iss': 'yatharth', 'aud': 'yatharth-api'}, settings.jwt_secret, algorithm='HS256')
