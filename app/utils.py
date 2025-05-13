import os
import base64
import io
from captcha.image import ImageCaptcha
from flask import session

from app import app

def generate_captcha():
    """
    Generate a captcha image and text.

    Returns:
        tuple: (captcha_text, captcha_image_base64)
    """
    # Create a captcha image generator
    image = ImageCaptcha(width=280, height=90)

    # Generate a random captcha text
    import random
    import string
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Generate the captcha image
    captcha_image = image.generate(captcha_text)

    # Convert the image to base64 for embedding in HTML
    captcha_image.seek(0)
    captcha_image_base64 = base64.b64encode(captcha_image.read()).decode('utf-8')

    return captcha_text, captcha_image_base64

def validate_captcha(user_input, captcha_text):
    """
    Validate the user's captcha input against the generated captcha text.

    Args:
        user_input (str): The user's input
        captcha_text (str): The generated captcha text

    Returns:
        bool: True if the input matches the captcha text, False otherwise
    """
    return user_input and user_input.upper() == captcha_text
