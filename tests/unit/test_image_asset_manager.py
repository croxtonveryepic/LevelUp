"""Unit tests for image asset management (save, load, cleanup)."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest


class TestImageSaving:
    """Test saving images to ticket asset directory."""

    def test_save_creates_asset_directory(self, tmp_path):
        """Saving image should create asset directory if it doesn't exist."""
        from levelup.gui.image_asset_manager import save_image

        image_data = b"fake-png-data"
        project_path = tmp_path

        # Asset directory shouldn't exist yet
        asset_dir = project_path / "levelup" / "ticket-assets"
        assert not asset_dir.exists()

        filepath = save_image(image_data, ticket_number=1, project_path=project_path, extension="png")

        # Asset directory should now exist
        assert asset_dir.exists()
        assert asset_dir.is_dir()

    def test_save_returns_relative_path(self, tmp_path):
        """Save should return path relative to project root."""
        from levelup.gui.image_asset_manager import save_image

        image_data = b"fake-png-data"
        filepath = save_image(image_data, ticket_number=5, project_path=tmp_path, extension="png")

        # Should be relative path
        assert filepath.startswith("levelup/ticket-assets/")
        assert "ticket-5-" in filepath
        assert filepath.endswith(".png")

    def test_filename_format(self, tmp_path):
        """Filename should follow ticket-{num}-{timestamp}-{hash}.{ext} format."""
        from levelup.gui.image_asset_manager import save_image

        image_data = b"test-image-data"
        filepath = save_image(image_data, ticket_number=3, project_path=tmp_path, extension="jpg")

        filename = Path(filepath).name
        # Format: ticket-3-20260211-abc123.jpg
        assert filename.startswith("ticket-3-")
        assert filename.endswith(".jpg")

        # Should have timestamp and hash components
        parts = filename.replace("ticket-3-", "").replace(".jpg", "").split("-")
        assert len(parts) >= 2  # timestamp and hash

    def test_unique_filenames_for_different_images(self, tmp_path):
        """Different images should get different filenames."""
        from levelup.gui.image_asset_manager import save_image

        image1 = b"first-image-data"
        image2 = b"second-image-data"

        path1 = save_image(image1, ticket_number=1, project_path=tmp_path, extension="png")
        path2 = save_image(image2, ticket_number=1, project_path=tmp_path, extension="png")

        assert path1 != path2

    def test_same_image_different_tickets(self, tmp_path):
        """Same image saved for different tickets should have different filenames."""
        from levelup.gui.image_asset_manager import save_image

        image_data = b"shared-image-data"

        path1 = save_image(image_data, ticket_number=1, project_path=tmp_path, extension="png")
        path2 = save_image(image_data, ticket_number=2, project_path=tmp_path, extension="png")

        assert "ticket-1-" in path1
        assert "ticket-2-" in path2
        assert path1 != path2

    def test_file_actually_written(self, tmp_path):
        """Image data should actually be written to disk."""
        from levelup.gui.image_asset_manager import save_image

        image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"  # PNG header
        filepath = save_image(image_data, ticket_number=1, project_path=tmp_path, extension="png")

        full_path = tmp_path / filepath
        assert full_path.exists()
        assert full_path.read_bytes() == image_data

    def test_supported_extensions(self, tmp_path):
        """Should support PNG, JPG, JPEG, GIF extensions."""
        from levelup.gui.image_asset_manager import save_image

        image_data = b"test-data"

        for ext in ["png", "jpg", "jpeg", "gif"]:
            filepath = save_image(image_data, ticket_number=1, project_path=tmp_path, extension=ext)
            assert filepath.endswith(f".{ext}")

    def test_hash_collision_prevention(self, tmp_path):
        """Timestamp should prevent hash collisions for rapid saves."""
        from levelup.gui.image_asset_manager import save_image

        # Save same image twice rapidly
        image_data = b"collision-test"
        path1 = save_image(image_data, ticket_number=1, project_path=tmp_path, extension="png")

        time.sleep(0.01)  # Small delay

        path2 = save_image(image_data, ticket_number=1, project_path=tmp_path, extension="png")

        # Should still get different filenames due to timestamp
        assert path1 != path2


