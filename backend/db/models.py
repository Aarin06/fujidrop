"""
Database models for FujiDrop.
Defines the data models: Asset, AssetPart, Device, Album.
"""
import datetime
import os
from enum import IntEnum

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
)

# Import database connection from connection module
# This works because db is defined in connection.py before models try to use it
from backend.config import get_images_path
from backend.db.connection import db


class AssetStatus(IntEnum):
    NEW = 0
    AVAILABLE = 1
    UPLOADED = 2
    FAILED = 3


class Asset(Model):
    id: int = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    filename: str = CharField(unique=True)
    filetype: str = CharField()
    filesize: int = IntegerField()
    asset_id: str = CharField()
    status: AssetStatus = IntegerField()
    parts: int = IntegerField()
    google_product_url: str = CharField(default="")

    @property
    def thumbnail(self) -> str:
        return self.filename.replace(".MOV", ".JPG")

    @property
    def is_video(self) -> bool:
        return self.filename.endswith(".MOV")

    @property
    def path(self) -> str:
        """Get the full file path for this asset."""
        return os.path.join(get_images_path(), self.filename)

    class Meta:
        database = db


class AssetPart(Model):
    id: int = AutoField()
    created = DateTimeField(default=datetime.datetime.now)
    part_no: int = IntegerField()
    asset = ForeignKeyField(Asset, backref="asset_parts")
    status: AssetStatus = IntegerField()

    class Meta:
        database = db

    @property
    def path(self) -> str:
        return f"{self.asset.path}.{self.part_no}"


class Device(Model):
    id: int = AutoField()
    client_id: str = CharField()
    client_secret: str = CharField()
    user_code: str = CharField()
    device_code: str = CharField()
    added: bool = BooleanField(default=False)

    class Meta:
        database = db


class Album(Model):
    id: str = CharField()
    title: str = CharField()
    productUrl: str = CharField()

    class Meta:
        database = db


# Database initialization moved to backend.db.connection.init_db()
