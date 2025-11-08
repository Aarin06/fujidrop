"""
Configuration module for FujiDrop.
Reads configuration from environment variables.
All settings must be provided via environment variables.
"""
import os


def get_db_path() -> str:
    """
    Get the database file path from FUJIDROP_DB_PATH environment variable.
    
    Raises:
        ValueError: If FUJIDROP_DB_PATH is not set
    """
    path = os.environ.get("FUJIDROP_DB_PATH")
    if not path:
        raise ValueError("FUJIDROP_DB_PATH environment variable is required")
    return path


def get_images_path() -> str:
    """
    Get the images directory path from FUJIDROP_IMAGES_PATH environment variable.
    
    Raises:
        ValueError: If FUJIDROP_IMAGES_PATH is not set
    """
    path = os.environ.get("FUJIDROP_IMAGES_PATH")
    if not path:
        raise ValueError("FUJIDROP_IMAGES_PATH environment variable is required")
    return path


def get_google_credentials_path() -> str:
    """
    Get the path to Google OAuth client_secret.json from FUJIDROP_GOOGLE_CREDENTIALS_PATH.
    
    Raises:
        ValueError: If FUJIDROP_GOOGLE_CREDENTIALS_PATH is not set
    """
    path = os.environ.get("FUJIDROP_GOOGLE_CREDENTIALS_PATH")
    if not path:
        raise ValueError("FUJIDROP_GOOGLE_CREDENTIALS_PATH environment variable is required")
    return path


def get_google_token_path() -> str:
    """
    Get the path to Google OAuth token.json from FUJIDROP_GOOGLE_TOKEN_PATH.
    
    Raises:
        ValueError: If FUJIDROP_GOOGLE_TOKEN_PATH is not set
    """
    path = os.environ.get("FUJIDROP_GOOGLE_TOKEN_PATH")
    if not path:
        raise ValueError("FUJIDROP_GOOGLE_TOKEN_PATH environment variable is required")
    return path


def get_fuji_part_size() -> int:
    """
    Get the preferred part size for Fujifilm camera uploads from FUJIDROP_FUJI_PART_SIZE.
    
    Raises:
        ValueError: If FUJIDROP_FUJI_PART_SIZE is not set
    """
    part_size = os.environ.get("FUJIDROP_FUJI_PART_SIZE")
    if not part_size:
        raise ValueError("FUJIDROP_FUJI_PART_SIZE environment variable is required")
    return int(part_size)


def get_oauth_server_port() -> int:
    """
    Get the port for OAuth local server from FUJIDROP_OAUTH_PORT.
    
    Raises:
        ValueError: If FUJIDROP_OAUTH_PORT is not set
    """
    port = os.environ.get("FUJIDROP_OAUTH_PORT")
    if not port:
        raise ValueError("FUJIDROP_OAUTH_PORT environment variable is required")
    return int(port)

