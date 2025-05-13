import json
import os
from datetime import datetime
from pathlib import Path
from app import db
from app.models import Contribution


class DatabaseInitializer:
    """Class to handle database initialization and population."""
    
    def __init__(self, app):
        """Initialize with Flask app instance."""
        self.app = app
        self.contributions_json_path = Path(__file__).resolve().parent.parent / "resources" /"verbatims" / "contributions.json"
    
    def is_contributions_table_empty(self):
        """Check if the contributions table is empty."""
        with self.app.app_context():
            return Contribution.query.count() == 0
    
    def load_contributions_data(self):
        """Load data from contributions.json file."""
        if not os.path.exists(self.contributions_json_path):
            print(f"Warning: Contributions data file not found at {self.contributions_json_path}")
            return []
        
        try:
            with open(self.contributions_json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except Exception as e:
            print(f"Error loading contributions data: {e}")
            return []
    
    def populate_contributions_table(self):
        """Populate the contributions table with data from contributions.json."""
        if not self.is_contributions_table_empty():
            print("Contributions table already populated, skipping initialization.")
            return
        
        contributions_data = self.load_contributions_data()
        if not contributions_data:
            print("No contributions data to import.")
            return
        
        print(f"Importing {len(contributions_data)} contributions...")
        
        with self.app.app_context():
            for item in contributions_data:
                # Parse the time string to a datetime object
                time_str = item.get('time')
                time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                
                # Create and add the contribution to the database
                if not item.get('user'):
                    raise ValueError("User is required for each contribution.")
                contribution = Contribution(
                    id=int(item.get('number')),
                    contributor=item.get('user'),
                    body=item.get('body'),
                    time=time
                )
                db.session.add(contribution)
            
            # Commit all changes to the database
            db.session.commit()
            print("Contributions table populated successfully.")
    
    def initialize_database(self):
        """Initialize the database by populating empty tables."""
        print("Checking database tables...")
        self.populate_contributions_table()
        print("Database initialization complete.")