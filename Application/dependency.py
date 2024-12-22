from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated
from sqlalchemy import and_
from .models import User
from .database import get_db
from .models import User, UserRole
from .processing import jwt_process
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated
import os
qwert = jwt_process()
oauth2_scheme = qwert.oauth_scheme
# Dependency to check user role
def role_required(required_roles: list[UserRole]):
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

# Current user retrieval with enhanced role checks
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
         # You might need to adjust this initialization
        payload = qwert.verify_access_token(token,credentials_exception)
        if not payload:
            raise credentials_exception
        
        username: str = payload.username
        user_id: str = payload.user_id
        user_email: str = payload.email
        if username is None or user_id is None or user_email is None:
            raise credentials_exception
        
        # Retrieve full user details including role
        user = db.query(User).filter(and_(User.username == username,User.email == user_email,User.id == user_id)).first()
        if user is None:
            raise credentials_exception
        
        return user
    except Exception:
        raise credentials_exception

# Active user dependency
async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if not current_user.is_active:
        print("Hello")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

# Additional utility functions for role-based access
def is_admin(user: User):
    return user.role == UserRole.ADMIN

def is_active_user(user: User):
    return user.is_active


class OAuth2Configuration:
    """
    Centralized OAuth2 Authentication Configuration
    """
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

def configure_swagger_authentication(app: FastAPI):
    """
    Configure Swagger UI to support OAuth2 authentication
    """
    app.swagger_ui_oauth2_redirect_url = "/docs/oauth2-redirect"
    app.swagger_ui_init_oauth = {
        "clientId": "swagger-ui-client",
        "clientSecret": "swagger-ui-client-secret",
        "appName": "Health Care System",
        "scopeSeparator": " ",
        "scopes": "openid profile email",
        "additionalQueryStringParams": {}
    }