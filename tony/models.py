from tony import db
from datetime import datetime

class User(db.Model):
    """User model for storing user-related data."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

class Comment(db.Model):
    """Comment model for storing user comments."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)

    @property
    def vote_score(self):
        """Calculate the total vote score (upvotes - downvotes)."""
        return self.upvotes - self.downvotes

    def __repr__(self):
        return f'<Comment {self.id} by {self.username}>'

# You can add more models as needed for your application
