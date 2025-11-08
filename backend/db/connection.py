"""
Database connection and initialization module.
Handles database connection setup, configuration, and lifecycle management.
"""
from peewee import SqliteDatabase

from backend.config import get_db_path


# Create database connection
# This must be defined before models.py imports it
# Use config module to get database path
db = SqliteDatabase(get_db_path())


def connect_db():
    """Connect to the database."""
    if not db.is_connection_usable():
        db.connect(reuse_if_open=True)


def close_db():
    """Close the database connection."""
    if not db.is_closed():
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Should be called once when the application starts.
    """
    # Import models here to avoid circular import
    # Models are imported after db is defined, so this is safe
    from backend.db.models import Album, Asset, AssetPart, Device
    
    connect_db()
    db.create_tables([Asset, AssetPart, Device, Album], safe=True)
    # safe=True prevents errors if tables already exist


def reset_db():
    """
    Reset the database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    # Import models here to avoid circular import
    from backend.db.models import Album, Asset, AssetPart, Device
    
    connect_db()
    db.drop_tables([Asset, AssetPart, Device, Album], safe=True)
    db.create_tables([Asset, AssetPart, Device, Album], safe=True)

