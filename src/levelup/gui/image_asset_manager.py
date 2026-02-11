"""Image asset management for ticket descriptions."""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path


MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


def save_image(
    image_data: bytes,
    ticket_number: int,
    project_path: Path | str,
    extension: str = "png"
) -> str:
    """
    Save image to ticket asset directory.

    Args:
        image_data: Raw image bytes
        ticket_number: Ticket number for filename
        project_path: Project root path
        extension: Image file extension (png, jpg, jpeg, gif)

    Returns:
        Relative path from project root (e.g., "levelup/ticket-assets/ticket-1-...")
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    # Create asset directory
    asset_dir = project_path / "levelup" / "ticket-assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp and hash for uniqueness
    # Include microseconds for better collision prevention
    timestamp = time.strftime("%Y%m%d%H%M%S") + f"{int(time.time() * 1000000) % 1000000:06d}"
    data_hash = hashlib.md5(image_data).hexdigest()[:8]
    filename = f"ticket-{ticket_number}-{timestamp}-{data_hash}.{extension}"

    # Write file
    filepath = asset_dir / filename
    filepath.write_bytes(image_data)

    # Return relative path
    return normalize_image_path(f"levelup/ticket-assets/{filename}")


def load_image(
    relative_path: str,
    project_path: Path | str
) -> bytes | None:
    """
    Load image from asset directory.

    Args:
        relative_path: Relative path from project root
        project_path: Project root path

    Returns:
        Image bytes or None if not found
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    # Handle absolute paths by converting to relative
    filepath = Path(relative_path)
    if filepath.is_absolute():
        try:
            filepath = filepath.relative_to(project_path)
        except ValueError:
            # Path is not relative to project_path
            return None

    full_path = project_path / filepath

    if not full_path.exists():
        return None

    try:
        return full_path.read_bytes()
    except Exception:
        return None


def cleanup_ticket_images(
    ticket_number: int,
    project_path: Path | str,
    filename: str | None = None
) -> None:
    """
    Remove all images associated with a ticket.

    Args:
        ticket_number: Ticket number to clean up
        project_path: Project root path
        filename: Tickets filename (unused, for compatibility)
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    asset_dir = project_path / "levelup" / "ticket-assets"

    if not asset_dir.exists():
        return

    # Pattern to match ticket-N-* files (with boundary to avoid ticket-1 matching ticket-10)
    pattern = f"ticket-{ticket_number}-*"

    for img_file in asset_dir.glob(pattern):
        # Double-check we're not matching ticket-10 when deleting ticket-1
        name = img_file.name
        if name.startswith(f"ticket-{ticket_number}-"):
            try:
                img_file.unlink()
            except Exception:
                # Ignore errors (file may be locked, etc.)
                pass


def cleanup_orphaned_images(
    description: str,
    ticket_number: int,
    project_path: Path | str
) -> None:
    """
    Remove images not referenced in description.

    Args:
        description: Markdown description with image references
        ticket_number: Ticket number
        project_path: Project root path
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    asset_dir = project_path / "levelup" / "ticket-assets"

    if not asset_dir.exists():
        return

    # Find all image references in markdown: ![alt](path)
    referenced_images = set()
    for match in re.finditer(r'!\[.*?\]\((.*?)\)', description):
        img_path = match.group(1)
        # Extract just the filename
        filename = Path(img_path).name
        referenced_images.add(filename)

    # Find all images for this ticket
    pattern = f"ticket-{ticket_number}-*"
    for img_file in asset_dir.glob(pattern):
        if img_file.name not in referenced_images:
            try:
                img_file.unlink()
            except Exception:
                pass


def validate_image_size(image_data: bytes) -> bool:
    """
    Validate image size is under limit.

    Args:
        image_data: Raw image bytes

    Returns:
        True if under limit, False otherwise
    """
    return len(image_data) <= MAX_IMAGE_SIZE


def validate_image_format(image_data: bytes, extension: str) -> bool:
    """
    Validate image format matches extension (basic check).

    Args:
        image_data: Raw image bytes
        extension: Expected extension

    Returns:
        True if format appears valid
    """
    # Basic magic byte checks
    if not image_data:
        return False

    if extension.lower() == "png":
        return image_data.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension.lower() in ("jpg", "jpeg"):
        return image_data.startswith(b"\xff\xd8\xff")
    elif extension.lower() == "gif":
        return image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a")

    # Unknown format, assume valid
    return True


def get_image_extension(image_data: bytes) -> str | None:
    """
    Detect image extension from data.

    Args:
        image_data: Raw image bytes

    Returns:
        Extension string or None if unknown
    """
    if not image_data:
        return None

    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    elif image_data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    elif image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
        return "gif"

    return None


def normalize_image_path(path: str) -> str:
    """
    Normalize image path for cross-platform compatibility.

    Args:
        path: Path to normalize

    Returns:
        Normalized path with forward slashes
    """
    return path.replace("\\", "/")
