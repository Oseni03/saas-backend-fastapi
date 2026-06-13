from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    billing,
    health,
    mfa,
    notifications,
    oauth,
    organizations,
    users,
)

router = APIRouter(prefix="/v1")

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(oauth.router)
router.include_router(mfa.router)
router.include_router(users.router)
router.include_router(organizations.router)
router.include_router(billing.router)
router.include_router(notifications.router)
router.include_router(admin.router)
