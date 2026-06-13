"""
OAuth endpoints — Google and GitHub.

Flow:
  1. Frontend redirects user to /api/v1/auth/oauth/{provider}
  2. User authenticates with provider
  3. Provider redirects to /api/v1/auth/oauth/{provider}/callback?code=...
  4. We exchange the code, upsert the user, return tokens
"""

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.api.deps import DBDep
from app.config import settings
from app.core.exceptions import BadRequestError
from app.models.user import OAuthProvider
from app.schemas.auth import TokenPair
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])

# ── Google ────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile"


@router.get("/google")
async def google_login() -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise BadRequestError("Google OAuth is not configured.")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.APP_BASE_URL}/api/v1/auth/oauth/google/callback",
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/google/callback", response_model=TokenPair)
async def google_callback(code: str = Query(...), db: DBDep = None) -> TokenPair:  # type: ignore[assignment]
    """Exchange auth code for user info and issue tokens."""
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.APP_BASE_URL}/api/v1/auth/oauth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise BadRequestError("Failed to exchange Google auth code.")
        access_token = token_res.json().get("access_token")

        # Fetch user info
        userinfo_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise BadRequestError("Failed to fetch Google user info.")
        info = userinfo_res.json()

    return await AuthService(db).oauth_login_or_register(
        provider=OAuthProvider.GOOGLE,
        provider_id=info["sub"],
        email=info["email"],
        full_name=info.get("name"),
        avatar_url=info.get("picture"),
    )


# ── GitHub ────────────────────────────────────────────────────────────

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"


@router.get("/github")
async def github_login() -> RedirectResponse:
    """Redirect the user to GitHub's OAuth consent screen."""
    if not settings.GITHUB_CLIENT_ID:
        raise BadRequestError("GitHub OAuth is not configured.")
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{settings.APP_BASE_URL}/api/v1/auth/oauth/github/callback",
        "scope": "read:user user:email",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GITHUB_AUTH_URL}?{query}")


@router.get("/github/callback", response_model=TokenPair)
async def github_callback(code: str = Query(...), db: DBDep = None) -> TokenPair:  # type: ignore[assignment]
    """Exchange auth code for user info and issue tokens."""
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.APP_BASE_URL}/api/v1/auth/oauth/github/callback",
            },
        )
        if token_res.status_code != 200:
            raise BadRequestError("Failed to exchange GitHub auth code.")
        access_token = token_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        # Fetch user profile
        user_res = await client.get(GITHUB_USER_URL, headers=headers)
        user_data = user_res.json()

        # GitHub may not expose email in profile; fetch separately
        email: str | None = user_data.get("email")
        if not email:
            emails_res = await client.get(GITHUB_EMAIL_URL, headers=headers)
            emails = emails_res.json()
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None
            )
            email = primary["email"] if primary else None

    if not email:
        raise BadRequestError("Could not retrieve a verified email from GitHub.")

    return await AuthService(db).oauth_login_or_register(
        provider=OAuthProvider.GITHUB,
        provider_id=str(user_data["id"]),
        email=email,
        full_name=user_data.get("name"),
        avatar_url=user_data.get("avatar_url"),
    )
