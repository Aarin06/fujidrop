"""
Client route handlers - Business logic for client-facing API routes.
Handles status, asset management, and other client endpoints.
"""
import peewee
from playhouse.shortcuts import model_to_dict
from sanic.response import json

from backend.db.models import Album, Asset, Device


async def handle_status():
    """
    Handle status endpoint request.
    Returns current status of assets, devices, and album.
    
    Returns:
        JSON response with assets count/results, devices count/results, and album
    """
    assets = Asset.select()
    devices = Device.select()

    try:
        album = model_to_dict(Album.get())
    except peewee.DoesNotExist:
        album = None
    
    return json(
        {
            "assets": {
                "count": len(assets),
                "results": [model_to_dict(asset) for asset in assets],
            },
            "devices": {
                "count": len(devices),
                "results": [model_to_dict(device) for device in devices],
            },
            "album": album,
        },
        default=str,
    )
