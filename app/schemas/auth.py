"""Auth schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.config import project
from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=project.password.min_length, max_length=project.password.max_length)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if project.password.require_uppercase and not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if project.password.require_digit and not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = project.token_type


class MfaPendingResponse(BaseModel):
    mfa_pending: str
    expires_in: int


class LoginResponse(TokenPair):
    user: UserResponse


class SignupResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = project.token_type


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=project.password.min_length, max_length=project.password.max_length)
