# app/utils/email.py
from flask import current_app, url_for
from flask_mail import Message
from ..extensions import mail
from threading import Thread
import logging

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            logging.info(f"Email sent successfully to {msg.recipients}")
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")

def send_email(subject, recipient, body, html=None):
    try:
        msg = Message(
            subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[recipient]
        )
        msg.body = body
        if html:
            msg.html = html
        
        Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        ).start()
        
    except Exception as e:
        logging.error(f"Error creating email message: {str(e)}")
        raise

def send_verification_email(user_email, token):
    try:
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        html = f"""
        <h1>Verify Your Email</h1>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>This link will expire in 1 hour.</p>
        """
        send_email("Verify Your Email", user_email, "Please verify your email", html)
    except Exception as e:
        logging.error(f"Error in send_verification_email: {str(e)}")
        raise