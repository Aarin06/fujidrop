"""
Main route registration for the API.
Registers all blueprints (camera, client) and standalone routes.
"""
from sanic import Sanic

from backend.api.camera.routes import setup_camera_routes
from backend.api.client.routes import setup_client_routes


def setup_routes(app: Sanic):
    """
    Register all routes and blueprints with the Sanic app.
    
    Args:
        app: Sanic application instance
    """
    # Register camera routes (blueprint + standalone routes)
    setup_camera_routes(app)
    
    # Register client routes (blueprint routes)
    setup_client_routes(app)

