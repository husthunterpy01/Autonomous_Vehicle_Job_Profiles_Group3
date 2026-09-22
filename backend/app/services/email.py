import smtplib
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import quote

from app.core.config import settings
from app.models.user import User


class EmailDeliveryError(Exception):
    pass


class PasswordResetEmailSender(Protocol):
    def send_reset_link(self, user: User, token: str) -> None: ...

    def send_password_changed(self, user: User) -> None: ...


class SmtpPasswordResetEmailSender:
    def _send(self, message: EmailMessage) -> None:
        if not settings.smtp_host:
            raise EmailDeliveryError("SMTP_HOST is not configured")

        try:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=10,
            ) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise EmailDeliveryError("Unable to deliver authentication email") from error

    def send_reset_link(self, user: User, token: str) -> None:
        separator = "&" if "?" in settings.password_reset_frontend_url else "?"
        reset_url = (
            f"{settings.password_reset_frontend_url}{separator}token={quote(token)}"
        )
        message = EmailMessage()
        message["Subject"] = "Reset your AV Job Profiles password"
        message["From"] = settings.smtp_from_email
        message["To"] = user.email
        message.set_content(
            f"Hello {user.full_name},\n\n"
            f"Use this link to reset your password within "
            f"{settings.password_reset_token_minutes} minutes:\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
        self._send(message)

    def send_password_changed(self, user: User) -> None:
        message = EmailMessage()
        message["Subject"] = "Your AV Job Profiles password was changed"
        message["From"] = settings.smtp_from_email
        message["To"] = user.email
        message.set_content(
            f"Hello {user.full_name},\n\n"
            "Your password was reset successfully. If you did not make this "
            "change, contact the project team immediately."
        )
        self._send(message)


def get_password_reset_email_sender() -> PasswordResetEmailSender:
    return SmtpPasswordResetEmailSender()