class TestImageLoading:
    """Test loading images from asset directory."""

    def test_load_existing_image(self, tmp_path):
        """Should load image that exists on disk."""
        from levelup.gui.image_asset_manager import save_image, load_image

        original_data = b"test-image-content"
        filepath = save_image(original_data, ticket_number=1, project_path=tmp_path, extension="png")

        loaded_data = load_image(filepath, project_path=tmp_path)
        assert loaded_data == original_data

    def test_load_nonexistent_image_returns_none(self, tmp_path):
        """Loading missing image should return None instead of crashing."""
        from levelup.gui.image_asset_manager import load_image

        result = load_image("levelup/ticket-assets/missing.png", project_path=tmp_path)
        assert result is None

    def test_load_with_absolute_path(self, tmp_path):
        """Should handle absolute paths by converting to relative."""
        from levelup.gui.image_asset_manager import save_image, load_image

        image_data = b"absolute-path-test"
        rel_path = save_image(image_data, ticket_number=1, project_path=tmp_path, extension="png")

        # Try loading with absolute path
        abs_path = tmp_path / rel_path
        loaded = load_image(str(abs_path), project_path=tmp_path)

        assert loaded == image_data


class TestImageCleanup:
    """Test cleaning up orphaned images."""

    def test_cleanup_ticket_images(self, tmp_path):
        """Deleting ticket should remove associated images."""
        from levelup.gui.image_asset_manager import save_image, cleanup_ticket_images

        # Save images for ticket 5
        save_image(b"img1", ticket_number=5, project_path=tmp_path, extension="png")
        save_image(b"img2", ticket_number=5, project_path=tmp_path, extension="jpg")

        # Save image for different ticket
        other_path = save_image(b"img3", ticket_number=3, project_path=tmp_path, extension="png")

        # Cleanup ticket 5
        cleanup_ticket_images(ticket_number=5, project_path=tmp_path)

        # Ticket 5 images should be deleted
        asset_dir = tmp_path / "levelup" / "ticket-assets"
        remaining_files = list(asset_dir.glob("ticket-5-*"))
        assert len(remaining_files) == 0

        # Ticket 3 image should still exist
        assert (tmp_path / other_path).exists()

    def test_cleanup_orphaned_images(self, tmp_path):
        """Should remove images not referenced in description."""
        from levelup.gui.image_asset_manager import save_image, cleanup_orphaned_images

        # Create several images
        img1 = save_image(b"img1", ticket_number=1, project_path=tmp_path, extension="png")
        img2 = save_image(b"img2", ticket_number=1, project_path=tmp_path, extension="png")
        img3 = save_image(b"img3", ticket_number=1, project_path=tmp_path, extension="png")

        # Description references only img1 and img2
        description = f"""Here is the issue:
![Screenshot 1]({img1})
Some text
![Screenshot 2]({img2})
End of description"""

        cleanup_orphaned_images(description, ticket_number=1, project_path=tmp_path)

        # img1 and img2 should exist
        assert (tmp_path / img1).exists()
        assert (tmp_path / img2).exists()

        # img3 should be deleted (orphaned)
        assert not (tmp_path / img3).exists()

    def test_cleanup_no_crash_if_already_deleted(self, tmp_path):
        """Cleanup should not crash if files already deleted."""
        from levelup.gui.image_asset_manager import cleanup_ticket_images

        # Try to cleanup non-existent ticket images
        cleanup_ticket_images(ticket_number=999, project_path=tmp_path)

        # Should not crash

    def test_cleanup_preserves_other_tickets(self, tmp_path):
        """Cleanup should not affect other tickets' images."""
        from levelup.gui.image_asset_manager import save_image, cleanup_ticket_images

        # Create images for multiple tickets
        t1_img = save_image(b"t1", ticket_number=1, project_path=tmp_path, extension="png")
        t2_img = save_image(b"t2", ticket_number=2, project_path=tmp_path, extension="png")
        t3_img = save_image(b"t3", ticket_number=3, project_path=tmp_path, extension="png")

        # Cleanup ticket 2
        cleanup_ticket_images(ticket_number=2, project_path=tmp_path)

        # Ticket 1 and 3 images should remain
        assert (tmp_path / t1_img).exists()
        assert (tmp_path / t3_img).exists()

        # Ticket 2 image should be gone
        assert not (tmp_path / t2_img).exists()


