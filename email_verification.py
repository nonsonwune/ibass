# email_verification.py
import os
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from flask import url_for, current_app


def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="email-verification-salt")


def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token, salt="email-verification-salt", max_age=expiration
        )
    except Exception:
        return False
    return email


def send_verification_email(user_email, token):
    from app import mail  # Import here to avoid circular imports

    verify_url = url_for("verify_email", token=token, _external=True)
    html = f"""
    <h1>Verify Your Email</h1>
    <p>Click the link below to verify your email address:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>This link will expire in 1 hour.</p>
    """
    msg = Message("Verify Your Email", recipients=[user_email], html=html)
    mail.send(msg)
