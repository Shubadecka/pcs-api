"""Authentication route handlers."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import DbSession, CurrentUserId
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
)
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(db: DbSession) -> AuthService:
    """Dependency to get AuthService with repositories."""
    user_repo = UserRepository(db)
    return AuthService(user_repo)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        400: {"description": "Validation error or email already exists"},
        403: {"description": "Email domain not permitted"},
    }
)
async def register(
    request: RegisterRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.
    
    Creates a new user with the provided email, username, and password.
    Returns user information and sets an httpOnly JWT cookie.
    """
    try:
        user, token = await auth_service.register(
            email=request.email,
            username=request.username,
            password=request.password
        )
    except ValueError as e:
        msg = str(e)
        if "email domain" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": msg}
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": msg}
        )
    
    # Set JWT token in httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,  # Set to False in development if not using HTTPS
        samesite="lax",
        max_age=60 * 60 * 24  # 24 hours
    )
    
    return AuthResponse(user=UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        createdAt=user["created_at"]
    ))


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in a user",
    responses={
        401: {"description": "Invalid email or password"},
    }
)
async def login(
    request: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Log in an existing user.
    
    Authenticates user with email and password.
    Returns user information and sets an httpOnly JWT cookie.
    """
    try:
        user, token = await auth_service.login(
            email=request.email,
            password=request.password
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e)}
        )
    
    # Set JWT token in httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24  # 24 hours
    )
    
    return AuthResponse(user=UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        createdAt=user["created_at"]
    ))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out the current user"
)
async def logout(response: Response):
    """
    Log out the current user.
    
    Clears the JWT cookie. Always succeeds even if not logged in.
    """
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return None


@router.get(
    "/me",
    response_model=AuthResponse,
    summary="Get current user",
    responses={
        401: {"description": "Not authenticated"},
    }
)
async def get_me(
    user_id: CurrentUserId,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get the currently logged-in user's information.
    
    Used on app startup to check if user has an active session.
    """
    user = await auth_service.get_current_user(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "User not found"}
        )
    
    return AuthResponse(user=UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        createdAt=user["created_at"]
    ))
