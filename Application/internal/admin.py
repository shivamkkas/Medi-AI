from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy.orm import Session
from typing import List, Dict
from enum import Enum

from ..models import User
from ..database import get_db
from ..schemas import UserCreate, UserResponse
from ..processing import jwt_process 
from ..schemas import UserRole
from ..dependency import qwert,get_current_user


class Authorization:
    pwd_context = qwert.pwd_context

    @staticmethod
    def check_user_permission(required_roles: List[UserRole], current_user: User) -> bool:
        """
        Check if user has required roles, with SUPERADMIN having full access
        """
        return (
            current_user.role in required_roles or 
            current_user.role == UserRole.SUPERADMIN
        )

    @staticmethod
    def get_user_permissions(user: User) -> Dict[str, bool]:
        """
        Generate comprehensive permissions for a user
        Superadmin gets full permissions by default
        """
        is_superadmin = user.role == UserRole.SUPERADMIN
        
        permissions = {
            "can_view_profile": True,
            "can_edit_profile": user.role in [UserRole.USER, UserRole.ADMIN, UserRole.SUPERADMIN],
            "can_create_records": user.role in [UserRole.USER, UserRole.ADMIN, UserRole.SUPERADMIN],
            "can_delete_records": user.role in [UserRole.ADMIN, UserRole.SUPERADMIN],
            "can_manage_users": user.role in [UserRole.ADMIN, UserRole.SUPERADMIN],
            "is_superadmin": is_superadmin
        }
        return permissions

