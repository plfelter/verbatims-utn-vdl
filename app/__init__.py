from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
import locale

persistent_path: Path = Path(__file__).resolve().parent
db_path = persistent_path / "sqlite.db"

# App settings
anonymise_contributors = True
# locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{db_path}'
app.config["SQLALCHEMY_ECHO"] = False
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()

from app import views
from app import models

db.init_app(app)

with app.app_context():
    db.create_all()

# Initialize database with data if needed
from app.database import DatabaseInitializer
db_initializer = DatabaseInitializer(app)
db_initializer.initialize_database()
