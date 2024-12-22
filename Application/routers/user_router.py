from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated, List
from ..models import User, UserProfile
from ..schemas import UserResponse, UserProfileCreate, UserCreate, Token, TokenData, UserLogin
from fastapi.security import OAuth2PasswordRequestForm
from ..dependency import (
    get_current_active_user,
    role_required,
    qwert
)
from ..database import get_db
from dotenv import load_dotenv
load_dotenv()
router = APIRouter(prefix="/user")


# user signup
@router.post("/signup", response_model=UserResponse)
async def signup(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """
    Create a new user account
    
    - Checks if username or email already exists
    - Hashes the password
    - Creates a new user in the database
    """
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    try:
        # Create new user
        hashed_password = qwert.get_password_hashed(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse(**new_user.__dict__)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Registration failed: {str(e)}"
        )
    
# User Signin 
@router.post("/login", response_model=Token)
async def login(user_login: Annotated[OAuth2PasswordRequestForm,Depends()], db: Annotated[Session, Depends(get_db)]):
    """
    Authenticate user and return access token
    
    - Verify username/email and password
    - Create and return JWT access token
    """
    print(user_login)
    try:
        # Try to find user by username or email
        print("first",user_login)
        user = (db.query(User)
                .filter((User.username == user_login.username) | 
                        (User.email == user_login.username))
                .first())
        print(user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect username/email or password"
            )
        
        # Verify password
        if not qwert.verify_password(user_login.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect username/email or password"
            )
        access_token = qwert.create_access_token({"user_id":user.id,"username": user.username,"user_email":user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        return {"status":"error","Error":e}

@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    Get the current authenticated user's profile
    """
    return UserResponse(**current_user.__dict__)

@router.put("/profile")
async def update_user_profile(profile_data: UserProfileCreate,current_user: Annotated[User, Depends(get_current_active_user)],db: Session = Depends(get_db)):
    """
    Update or create user profile for the current authenticated user
    """
    existing_profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    try:
        if existing_profile:
            # Update existing profile
            for key, value in profile_data.__dict__(exclude_unset=True).items():
                setattr(existing_profile, key, value)
        else:
            # Create new profile
            new_profile = UserProfile(
                user_id=current_user.id,
                **profile_data.__dict__
            )
            db.add(new_profile)
        
        db.commit()
        return {"message": "Profile updated successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Profile update failed: {str(e)}"
        )

# for delete account permanently
@router.delete("/delete")
async def delete_user(current_user: Annotated[User, Depends(get_current_active_user)],db: Session = Depends(get_db)):
    """
    Delete the current authenticated user's account
    """
    try:
        # Delete associated profile first (if exists)
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if profile:
            db.delete(profile)
        
        # Delete user
        db.delete(current_user)
        db.commit()
        
        return {"message": "User account deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Account deletion failed: {str(e)}"
        )

# # Optional: Admin route to list users (requires admin role)
# @router.get("/list", dependencies=[Depends(role_required(UserRole.ADMIN))])
# async def list_users(
#     db: Session = Depends(get_db),
#     skip: int = 0,
#     limit: int = 100
# ):
#     """
#     List users (Admin only)
    
#     - Requires admin authentication
#     - Supports pagination
#     """
#     users = db.query(User).offset(skip).limit(limit).all()
#     return [UserResponse(**user.__dict__) for user in users]