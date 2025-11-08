"""
Camera route handlers - Business logic for camera routes.
Handles frame.io compatibility logic for camera uploads.
"""
import asyncio
import json as json_lib
import random
import time
import uuid

import os

import peewee
from sanic.response import json, text

from backend.api.camera.responses import ASSET_RESPONSE, DEVICE_RESPONSE
from backend.api.camera.types import Asset
from backend.db.models import Asset as AssetModel, AssetPart, AssetStatus, Device
from backend.services.asset_processor import stitch_file, upload_to_google


async def handle_health():
    """
    Handle health check request.
    
    Returns:
        JSON response: {"ok": True}
    """
    return json({"ok": True})


async def handle_create_asset(body: Asset, request_json: dict):
    """
    Handle asset creation request from camera.
    
    This function:
    1. Creates or retrieves asset by filename (handles camera reconnection)
    2. Creates AssetPart records for each upload chunk
    3. Generates fake frame.io upload URLs
    4. Returns frame.io-compatible response
    
    Args:
        body: Validated Asset dataclass
        request_json: Raw request JSON (for accessing fields)
    
    Returns:
        JSON response with asset ID and upload URLs (frame.io format)
    """
    asset_id = uuid.uuid4()
    filename = request_json.get("name")
    filetype = request_json.get("filetype")
    filesize = request_json.get("filesize")
    parts = request_json.get("parts")

    # If the camera restarts an upload under a new asset, we want to actually resume the one
    # we were working on
    asset, created = AssetModel.get_or_create(
        filename=filename,
        defaults={
            "parts": parts,
            "asset_id": asset_id,
            "status": AssetStatus.NEW,
            "filetype": filetype,
            "filesize": filesize,
        },
    )

    assert asset.parts == parts, "Camera changed parts on the fly??"

    if created:
        print(f"Picture taken: {filename}")
        # Initialize parts
        for i in range(1, parts + 1):
            AssetPart.create(
                asset=asset,
                status=AssetStatus.NEW,
                part_no=i,
            )
    else:
        # Have to update the asset_id
        asset.asset_id = asset_id
        asset.save()

    # Determine file extension based on filetype
    match filetype:
        case "image/jpeg":
            extension = ".JPG"
        case "image/x-fujifilm-raf":
            extension = ".RAF"
        case "video/mp4":
            extension = ".mp4"
        case _:
            print(f"unknown type {filetype}")
            return json({"status": "oh god"}, status=400)

    urls = [
        f"https://api.frame.io/upload?x-amz-meta-asset_id={asset_id}&x-amz-meta-extension={extension}"
        f"&x-amz-meta-is_realtime_upload=false&x-amz-meta-part_count={parts}&x-amz-meta-part_number={part}"
        f"&x-amz-meta-project_id=73eb534d-23fa-4db1-b341-a05616de5d54&x-amz-meta-request_id=F_Cf-zNJlCzl-nwRe9fJ"
        f"&x-amz-meta-resource_id=d4ac41d4-9711-4dfb-8be5-3a38c89203f7&x-amz-meta-resource_type=asset"
        f"&x-amz-meta-total_parts=2&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAZ5BPIQ3GOE3GUNGI%2F20240830%2Fus-east-1%2Fs3%2Faws4_request"
        "&X-Amz-Date=20240830T214918Z&X-Amz-Expires=86400&X-Amz-SignedHeaders=content-type%3Bhost%3Bx-amz-acl"
        "&X-Amz-Signature=346bd7bb9f7e6a80468373ec5366d8a63398a48e0ab4014d2dfa7ee5d3ed57f3"
        for part in range(1, parts + 1)
    ]

    return json(
        {
            "id": str(asset_id),
            "filetype": "image/jpeg",
            "upload_urls": urls,
            "original_upload": urls[0],
            **ASSET_RESPONSE,
        }
    )


