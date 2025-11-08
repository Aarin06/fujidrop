"""
Main server file for FujiDrop.
Initializes the Sanic application for camera uploads.
Focuses on core functionality: receiving photos from the camera and uploading to Google Photos.
"""
import os
from pathlib import Path

# Load environment variables FIRST, before any imports that use config
from dotenv import load_dotenv

# Load environment variables if .env file exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)
elif not os.environ.get("FUJIDROP_DB_PATH"):
    # Only warn if critical env vars are missing and .env doesn't exist
    import sys
    print(f"Warning: .env file not found at {env_path}. Make sure all environment variables are set.", file=sys.stderr)

# Now import everything else (which may use config)
import logging
import peewee
from sanic import Sanic
from sanic.log import logger

from backend.api.camera.routes import setup_camera_routes
from backend.db import Album, init_db


# Create Sanic application instance
app = Sanic("FujiDrop", env_prefix="FUJIDROP_")


# Configure logging to suppress expected WebSocket closure errors
# These occur when camera closes connection abnormally (1006 ABNORMAL)
# and Sanic tries to clean up an already-closed connection
class WebSocketErrorFilter(logging.Filter):
    """Filter to suppress expected WebSocket closure RuntimeErrors."""
    def filter(self, record):
        # Check both exception info and message text
        try:
            message = record.getMessage() if hasattr(record, 'getMessage') else str(record.msg)
        except Exception:
            message = str(getattr(record, 'msg', ''))
        
        # Suppress RuntimeError about TCPTransport being closed
        # This is expected when camera disconnects abnormally
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            if exc_type == RuntimeError:
                error_msg = str(exc_value)
                if "TCPTransport closed" in error_msg and "unable to perform operation" in error_msg:
                    # This is expected - camera closed connection, Sanic trying to clean up
                    return False  # Don't log this record
        
        # Also check message text for WebSocket closure errors
        if "Error closing websocket connection" in message:
            if "TCPTransport closed" in message or "unable to perform operation" in message:
                # Expected error when camera disconnects
                return False  # Don't log this record
        
        return True  # Log all other records


@app.before_server_start
async def setup_logging_filter(app, loop):
    """
    Configure logging filter to suppress expected WebSocket closure errors.
    This runs after Sanic initializes its logging system.
    """
    # Create and apply filter to Sanic's loggers
    ws_filter = WebSocketErrorFilter()
    
    # Filter Sanic's error logger
    error_logger = logging.getLogger("sanic.error")
    error_logger.addFilter(ws_filter)
    
    # Filter Sanic's access logger (just in case)
    access_logger = logging.getLogger("sanic.access")
    access_logger.addFilter(ws_filter)
    
    # Filter root logger handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(ws_filter)


@app.before_server_start
async def setup_database(app, loop):
    """
    Initialize database before server starts.
    Creates all tables if they don't exist.
    """
    logger.info("Initializing database...")
    init_db()
    
    # Check if album exists (legacy check from old code)
    try:
        Album.get()
        logger.info("Database initialized - album exists")
    except peewee.DoesNotExist:
        logger.info("Database initialized - no album yet")
        # await create_album()  # Can be implemented later if needed
    except Exception as e:
        logger.error(f"Error checking album: {e}")


# Register camera routes only (for camera uploads)
setup_camera_routes(app)


if __name__ == "__main__":
    # Run the server directly (for development)
    # In production, use: uv run sanic backend.server:app
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True,
        access_log=True,
        auto_reload=True,
    )
