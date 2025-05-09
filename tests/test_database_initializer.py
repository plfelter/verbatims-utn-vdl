import os
import sys
import unittest
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tony import app, db
from tony.models import Contribution
from tony.database import DatabaseInitializer


class TestDatabaseInitializer(unittest.TestCase):
    """Test the DatabaseInitializer class."""

    def setUp(self):
        """Set up test environment."""
        # Use an in-memory SQLite database for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        
        # Create the database and tables
        with app.app_context():
            db.create_all()
        
        self.db_initializer = DatabaseInitializer(app)
    
    def tearDown(self):
        """Clean up after tests."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_is_contributions_table_empty(self):
        """Test the is_contributions_table_empty method."""
        # Initially, the table should be empty
        self.assertTrue(self.db_initializer.is_contributions_table_empty())
        
        # Add a contribution and check again
        with app.app_context():
            contribution = Contribution(contributor="Test User", body="Test Body")
            db.session.add(contribution)
            db.session.commit()
        
        # Now the table should not be empty
        self.assertFalse(self.db_initializer.is_contributions_table_empty())
    
    def test_load_contributions_data(self):
        """Test the load_contributions_data method."""
        # Ensure the contributions.json file exists
        contributions_json_path = Path(__file__).resolve().parent.parent / "verbatims" / "contributions.json"
        self.assertTrue(os.path.exists(contributions_json_path), "contributions.json file not found")
        
        # Load the data
        data = self.db_initializer.load_contributions_data()
        
        # Verify the data is loaded correctly
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0, "No data loaded from contributions.json")
        
        # Check the structure of the first item
        first_item = data[0]
        self.assertIn('body', first_item)
        self.assertIn('user', first_item)
        self.assertIn('time', first_item)
    
    def test_populate_contributions_table(self):
        """Test the populate_contributions_table method."""
        # Initially, the table should be empty
        self.assertTrue(self.db_initializer.is_contributions_table_empty())
        
        # Populate the table
        self.db_initializer.populate_contributions_table()
        
        # Now the table should not be empty
        self.assertFalse(self.db_initializer.is_contributions_table_empty())
        
        # Check that the data was imported correctly
        with app.app_context():
            contributions_count = Contribution.query.count()
            self.assertTrue(contributions_count > 0, "No contributions were imported")
            
            # Check a few random contributions
            contributions = Contribution.query.limit(5).all()
            for contribution in contributions:
                self.assertIsNotNone(contribution.contributor)
                self.assertIsNotNone(contribution.body)
                self.assertIsNotNone(contribution.time)


if __name__ == '__main__':
    unittest.main()