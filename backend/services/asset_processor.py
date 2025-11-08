"""
Asset processing service.
Handles file stitching, validation, and triggering Google Photos uploads.
"""
import os
import shutil
import time

from backend.config import get_fuji_part_size, get_images_path
from backend.db.models import Asset, AssetPart, AssetStatus
from backend.services.google_photos import upload_photo

# In bytes, what Fuji camera prefers to break the parts into
FUJI_PART_SIZE = get_fuji_part_size()

# Cache images path to avoid repeated path resolution (performance optimization)
_IMAGES_PATH = get_images_path()


async def stitch_file(asset: Asset) -> None:
    """
    Stitch together file parts into a complete file.
    
    This function:
    1. Combines all part files (filename.1, filename.2, etc.) into one file
    2. Validates the file size matches expected size
    3. Cleans up part files after successful stitching
    4. Updates asset status to AVAILABLE
    
    Args:
        asset: Asset model instance to stitch
    
    Raises:
        AssertionError: If file size doesn't match expected size
    """
    out_file = asset.path
    # Use cached images path for better performance (matches OLD behavior of hardcoded path)
    images_path = _IMAGES_PATH

    # Combine all parts into complete file
    with open(out_file, "wb") as f:
        for part in range(1, asset.parts + 1):
            part_path = os.path.join(images_path, f"{asset.filename}.{part}")
            with open(part_path, "rb") as g:
                shutil.copyfileobj(g, f)

    # Validate file size
    disk_size = os.stat(out_file).st_size
    try:
        assert disk_size == asset.filesize, (
            f"File size mismatch: disk_size={disk_size}, filesize={asset.filesize}"
        )
    except AssertionError:
        asset.delete()
        raise

    # Clean up part files after successful stitching
    for part in range(1, asset.parts + 1):
        part_path = os.path.join(images_path, f"{asset.filename}.{part}")
        try:
            os.remove(part_path)
        except FileNotFoundError:
            pass  # Part file already removed

    # Update asset status
    asset.status = AssetStatus.AVAILABLE
    asset.save()

    # Log timing information
    fully_uploaded_time = time.time()
    picture_taken_time = asset.created.timestamp()
    duration = fully_uploaded_time - picture_taken_time
    print(f"[TIMING] Fully uploaded to computer: {asset.filename}")
    print(
        f"[TIMING]   Picture taken at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(picture_taken_time))}"
    )
    print(
        f"[TIMING]   Fully uploaded at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(fully_uploaded_time))}"
    )
    print(f"[TIMING]   Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")


async def upload_to_google() -> None:
    """
    Upload all available assets to Google Photos.
    
    This function:
    1. Finds all assets with status AVAILABLE
    2. Uploads each to Google Photos
    3. Updates asset status to UPLOADED
    4. Saves Google Photos URL
    
    Assets that fail to upload remain in AVAILABLE status for retry.
    """
    assets = Asset.select().where(Asset.status == AssetStatus.AVAILABLE)
    for asset in assets:
        try:
            google_upload_start = time.time()
            url = await upload_photo(asset.filename)
            google_upload_end = time.time()

            asset.status = AssetStatus.UPLOADED
            asset.google_product_url = url
            asset.save()

            # Log Google upload timing
            picture_taken_time = asset.created.timestamp()
            total_duration = google_upload_end - picture_taken_time
            google_upload_duration = google_upload_end - google_upload_start
            print(f"[TIMING] Uploaded to Google Photos: {asset.filename}")
            print(
                f"[TIMING]   Google upload duration: {google_upload_duration:.2f} seconds"
            )
            print(
                f"[TIMING]   Total time (picture taken → Google Photos): {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)"
            )

            # Optionally delete local file after successful upload
            # Uncomment if you want to free up disk space
            # try:
            #     os.remove(asset.path)
            # except FileNotFoundError:
            #     pass

        except (FileNotFoundError, Exception) as e:
            print(f"Failed to upload {asset.filename} to Google Photos: {e}")
            # Keep asset status as AVAILABLE so it can be retried later
            pass

