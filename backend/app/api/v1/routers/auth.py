"""Authentication routes for user registration, login, and token management."""

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import settings
from app.core.dependencies import get_auth_service, limiter
from app.schemas.auth import (
    AuthResponse,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("5/hour")  # 5 registrations per hour per IP
async def register(
    request: Request,
    user_request: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    """
    Register a new user account with email and password.

    Rate limit: 5 requests per hour per IP address.

    Returns:
    - **201 Created**: User successfully registered with tokens
    - **409 Conflict**: Email already exists
    - **422 Unprocessable Entity**: Validation error (weak password, invalid email, etc.)
    - **429 Too Many Requests**: Rate limit exceeded
    """
    try:
        result = await auth_service.register(
            email=user_request.email,
            password=user_request.password,
            display_name=user_request.display_name,
        )

        return AuthResponse(
            user=UserResponse.model_validate(result.user),
            tokens=TokenResponse(
                access_token=result.access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            ),
        )
    except UserAlreadyExistsError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
@limiter.limit("10/15minutes")  # 10 login attempts per 15 minutes per IP
async def login(
    request: Request,
    response: Response,
    user_request: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    """
    Authenticate user with email and password.

    Rate limit: 10 requests per 15 minutes per IP address.

    Sets httpOnly cookie with refresh token for security.

    Returns:
    - **200 OK**: Successfully authenticated with tokens
    - **401 Unauthorized**: Invalid credentials
    - **403 Forbidden**: User account is inactive
    - **429 Too Many Requests**: Rate limit exceeded
    """
    try:
        result = await auth_service.login(
            email=user_request.email,
            password=user_request.password,
        )

        # Set refresh token in httpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 86400,
        )

        return AuthResponse(
            user=UserResponse.model_validate(result.user),
            tokens=TokenResponse(
                access_token=result.access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            ),
        )
    except InvalidCredentialsError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    except UserInactiveError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using refresh token",
)
@limiter.limit("30/hour")  # 30 refresh requests per hour per IP
async def refresh(
    request: Request,
    response: Response,
    refresh_request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    """
    Exchange refresh token for new access and refresh tokens.

    Rate limit: 30 requests per hour per IP address.

    Implements token rotation - old refresh token is invalidated.
    Sets new refresh token in httpOnly cookie.

    Returns:
    - **200 OK**: New token pair generated
    - **401 Unauthorized**: Invalid or expired refresh token
    - **403 Forbidden**: User account is inactive
    - **429 Too Many Requests**: Rate limit exceeded
    """
    try:
        result = await auth_service.refresh_tokens(refresh_request.refresh_token)

        # Set new refresh token in httpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 86400,
        )

        return RefreshResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
    except InvalidTokenError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    except UserInactiveError:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    except UserNotFoundError:
        from fastapi import HTTPException

        # Return 401 instead of 404 for security (don't confirm user existed)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
