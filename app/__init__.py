from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from pathlib import Path
import secrets

persistent_path: Path = Path(__file__).resolve().parent
db_path = persistent_path / "database" / "sqlite.db"

# App settings
anonymise_contributors = True
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_path}'
app.config["SQLALCHEMY_ECHO"] = False
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Mail configuration
app.config["MAIL_SERVER"] = "smtp.example.com"  # Replace with your SMTP server
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "your-email@example.com"  # Replace with your email
app.config["MAIL_PASSWORD"] = "your-password"  # Replace with your password
app.config["MAIL_DEFAULT_SENDER"] = "your-email@example.com"  # Replace with your email
app.config["SECRET_KEY"] = secrets.token_hex(16)  # Generate a random secret key

db = SQLAlchemy()
mail = Mail()

from app import views
from app import models

db.init_app(app)
mail.init_app(app)

with app.app_context():
    db.create_all()

# Initialize database with data if needed
from app.database import DatabaseInitializer
db_initializer = DatabaseInitializer(app)
db_initializer.initialize_database()
