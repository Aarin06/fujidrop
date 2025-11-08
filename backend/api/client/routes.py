"""
Client API routes - Endpoints for web client/frontend.
These routes provide status, asset management, and other client-facing functionality.
"""
from sanic import Blueprint

from backend.api.client.handlers import handle_status

# Create blueprint for client routes (with /api/ prefix)
client_bp = Blueprint("client", url_prefix="/api")


@client_bp.get("/status")
async def status(request):
    """
    Get API status - assets, devices, and album information.
    GET /api/status
    
    Args:
        request: Sanic request object
    
    Returns:
        JSON response with assets, devices, and album status
    """
    return await handle_status()


def setup_client_routes(app):
    """
    Register all client routes with the Sanic app.
    
    Args:
        app: Sanic application instance
    """
    # Register client blueprint (routes under /api/)
    app.blueprint(client_bp)
