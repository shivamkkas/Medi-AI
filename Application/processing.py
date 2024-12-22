from sqlalchemy.orm import Session
from . import models
import json
from .schemas import UserResponse,TokenData
from datetime import timedelta, datetime, timezone
import jwt
from jose import JWTError
from dotenv import load_dotenv
import os
import secrets
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials,OAuth2PasswordBearer
load_dotenv()

class jwt_process:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=['bcrypt'],deprecated='auto')
        self.oauth_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/user/login")
        self.SECRET_KEY = os.getenv("SECRET_KEY")
        self.ALGORITHM = os.getenv("ALGORITHM") 
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
        
        # Password complexity requirements
        self.MIN_PASSWORD_LENGTH = 8
        self.REQUIRED_COMPLEXITY = {
            'uppercase': 1,
            'lowercase': 1,
            'digits': 1,
            'special_chars': 1
        }

    def _generate_or_load_secret_key(self):
        """
        Generate a new secret key if not exists, or load existing
        Stores in environment or .env file for persistence
        """
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            secret_key = secrets.token_hex(32)  # 256-bit key
            # Update .env file or environment variable
            with open('.env', 'a') as f:
                f.write(f"\nSECRET_KEY={secret_key}")
        return secret_key

    def verify_password(self, plain_password, hashed_password):
        """
        Verify password with additional logging and security checks
        """
        if not plain_password or not hashed_password:
            return False
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except ValueError:
            # Log failed password verification attempts
            print(f"Password verification failed for user")
            return False

    def validate_password_complexity(self, password):
        """
        Enforce password complexity requirements
        """
        if len(password) < self.MIN_PASSWORD_LENGTH:
            return False
        
        complexity_checks = {
            'uppercase': any(c.isupper() for c in password),
            'lowercase': any(c.islower() for c in password),
            'digits': any(c.isdigit() for c in password),
            'special_chars': any(not c.isalnum() for c in password)
        }
        
        return all(complexity_checks[key] for key in self.REQUIRED_COMPLEXITY)

    def get_password_hashed(self, password):
        """
        Enhanced password hashing with complexity check
        """
        # if not self.validate_password_complexity(password):
        #     raise ValueError("Password does not meet complexity requirements")
        
        return self.pwd_context.hash(password)

    def get_user(self, username: str, db: Session):
        """
        Retrieve user with enhanced error handling
        """
        try:
            user = db.query(models.User).filter(models.User.username == username).first()
            if user:
                return json(**user.__dict__)
            return None
        except Exception as e:
            # Log the error
            print(f"Error retrieving user {username}: {e}")
            return None

    def authenticate_user(self, username: str, password: str, db: Session):
        """
        Enhanced user authentication with additional checks
        """
        if not username or not password:
            return False
        
        user = self.get_user(username, db)
        print(user)
        if not user:
            return False
        
        # Additional checks can be added here (e.g., account lockout)
        if not self.verify_password(password, user.hashed_password):
            # Optionally: Implement login attempt tracking
            return False
        
        return user

    def create_access_token(self,data:dict):
          to_encode = data.copy()
          expire = datetime.now(timezone.utc) + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
          to_encode.update({"exp": expire})
          encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
          return encoded_jwt

        
    def verify_access_token(self,token: str, credentials_exception):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            user_id: str = payload.get("user_id")
            user_email: str = payload.get("user_email")
            username: str = payload.get("username")

            if user_id is None or user_email is None or username is None:
                raise credentials_exception
            print(user_id,user_email,username)
            return TokenData(user_id=str(user_id),username=username, email=user_email)
        except JWTError:
            raise credentials_exception

        
          