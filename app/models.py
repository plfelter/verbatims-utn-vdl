from datetime import datetime

import pytz
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import case

from app import db, anonymise_contributors


class SearchLog(db.Model):
    """Model for logging search queries."""
    __tablename__ = 'search_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(tz=pytz.timezone('Europe/Paris')))
    search_content = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)  # Store user agent information

    def __repr__(self):
        return f'<SearchLog {self.id} from {self.ip_address}>'


class Contribution(db.Model):
    """Contribution model for storing verbatim data."""
    __tablename__ = 'contributions'

    id = db.Column(db.Integer, primary_key=True)
    contributor = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text, nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    @hybrid_property
    def formatted_time(self):
        """Return time formatted in French style."""
        format_str = 'Le %d/%m/%Y à %Hh%M'
        # We need to ensure we have the actual datetime instance
        if hasattr(self, '_time') and self._time is not None:
            return self._time.strftime(format_str)
        if self.time is not None:
            # Access the actual datetime value, not the SQLAlchemy column
            time_value = self.time
            if hasattr(time_value, 'strftime'):  # Make sure it's a datetime object
                return time_value.strftime(format_str)
        return func.strftime(format_str, self.time).label('formatted_time')

    @hybrid_property
    def anonymized_contributor(self):
        """Return anonymized or genuine contributor name based on flag."""
        if not anonymise_contributors:
            return self.contributor

        # Get actual contributor value
        if hasattr(self, '_contributor') and self._contributor is not None:
            contributor_value = self._contributor
        else:
            contributor_value = self.contributor

        if contributor_value is not None:
            return self.anonymise_contributor(contributor_value)
        return None

    @anonymized_contributor.expression
    def anonymized_contributor(cls):
        """SQL expression for anonymized contributor."""
        if not anonymise_contributors:
            return cls.contributor

        # Correct syntax for SQLAlchemy's case function
        return case(
            (func.lower(cls.contributor) == 'anonyme', cls.contributor),
            else_='anonymisée'
        ).label('anonymized_contributor')

    @staticmethod
    def anonymise_contributor(contributor):
        """Anonymize the contributor name."""
        # contributor = contributor.lower()
        if contributor.lower() == 'anonyme':
            return contributor
        return 'Anonymisée'

    def __repr__(self):
        return f'<Contribution {self.id} by {self.contributor}>'


class Comment(db.Model):
    """Comment model for storing user comments."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)  # Email is now required for confirmation
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)  # Store user agent information
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(tz=pytz.timezone('Europe/Paris')))
    confirmed = db.Column(db.Boolean, default=False)  # Whether the comment has been confirmed
    confirmation_token = db.Column(db.String(100), nullable=False)  # Token for email confirmation

    # Relationship with answers
    answers = db.relationship('Answer', backref='comment', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Comment {self.id} by {self.username}>'


class Answer(db.Model):
    """Answer model for storing replies to comments."""
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)  # Email is now required for confirmation
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)  # Store user agent information
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(tz=pytz.timezone('Europe/Paris')))
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)  # Whether the answer has been confirmed
    confirmation_token = db.Column(db.String(100), nullable=False)  # Token for email confirmation

    def __repr__(self):
        return f'<Answer {self.id} to comment {self.comment_id} by {self.username}>'

class AnalyseChat(db.Model):
    """Model for storing chat messages from the analyse view."""
    __tablename__ = 'analyse_chats'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(tz=pytz.timezone('Europe/Paris')))
    user_message = db.Column(db.Text, nullable=False)
    server_response = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)  # Store user agent information

    def __repr__(self):
        return f'<AnalyseChat {self.id} from {self.ip_address}>'


class DownloadLog(db.Model):
    """Model for logging file downloads."""
    __tablename__ = 'download_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(tz=pytz.timezone('Europe/Paris')))
    file_name = db.Column(db.Text, nullable=False)  # 'csv' or 'json'
    ip_address = db.Column(db.String(45), nullable=False)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.Text, nullable=True)  # Store user agent information

    def __repr__(self):
        return f'<DownloadLog {self.id} - {self.file_type} from {self.ip_address}>'

# You can add more models as needed for your application
