from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import jwt
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.entities import User

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency that extracts and validates the Bearer JWT token,
    returning the authenticated User entity.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject (user_id)",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.user_id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

class RoleChecker:
    """
    Role-Based Access Control (RBAC) dependency.
    Validates user has at least one of the allowed roles.
    ADMIN role has omnipotent access across all endpoints.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = set(allowed_roles)

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role == "ADMIN":
            return user
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user.role}' lacks required permissions. Required: {list(self.allowed_roles)}"
            )
        return user

def require_admin(user: User = Depends(RoleChecker(["ADMIN"]))) -> User:
    return user

def require_supervisor(user: User = Depends(RoleChecker(["ADMIN", "SUPERVISOR"]))) -> User:
    return user

def require_agent_or_above(user: User = Depends(RoleChecker(["ADMIN", "SUPERVISOR", "AGENT"]))) -> User:
    return user

def verify_tenant_access(target_tenant_id: str, current_user: User) -> None:
    """
    Enforces multi-tenant data isolation.
    Users cannot access resources belonging to another tenant unless they possess the ADMIN role.
    """
    if current_user.role == "ADMIN":
        return
    if target_tenant_id and current_user.tenant_id != target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-tenant access forbidden: User tenant '{current_user.tenant_id}' cannot access resource tenant '{target_tenant_id}'"
        )