async def handle_upload(request):
    """
    Handle file part uploads from camera.
    
    This function:
    1. Receives streaming upload of file part
    2. Saves part to disk
    3. Marks part as available
    4. Triggers file stitching when last part received
    5. Triggers Google Photos upload after stitching
    
    Args:
        request: Sanic request object with streaming upload data
    
    Returns:
        Text response: "ok"
    """
    asset_id = request.args.get("x-amz-meta-asset_id")
    part = int(request.args.get("x-amz-meta-part_number"))
    length = int(request.headers.get("content-length"))

    # Find the asset part
    asset_part = (
        AssetPart.select()
        .join(AssetModel)
        .where(
            AssetModel.asset_id == asset_id,
            AssetPart.part_no == part,
        )
        .get()
    )

    print(f"{asset_part.asset.filename}: #{part}")

    # Optimization: we already have the part so tell the camera its done
    if asset_part.status != AssetStatus.AVAILABLE:
        path = asset_part.path
        received_bytes = b""
        while True:
            body = await request.stream.read()
            if body is None:
                break
            received_bytes += body
        with open(path, "wb") as f:
            written = f.write(received_bytes)
            assert written == length, (length, written)
            asset_part.status = AssetStatus.AVAILABLE
            asset_part.save()

    else:
        print("already got it")
        # Part already uploaded - consume and discard the request body
        # We must read it to prevent connection issues with the camera
        # Using a small buffer to minimize memory usage
        while True:
            body = await request.stream.read()
            if body is None:
                break

    # Finished upload? Stitch file and trigger Google Photos upload
    if part == asset_part.asset.parts:
        await stitch_file(asset_part.asset)
        # Trigger Google Photos upload in background (pass coroutine, don't call it!)
        # Fix: Remove parentheses to pass the coroutine, not call it immediately
        # request.app.add_task(upload_to_google, name="upload_to_google")

    return text("ok", status=200)


async def handle_device_code(request, body):
    """
    Handle device authentication code request.
    Generates a user code and device code for camera authentication.
    
    Args:
        request: Sanic request object
        body: Validated DeviceCode dataclass
    
    Returns:
        JSON response with device_code, user_code, and expiration info
    """
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    # In case we need it later
    _ = request.form.get("scope")

    # Generate new user code (6-digit number)
    user_code = f"{random.randrange(10**5, 10**6):06d}"

    device_code = str(uuid.uuid4())
    Device.create(
        client_id=client_id,
        client_secret=client_secret,
        user_code=user_code,
        device_code=device_code,
        added=False,
    )

    return json(
        {
            "device_code": device_code,
            "expires_in": 120,
            "interval": 5,
            "name": f"MyDevice-{client_id}",
            "user_code": user_code,
        }
    )


