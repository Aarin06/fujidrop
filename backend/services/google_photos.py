"""
Google Photos integration service.
Handles OAuth authentication and uploading photos to Google Photos.
"""
import mimetypes
import os

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from backend.config import (
    get_google_credentials_path,
    get_google_token_path,
    get_images_path,
    get_oauth_server_port,
)
from backend.db.models import Album

# Google Photos API scopes
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.appendonly"]


def get_credentials() -> Credentials:
    """
    Get or refresh Google OAuth credentials.
    Handles token refresh and initial OAuth flow if needed.
    """
    creds = None
    token_file = get_google_token_path()

    # Try to load existing token
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # Refresh or create new credentials if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Start OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                get_google_credentials_path(), SCOPES
            )
            creds = flow.run_local_server(
                open_browser=False,
                bind_addr="0.0.0.0",
                port=get_oauth_server_port(),
            )

    # Save token for future use
    with open(token_file, "w") as f:
        f.write(creds.to_json())

    return creds


async def upload_photo(filename: str) -> str:
    """
    Upload a photo to Google Photos.
    
    Args:
        filename: Name of the file to upload (e.g., "DSCF1234.JPG")
    
    Returns:
        Google Photos product URL for the uploaded photo
    
    Raises:
        AssertionError: If upload fails
    """
    mimetype, _ = mimetypes.guess_type(filename)
    creds = get_credentials()

    print(f"Uploading '{filename}' to Google Photos")
    images_path = get_images_path()
    file_path = os.path.join(images_path, filename)

    async with aiohttp.ClientSession() as session:
        # Step 1: Upload file to Google Photos API
        with open(file_path, "rb") as f:
            headers = {
                "Content-type": "application/octet-stream",
                "X-Goog-Upload-Protocol": "raw",
                "X-Goog-Upload-Content-Type": mimetype,
                "X-Goog-File-Name": filename,
                "Authorization": f"Bearer {creds.token}",
            }
            async with session.post(
                "https://photoslibrary.googleapis.com/v1/uploads",
                data=f,
                headers=headers,
            ) as resp:
                assert resp.status == 200, f"Upload failed with status {resp.status}"
                upload_token = await resp.text()

        # Step 2: Create media item in Google Photos
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {creds.token}",
        }

        # Check if album exists in database
        try:
            album = Album.get()
            data = {
                "albumId": album.id,
            }
        except Album.DoesNotExist:
            data = {}

        data["newMediaItems"] = [
            {
                "simpleMediaItem": {
                    "uploadToken": upload_token,
                    "fileName": filename,
                },
            }
        ]

        async with session.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate",
            headers=headers,
            json=data,
        ) as resp:
            assert resp.status == 200, f"Media creation failed with status {resp.status}"
            google_response = await resp.json()
            media_result = google_response["newMediaItemResults"][0]
            assert (
                media_result["status"]["message"] == "Success"
            ), f"Media creation failed: {google_response}"
            return media_result["mediaItem"]["productUrl"]


async def create_album() -> Album:
    """
    Create a Google Photos album named "X100VI".
    
    Returns:
        Album model instance with Google Photos album info
    
    Raises:
        AssertionError: If album creation fails
    """
    creds = get_credentials()

    async with aiohttp.ClientSession() as session:
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {creds.token}",
        }
        data = {
            "album": {
                "title": "X100VI",
            }
        }
        async with session.post(
            "https://photoslibrary.googleapis.com/v1/albums",
            headers=headers,
            json=data,
        ) as resp:
            assert resp.status == 200, f"{resp.status}: {await resp.text()}"
            google_response = await resp.json()
            assert (
                google_response["isWriteable"] is True
            ), "Album not writable"
            album = Album.create(
                id=google_response["id"],
                title=google_response["title"],
                productUrl=google_response["productUrl"],
            )
            return album


async def list_albums() -> dict:
    """
    List all Google Photos albums.
    
    Returns:
        Dictionary containing album list from Google Photos API
    """
    creds = get_credentials()

    async with aiohttp.ClientSession() as session:
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {creds.token}",
        }
        async with session.get(
            "https://photoslibrary.googleapis.com/v1/albums",
            headers=headers,
        ) as resp:
            assert resp.status == 200, f"{resp.status}: {await resp.text()}"
            google_response = await resp.json()
            return google_response

