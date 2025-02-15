
from app import db, app


def create_tables():
    # Create database tables manually
    with app.app_context():
        db.create_all()

def drop_tables():
    # Drop all the tables
    with app.app_context():
        db.drop_all()
