"""
Camera upload routes - Frame.io compatibility endpoints.
These routes handle direct communication with the Fujifilm X100VI camera.
"""
from sanic import Blueprint
from sanic.response import json
from sanic_ext import validate

from backend.api.camera.handlers import (
    devices_websocket,
    handle_add_device,
    handle_auth_token,
    handle_create_asset,
    handle_device_code,
    handle_devices_me,
    handle_health,
    handle_upload,
)
from backend.api.camera.types import Asset, DeviceCode

# Create blueprint for camera routes (with /v2/ prefix)
camera_bp = Blueprint("camera", url_prefix="/v2")


@camera_bp.post("/assets")
@validate(json=Asset)
async def create_asset(request, body):
    """
    Create a new asset - camera initiates upload.
    Frame.io endpoint: POST /v2/assets
    
    Args:
        request: Sanic request object
        body: Validated Asset dataclass from request JSON
    """
    return await handle_create_asset(body, request.json)


@camera_bp.post("/auth/device/code")
@validate(form=DeviceCode)
async def device_code(request, body):
    """
    Generate device authentication code.
    Frame.io endpoint: POST /v2/auth/device/code
    
    Args:
        request: Sanic request object
        body: Validated DeviceCode dataclass
    """
    return await handle_device_code(request, body)


@camera_bp.post("/auth/token")
async def auth_token(request):
    """
    Exchange device code for access token.
    Frame.io endpoint: POST /v2/auth/token
    
    Args:
        request: Sanic request object
    """
    return await handle_auth_token(request)


@camera_bp.get("/devices/me")
async def devices_me(request):
    """
    Get current device information.
    Frame.io endpoint: GET /v2/devices/me
    
    Args:
        request: Sanic request object
    """
    return await handle_devices_me()


@camera_bp.get("/health")
async def health_v2(request):
    """
    Health check endpoint under /v2/ prefix.
    Frame.io endpoint: GET /v2/health
    
    Args:
        request: Sanic request object
    """
    return await handle_health()


# Upload route - defined here but registered without blueprint prefix
# This route is registered directly on the app at /upload (not /v2/upload)
async def upload(request):
    """
    Handle file part uploads.
    Frame.io endpoint: PUT /upload (no prefix - root level)
    """
    return await handle_upload(request)


# Device approval route - defined here but registered without blueprint prefix
# This route is registered directly on the app at /add-device (not /v2/add-device)
async def add_device(request, user_code: str):
    """
    Approve device by user code.
    Legacy endpoint: GET /add-device/<user_code>
    
    Args:
        request: Sanic request object
        user_code: 6-digit user code from device registration
    """
    return await handle_add_device(user_code)

async def health(request):
    """
    Health check endpoint (frame.io compatible).
    GET /health (root level)
    """
    return await handle_health()


def setup_camera_routes(app):
    """
    Register all camera routes with the Sanic app.
    This includes both blueprint routes (/v2/*) and standalone routes.
    
    Args:
        app: Sanic application instance
    """
    # Register camera blueprint (routes under /v2/)
    # Includes: /v2/health, /v2/assets, /v2/auth/device/code, /v2/auth/token, /v2/devices/me
    app.blueprint(camera_bp)
    
    # Register standalone routes directly on app (no blueprint prefix)
    # These must be at root level to match frame.io's API structure
    
    # Upload route: PUT /upload
    app.add_route(upload, "/upload", methods=["PUT"], stream=True)
    
    # Device approval route: GET /add-device/<user_code>
    # Legacy endpoint for manually approving devices via web interface
    app.add_route(add_device, "/add-device/<user_code>", methods=["GET"])

    # Health check at root level: GET /health
    app.add_route(health, "/health", methods=["GET"])
    
    # WebSocket endpoint: GET /devices/websocket
    # Implements Frame.io C2C Phoenix WebSocket protocol
    # Handles channel joins (phx_join) and heartbeats to keep connection alive
    # Authorization comes from query parameter: ?Authorization=Bearer%20TOKEN
    app.add_websocket_route(devices_websocket, "/devices/websocket")