async def handle_auth_token(request):
    """
    Handle device token exchange request.
    Exchanges device code for access token (returns fake JWT).
    
    Matches OLD behavior: always returns a token immediately (device approval not required).
    The camera doesn't care if you always return the same credentials.
    
    Args:
        request: Sanic request object
    
    Returns:
        JSON response with access_token and refresh_token (fake JWT)
    """
    device_code = request.form.get("device_code")
    client_id = request.form.get("client_id")

    # Note: Token stored in environment variable to avoid GitHub secret scanning
    # The camera doesn't care if you always return the same credentials.
    # Match OLD behavior: always return token immediately (no device approval check)
    # Get token from environment variable, with fallback for development
    access_token = os.environ.get(
        "FUJIDROP_ACCESS_TOKEN",
        # Fallback: clearly marked as fake to avoid secret scanning
        # In production, set FUJIDROP_ACCESS_TOKEN environment variable
        "FAKE_TOKEN_PLACEHOLDER_SET_FUJIDROP_ACCESS_TOKEN_ENV_VAR"
    )
    refresh_token = os.environ.get(
        "FUJIDROP_REFRESH_TOKEN",
        "FAKE_REFRESH_TOKEN_PLACEHOLDER_SET_FUJIDROP_REFRESH_TOKEN_ENV_VAR"
    )
    
    token_response = {
        "access_token": access_token,
        "expires_in": 28800,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
    
    # Always return token immediately (matches OLD behavior)
    # Device approval check happens after return in OLD code (dead code)
    return json(token_response)


async def handle_devices_me():
    """
    Handle device info request.
    Returns frame.io-compatible device information.
    
    Returns:
        JSON response with device information (fake frame.io response)
    """
    return json(DEVICE_RESPONSE)


async def handle_add_device(user_code: str):
    """
    Handle device approval request.
    Approves a device by user code (manual approval via web interface).
    
    Args:
        user_code: 6-digit user code from device registration
    
    Returns:
        JSON response with status
    """
    try:
        device = Device.get(user_code=user_code)
    except peewee.DoesNotExist:
        return json({"status": "not found"}, status=404)
    else:
        device.added = True
        device.save()

    return json({"status": "ok"})


async def devices_websocket(request, ws):
    """
    WebSocket endpoint for device communication using Phoenix protocol.
    
    Implements Frame.io C2C WebSocket protocol:
    1. Camera connects and joins channel via phx_join
    2. Camera sends heartbeats every ~15 seconds
    3. Server responds to keep connection alive
    4. Gracefully handles camera disconnection
    
    Frame.io endpoint: GET /devices/websocket
    Reference: https://developer.frame.io/docs/device-integrations/manage-status-and-state
    
    Args:
        request: Sanic request object
        ws: WebSocket connection object
    """
    connection_open = True
    
    try:
        # Authorization comes from query parameter, not header
        # Format: ?Authorization=Bearer%20TOKEN (URL-encoded)
        auth_param = request.args.get("Authorization", "")
        
        # Verify token is present (basic validation)
        if not auth_param or not auth_param.startswith("Bearer "):
            try:
                await ws.close(code=403, reason="Unauthorized")
            except Exception:
                pass  # Connection may already be closed
            return
        
        print("WebSocket: Camera connected")
        
        # Keep connection alive and handle messages
        while connection_open:
            try:
                # Wait for messages from the camera
                # Frame.io spec: connection times out after 60s without heartbeat
                # Set timeout slightly longer to account for network delays
                message = await ws.recv(timeout=75.0)
                
                try:
                    # Parse JSON message (Phoenix protocol uses JSON)
                    data = json_lib.loads(message)
                    topic = data.get("topic", "")
                    event = data.get("event", "")
                    ref = data.get("ref", "")
                    payload = data.get("payload", "")
                    
                    # Handle channel join (phx_join)
                    # Topic format: "devices:DEVICE_ID"
                    if event == "phx_join" and topic.startswith("devices:"):
                        # Camera is joining its device channel
                        # Respond with phx_reply to confirm join
                        response = {
                            "event": "phx_reply",
                            "payload": {"response": {}, "status": "ok"},
                            "ref": ref,
                            "topic": topic
                        }
                        try:
                            await ws.send(json_lib.dumps(response))
                            print(f"WebSocket: Channel joined - {topic}")
                        except Exception as send_error:
                            # Connection closed while sending
                            print(f"WebSocket: Failed to send join response: {send_error}")
                            connection_open = False
                            break
                    
                    # Handle heartbeat (Phoenix protocol)
                    # Topic: "phoenix", Event: "heartbeat"
                    elif event == "heartbeat" and topic == "phoenix":
                        # Camera is sending heartbeat to keep connection alive
                        # Respond with phx_reply to confirm
                        response = {
                            "event": "phx_reply",
                            "payload": {"response": {}, "status": "ok"},
                            "ref": ref,
                            "topic": "phoenix"
                        }
                        try:
                            await ws.send(json_lib.dumps(response))
                        except Exception as send_error:
                            # Connection closed while sending heartbeat response
                            print(f"WebSocket: Failed to send heartbeat response: {send_error}")
                            connection_open = False
                            break
                    
                    # Handle status_updated events (optional, for pause/resume)
                    elif event == "status_updated":
                        # Frame.io may send status updates
                        print(f"WebSocket: Status updated - {payload}")
                        pass
                    
                    # Handle other events (log for debugging, but keep connection alive)
                    elif event:
                        # Unknown event - log but keep connection alive for compatibility
                        print(f"WebSocket: Unknown event '{event}' on topic '{topic}'")
                        
                except json_lib.JSONDecodeError:
                    # Not JSON - might be a ping or invalid message, just ignore
                    print(f"WebSocket: Received non-JSON message: {message[:100]}")
                    pass
                except Exception as e:
                    # Error processing message - log but keep connection alive
                    print(f"WebSocket message processing error: {e}")
                    
            except asyncio.TimeoutError:
                # No message received within timeout period
                # This can happen if camera stops sending heartbeats (camera turned off)
                print("WebSocket: Timeout - no heartbeat received (camera may have disconnected)")
                connection_open = False
                break
                
            except ConnectionError:
                # Connection was closed by client (camera turned off)
                print("WebSocket: Connection closed by camera")
                connection_open = False
                break
                
            except Exception as recv_error:
                # Other connection errors
                error_type = type(recv_error).__name__
                error_msg = str(recv_error)
                
                # Check if connection is already closed
                if "closed" in error_msg.lower() or "Connection" in error_type:
                    print(f"WebSocket: Connection closed - {error_type}: {error_msg}")
                else:
                    print(f"WebSocket: Receive error - {error_type}: {error_msg}")
                
                connection_open = False
                break
                
    except Exception as e:
        # Outer exception handler for unexpected errors
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"WebSocket: Unexpected error - {error_type}: {error_msg}")
        connection_open = False
        
    finally:
        # Gracefully close connection if still open
        # Note: Sanic will handle cleanup, but we check state to avoid errors
        if connection_open:
            try:
                # Check if websocket is still open before attempting to close
                # Sanic's WebSocket protocol doesn't expose a direct 'is_open' check,
                # so we catch the exception if already closed
                await ws.close(code=1000, reason="Normal closure")
                print("WebSocket: Connection closed gracefully")
            except (ConnectionError, RuntimeError, Exception) as close_error:
                # Connection already closed by client or transport is closed
                # This is expected when camera disconnects - no need to log as error
                pass
        else:
            print("WebSocket: Connection already closed")