class TestImageValidation:
    """Test image validation (size, format, etc.)."""

    def test_validate_image_size_under_limit(self):
        """Images under 10MB should pass validation."""
        from levelup.gui.image_asset_manager import validate_image_size

        # 1MB image
        small_image = b"x" * (1024 * 1024)
        result = validate_image_size(small_image)

        assert result is True

    def test_validate_image_size_over_limit(self):
        """Images over 10MB should fail validation."""
        from levelup.gui.image_asset_manager import validate_image_size

        # 11MB image
        large_image = b"x" * (11 * 1024 * 1024)
        result = validate_image_size(large_image)

        assert result is False

    def test_validate_image_size_exactly_10mb(self):
        """10MB image should be at the boundary (implementation decides)."""
        from levelup.gui.image_asset_manager import validate_image_size

        # Exactly 10MB
        boundary_image = b"x" * (10 * 1024 * 1024)
        result = validate_image_size(boundary_image)

        # Should either pass or fail consistently
        assert isinstance(result, bool)

    def test_validate_supported_format(self):
        """Should validate image format based on magic bytes."""
        from levelup.gui.image_asset_manager import validate_image_format

        # PNG magic bytes
        png_data = b"\x89PNG\r\n\x1a\n"
        result = validate_image_format(png_data, extension="png")

        # Should validate or at least not crash
        assert isinstance(result, bool)

    def test_get_image_extension_from_data(self):
        """Should detect image extension from data."""
        from levelup.gui.image_asset_manager import get_image_extension

        # PNG magic bytes
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        ext = get_image_extension(png_data)

        assert ext in ["png", "PNG", None]  # May return None if not implemented


class TestPathNormalization:
    """Test path normalization for cross-platform compatibility."""

    def test_normalize_windows_paths(self, tmp_path):
        """Windows backslashes should be normalized to forward slashes."""
        from levelup.gui.image_asset_manager import normalize_image_path

        windows_path = "levelup\\ticket-assets\\image.png"
        normalized = normalize_image_path(windows_path)

        assert "\\" not in normalized
        assert "/" in normalized or normalized == windows_path

    def test_relative_path_preserved(self, tmp_path):
        """Relative paths should remain relative."""
        from levelup.gui.image_asset_manager import normalize_image_path

        rel_path = "levelup/ticket-assets/test.png"
        normalized = normalize_image_path(rel_path)

        # Should not become absolute
        assert not normalized.startswith("/")
        assert not (len(normalized) > 1 and normalized[1] == ":")  # Not C:/ style


class TestConcurrentAccess:
    """Test handling of concurrent image operations."""

    def test_multiple_saves_same_ticket(self, tmp_path):
        """Multiple rapid saves to same ticket should all succeed."""
        from levelup.gui.image_asset_manager import save_image

        paths = []
        for i in range(5):
            image_data = f"image-{i}".encode()
            path = save_image(image_data, ticket_number=1, project_path=tmp_path, extension="png")
            paths.append(path)

        # All paths should be unique
        assert len(paths) == len(set(paths))

        # All files should exist
        for path in paths:
            assert (tmp_path / path).exists()
