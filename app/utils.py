from flask_mail import Message
from flask import url_for
import secrets

from app import mail, app

def generate_confirmation_token():
    """Generate a secure token for email confirmation."""
    return secrets.token_urlsafe(32)

def send_confirmation_email(email, token, content_type, content_id):
    """
    Send a confirmation email to the user.
    
    Args:
        email (str): The recipient's email address
        token (str): The confirmation token
        content_type (str): Either 'comment' or 'answer'
        content_id (int): The ID of the comment or answer
    """
    # Generate the confirmation URL
    confirm_url = url_for(
        'confirm_content', 
        token=token, 
        content_type=content_type, 
        content_id=content_id,
        _external=True
    )
    
    # Create the email subject and body
    subject = f"Please confirm your {content_type}"
    body = f"""
    Thank you for your contribution!
    
    Please click the link below to confirm your {content_type}:
    {confirm_url}
    
    Your {content_type} will appear on the website after confirmation.
    
    If you did not make this request, please ignore this email.
    """
    
    # Create and send the email
    msg = Message(
        subject=subject,
        recipients=[email],
        body=body
    )
    
    mail.send(msg)