"""
Transactional email via Resend.
All email types are defined here as typed functions.
"""

import resend

from app.config import project, settings
from app.lib.logger import logger

resend.api_key = settings.RESEND_API_KEY


def _send(to: str, subject: str, html: str) -> None:
    if not settings.RESEND_API_KEY:
        logger.info("email.logged", to=to, subject=subject, html=html)
        print(f"\n{'='*60}\nTO: {to}\nSUBJECT: {subject}\nHTML:\n{html}\n{'='*60}\n")
        return
    try:
        resend.Emails.send(
            {
                "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        logger.info("email.sent", to=to, subject=subject)
    except Exception as exc:
        logger.error("email.failed", to=to, subject=subject, error=str(exc))
        raise


def send_verification_email(to: str, full_name: str, token: str) -> None:
    url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    _send(
        to=to,
        subject=f"Verify your email — {settings.APP_NAME}",
        html=f"""
        <h2>Welcome to {settings.APP_NAME}, {full_name or 'there'}!</h2>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{url}" style="padding:10px 20px;background:#4F46E5;color:white;
           border-radius:6px;text-decoration:none;">Verify Email</a></p>
        <p>This link expires in {project.expiry.verification_hours} hours.</p>
        """,
    )


def send_password_reset_email(to: str, token: str) -> None:
    url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    _send(
        to=to,
        subject=f"Reset your password — {settings.APP_NAME}",
        html=f"""
        <h2>Password Reset</h2>
        <p>Click the link below to reset your password. This link expires in {project.expiry.password_reset_hours} hour(s).</p>
        <p><a href="{url}" style="padding:10px 20px;background:#4F46E5;color:white;
           border-radius:6px;text-decoration:none;">Reset Password</a></p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """,
    )


def send_invitation_email(
    to: str, invited_by: str, org_name: str, token: str, role: str
) -> None:
    try:
        url = f"{settings.FRONTEND_URL}/invitations/accept?token={token}"
        _send(
            to=to,
            subject=f"{invited_by} invited you to {org_name}",
            html=f"""
            <h2>You've been invited!</h2>
            <p><strong>{invited_by}</strong> has invited you to join
            <strong>{org_name}</strong> as a <strong>{role}</strong>.</p>
            <p><a href="{url}" style="padding:10px 20px;background:#4F46E5;color:white;
            border-radius:6px;text-decoration:none;">Accept Invitation</a></p>
            <p>This invitation expires in {project.expiry.invitation_days} days.</p>
            """,
        )
    except:
        logger.exception("Failed to send verification email", to=to)


def send_welcome_email(to: str, full_name: str) -> None:
    _send(
        to=to,
        subject=f"Welcome to {settings.APP_NAME}!",
        html=f"""
        <h2>Welcome aboard, {full_name or 'there'}! 🎉</h2>
        <p>Your account is all set. Here's what you can do next:</p>
        <ul>
          <li>Create or join an organization</li>
          <li>Invite your teammates</li>
          <li>Explore the dashboard</li>
        </ul>
        <p><a href="{settings.FRONTEND_URL}/dashboard"
           style="padding:10px 20px;background:#4F46E5;color:white;
           border-radius:6px;text-decoration:none;">Go to Dashboard</a></p>
        """,
    )