def authorize_user(
    required_roles: List[UserRole] = [UserRole.USER],
    check_active: bool = True,
    superadmin_override: bool = True
):
    """
    Dependency for role-based authorization with optional superadmin override
    """
    def authorization_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        # Check if user is active
        if check_active and not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Superadmin override if enabled
        if superadmin_override and current_user.role == UserRole.SUPERADMIN:
            return current_user
        
        # Check user roles
        if not Authorization.check_user_permission(required_roles, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return authorization_dependency

# Admin and Superadmin Signup Router
router = APIRouter()

@router.post("/admin-signup")
def admin_signup(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Signup route for creating admin accounts
    Only accessible by SUPERADMIN
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    # Create new admin user
    new_user = User(
        email=user_data.email,
        hashed_password=qwert.get_password_hashed(user_data.password),
        role=UserRole.ADMIN,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Admin account created successfully"}

@router.post("/superadmin-signup")
def superadmin_signup(
    user_data: UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Initial superadmin signup
    Can only be done if no superadmin exists
    """
    # Check if any superadmin already exists
    existing_superadmin = db.query(User).filter(User.role == UserRole.SUPERADMIN).first()
    if existing_superadmin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Superadmin already exists. Contact system administrator."
        )
    
    # Create superadmin user
    new_superadmin = User(
        email=user_data.email,
        hashed_password=qwert.get_password_hashed(user_data.password),
        role=UserRole.SUPERADMIN,
        is_active=True
    )
    
    db.add(new_superadmin)
    db.commit()
    db.refresh(new_superadmin)
    
    return {"message": "Superadmin account created successfully"}

# Superadmin-specific routes
@router.get("/superadmin-dashboard")
def superadmin_dashboard(
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Superadmin dashboard with full system insights
    """
    return {
        "message": "Welcome to Superadmin Dashboard",
        "permissions": Authorization.get_user_permissions(current_user)
    }

# Additional Superadmin Management Routes
@router.get("/system-overview")
def system_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Get comprehensive system overview
    """
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admins = db.query(User).filter(User.role == UserRole.ADMIN).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_count": admins,
        "system_health": "Operational"
    }


from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr, Field

from ..models import User
from ..database import get_db
from ..schemas import UserCreate, UserResponse
from ..dependency import get_current_user

class SuperAdminManagement:
    @staticmethod
    def create_user(
        db: Session, 
        username: str,
        email: str, 
        password: str, 
        role: UserRole = UserRole.USER,
        is_active: bool = True
    ):
        """
        Create a new user with specified role
        Only callable by SuperAdmin
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {email} already exists"
            )
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            hashed_password=qwert.get_password_hashed(password),
            role=role,
            is_active=is_active
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user

    @staticmethod
    def update_user(
        db: Session, 
        user_id: int, 
        updates: Dict[str, Any]
    ):
        """
        Update user details by SuperAdmin
        Allows updating email, role, active status, etc.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Apply updates
        for key, value in updates.items():
            if key == 'password':
                # Special handling for password
                user.hashed_password = qwert.get_password_hashed(value)
            elif hasattr(user, key):
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        
        return user

    @staticmethod
    def delete_user(
        db: Session, 
        user_id: int
    ):
        """
        Permanently delete a user by SuperAdmin
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db.delete(user)
        db.commit()
        
        return {"message": "User deleted successfully"}

    @staticmethod
    def get_all_users(
        db: Session, 
        role: Optional[UserRole] = None
    ):
        """
        Retrieve all users with optional role filtering
        """
        if role:
            users = db.query(User).filter(User.role == role).all()
        else:
            users = db.query(User).all()
        
        return [
            {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active
            } for user in users
        ]

    @staticmethod
    def system_diagnostics(db: Session):
        """
        Comprehensive system diagnostics and overview
        """
        return {
            "total_users": db.query(User).count(),
            "user_breakdown": {
                role.value: db.query(User).filter(User.role == role).count()
                for role in UserRole
            },
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "inactive_users": db.query(User).filter(User.is_active == False).count(),
            "system_status": "Fully Operational"
        }



class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

@router.post("/create-user", response_model=UserResponse)
def create_new_user(
    user_data: UserCreate,
    role: UserRole = UserRole.USER,
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Create a new user with specified role
    Only accessible by SuperAdmin
    """
    new_user = SuperAdminManagement.create_user(
        db, 
        user_data.username,
        user_data.email, 
        user_data.password, 
        role
    )
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role,
        is_active=new_user.is_active
    )

@router.put("/update-user/{user_id}")
def update_existing_user(
    user_id: int,
    user_updates: UserUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Update user details by SuperAdmin
    """
    # Convert Pydantic model to dictionary, removing None values
    update_dict = {
        k: v for k, v in user_updates.dict().items() 
        if v is not None
    }
    
    updated_user = SuperAdminManagement.update_user(
        db, 
        user_id, 
        update_dict
    )
    
    return {
        "message": "User updated successfully",
        "user": {
            "id": updated_user.id,
            "email": updated_user.email,
            "role": updated_user.role,
            "is_active": updated_user.is_active
        }
    }

@router.delete("/delete-user/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Delete a user by SuperAdmin
    """
    return SuperAdminManagement.delete_user(db, user_id)

@router.get("/all-users")
def list_all_users(
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Retrieve all users with optional role filtering
    """
    return SuperAdminManagement.get_all_users(db, role)

@router.get("/system-diagnostics")
def get_system_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(authorize_user([UserRole.SUPERADMIN]))
):
    """
    Get comprehensive system diagnostics
    """
    return SuperAdminManagement.system_diagnostics(db)

# Initial SuperAdmin Creation Endpoint (One-time setup)
@router.post("/initialize-superadmin")
def initialize_superadmin(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    One-time endpoint to create the first SuperAdmin
    Can only be used if no SuperAdmin exists
    """
    # Check if a SuperAdmin already exists
    existing_superadmin = db.query(User).filter(User.role == UserRole.SUPERADMIN).first()
    if existing_superadmin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SuperAdmin already exists. Contact system administrator."
        )
    
    # Create SuperAdmin
    new_superadmin = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=qwert.get_password_hashed(user_data.password),
        role=UserRole.SUPERADMIN,
        is_active=True
    )
    
    db.add(new_superadmin)
    db.commit()
    db.refresh(new_superadmin)
    
    return {
        "message": "SuperAdmin created successfully",
        "user": {
            "id": new_superadmin.id,
            "email": new_superadmin.email
        }
    }