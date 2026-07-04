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
from app.config import project, settings
from app.core.exceptions import BadRequestError
from app.models.user import OAuthProvider
from app.schemas.auth import TokenPair
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])

# ── Google ────────────────────────────────────────────────────────────


@router.get("/google")
async def google_login() -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise BadRequestError("Google OAuth is not configured.")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.APP_BASE_URL}{project.api_prefix}/auth/oauth/google/callback",
        "response_type": "code",
        "scope": project.oauth.google.scope,
        "access_type": project.oauth.google.access_type,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{project.oauth.google.auth_url}?{query}")


@router.get("/google/callback", response_model=TokenPair)
async def google_callback(code: str = Query(...), db: DBDep = None) -> TokenPair:  # type: ignore[assignment]
    """Exchange auth code for user info and issue tokens."""
    redirect_uri = f"{settings.APP_BASE_URL}{project.api_prefix}/auth/oauth/google/callback"
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            project.oauth.google.token_url,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise BadRequestError("Failed to exchange Google auth code.")
        access_token = token_res.json().get("access_token")

        userinfo_res = await client.get(
            project.oauth.google.userinfo_url,
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


@router.get("/github")
async def github_login() -> RedirectResponse:
    """Redirect the user to GitHub's OAuth consent screen."""
    if not settings.GITHUB_CLIENT_ID:
        raise BadRequestError("GitHub OAuth is not configured.")
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{settings.APP_BASE_URL}{project.api_prefix}/auth/oauth/github/callback",
        "scope": project.oauth.github.scope,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{project.oauth.github.auth_url}?{query}")


@router.get("/github/callback", response_model=TokenPair)
async def github_callback(code: str = Query(...), db: DBDep = None) -> TokenPair:  # type: ignore[assignment]
    """Exchange auth code for user info and issue tokens."""
    redirect_uri = f"{settings.APP_BASE_URL}{project.api_prefix}/auth/oauth/github/callback"
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            project.oauth.github.token_url,
            headers={"Accept": project.oauth.github.accept_header},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        if token_res.status_code != 200:
            raise BadRequestError("Failed to exchange GitHub auth code.")
        access_token = token_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": project.oauth.github.accept_header}

        user_res = await client.get(project.oauth.github.user_url, headers=headers)
        user_data = user_res.json()

        email: str | None = user_data.get("email")
        if not email:
            emails_res = await client.get(project.oauth.github.emails_url, headers=headers)
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
