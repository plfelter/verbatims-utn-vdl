from app import db
from datetime import datetime
import pytz


class Contribution(db.Model):
    """Contribution model for storing verbatim data."""
    __tablename__ = 'contributions'

    id = db.Column(db.Integer, primary_key=True)
    contributor = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text, nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Contribution {self.id} by {self.contributor}>'


class Comment(db.Model):
    """Comment model for storing user comments."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(tz=pytz.timezone('Europe/Paris')))
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    @property
    def vote_score(self):
        """Calculate the total vote score (upvotes - downvotes)."""
        return self.upvotes - self.downvotes

    def __repr__(self):
        return f'<Comment {self.id} by {self.username}>'

# You can add more models as needed for your application
