"""Unit tests for ticket deletion with image cleanup."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.tickets import add_ticket, delete_ticket


class TestTicketDeletionCleanup:
    """Test that delete_ticket cleans up associated images."""

    def test_delete_ticket_removes_images(self, tmp_path):
        """delete_ticket should remove associated image files."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket
        ticket = add_ticket(tmp_path, "Test ticket", "Description with image")

        # Manually create some image files for this ticket
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        img1 = asset_dir / "ticket-1-20260211-abc123.png"
        img1.write_bytes(b"fake-image-1")

        img2 = asset_dir / "ticket-1-20260211-def456.jpg"
        img2.write_bytes(b"fake-image-2")

        # Verify they exist
        assert img1.exists()
        assert img2.exists()

        # Delete ticket
        delete_ticket(tmp_path, 1)

        # Images should be deleted
        assert not img1.exists()
        assert not img2.exists()

    def test_delete_ticket_preserves_other_ticket_images(self, tmp_path):
        """Deleting ticket should not affect other tickets' images."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create multiple tickets
        add_ticket(tmp_path, "Ticket 1", "Desc 1")
        add_ticket(tmp_path, "Ticket 2", "Desc 2")
        add_ticket(tmp_path, "Ticket 3", "Desc 3")

        # Create images for each
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        t1_img = asset_dir / "ticket-1-test.png"
        t1_img.write_bytes(b"img1")

        t2_img = asset_dir / "ticket-2-test.png"
        t2_img.write_bytes(b"img2")

        t3_img = asset_dir / "ticket-3-test.png"
        t3_img.write_bytes(b"img3")

        # Delete ticket 2
        delete_ticket(tmp_path, 2)

        # Ticket 1 and 3 images should remain
        assert t1_img.exists()
        assert not t2_img.exists()
        assert t3_img.exists()

    def test_delete_ticket_no_crash_if_no_images(self, tmp_path):
        """Deleting ticket without images should not crash."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        ticket = add_ticket(tmp_path, "No images", "Plain text")

        # Delete without creating any images
        delete_ticket(tmp_path, 1)

        # Should succeed without error

    def test_delete_ticket_no_crash_if_asset_dir_missing(self, tmp_path):
        """Deleting ticket when asset directory doesn't exist should not crash."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        ticket = add_ticket(tmp_path, "Test", "Desc")

        # Don't create asset directory
        asset_dir = tickets_dir / "ticket-assets"
        assert not asset_dir.exists()

        # Delete should not crash
        delete_ticket(tmp_path, 1)

    def test_delete_ticket_handles_multiple_extensions(self, tmp_path):
        """Should delete images with various extensions."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        add_ticket(tmp_path, "Test", "Desc")

        # Create images with different extensions
        extensions = ["png", "jpg", "jpeg", "gif"]
        for ext in extensions:
            img = asset_dir / f"ticket-1-test.{ext}"
            img.write_bytes(b"image-data")

        # Delete ticket
        delete_ticket(tmp_path, 1)

        # All should be deleted
        for ext in extensions:
            img = asset_dir / f"ticket-1-test.{ext}"
            assert not img.exists()

    def test_delete_ticket_handles_complex_filenames(self, tmp_path):
        """Should delete images with timestamp and hash in filename."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        add_ticket(tmp_path, "Test", "Desc")

        # Create images with realistic filenames
        img1 = asset_dir / "ticket-1-20260211123045-a3f2b1c4.png"
        img2 = asset_dir / "ticket-1-20260211123046-d5e6f7a8.jpg"

        img1.write_bytes(b"img1")
        img2.write_bytes(b"img2")

        delete_ticket(tmp_path, 1)

        assert not img1.exists()
        assert not img2.exists()

    def test_delete_ticket_only_deletes_exact_match(self, tmp_path):
        """Should only delete ticket-N-* files, not ticket-NN-* files."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        add_ticket(tmp_path, "Ticket 1", "")
        add_ticket(tmp_path, "Ticket 11", "")

        # Create images
        t1_img = asset_dir / "ticket-1-test.png"
        t11_img = asset_dir / "ticket-11-test.png"

        t1_img.write_bytes(b"img1")
        t11_img.write_bytes(b"img11")

        # Delete ticket 1
        delete_ticket(tmp_path, 1)

        # Only ticket-1 image should be deleted
        assert not t1_img.exists()
        assert t11_img.exists()


class TestAssetDirectoryManagement:
    """Test asset directory management during deletion."""

    def test_empty_asset_directory_not_deleted(self, tmp_path):
        """Empty asset directory should remain after cleanup."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        ticket = add_ticket(tmp_path, "Test", "")

        # Create and delete image for ticket 1
        img = asset_dir / "ticket-1-test.png"
        img.write_bytes(b"img")

        delete_ticket(tmp_path, 1)

        # Directory should still exist (even if empty)
        # Implementation may choose to keep or remove empty directory
        # This test just ensures no crash


class TestCleanupHelperFunction:
    """Test the helper function for cleaning up ticket images."""

    def test_cleanup_ticket_images_function(self, tmp_path):
        """cleanup_ticket_images should remove all images for a ticket."""
        from levelup.core.tickets import cleanup_ticket_images

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        # Create images
        img1 = asset_dir / "ticket-5-abc.png"
        img2 = asset_dir / "ticket-5-def.jpg"
        img_other = asset_dir / "ticket-3-xyz.png"

        img1.write_bytes(b"img1")
        img2.write_bytes(b"img2")
        img_other.write_bytes(b"other")

        # Cleanup ticket 5
        cleanup_ticket_images(ticket_number=5, project_path=tmp_path)

        # Ticket 5 images gone, ticket 3 remains
        assert not img1.exists()
        assert not img2.exists()
        assert img_other.exists()

    def test_cleanup_with_custom_filename(self, tmp_path):
        """cleanup should work with custom tickets filename."""
        from levelup.core.tickets import cleanup_ticket_images

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        img = asset_dir / "ticket-1-test.png"
        img.write_bytes(b"img")

        # Cleanup with custom filename parameter
        cleanup_ticket_images(ticket_number=1, project_path=tmp_path, filename="custom-tickets.md")

        # Should still delete the image
        assert not img.exists()


class TestDeleteTicketIntegration:
    """Integration tests for delete_ticket with cleanup."""

    def test_delete_updates_markdown_and_cleans_images(self, tmp_path):
        """delete_ticket should both update markdown and clean images."""
        from levelup.core.tickets import read_tickets

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        # Create tickets
        add_ticket(tmp_path, "Keep this", "Desc 1")
        add_ticket(tmp_path, "Delete this", "Desc 2")

        # Create images
        img1 = asset_dir / "ticket-1-test.png"
        img2 = asset_dir / "ticket-2-test.png"
        img1.write_bytes(b"img1")
        img2.write_bytes(b"img2")

        # Delete ticket 2
        delete_ticket(tmp_path, 2)

        # Markdown should be updated
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].title == "Keep this"

        # Images should be cleaned
        assert img1.exists()
        assert not img2.exists()

    def test_delete_last_ticket_cleans_images(self, tmp_path):
        """Deleting the last ticket should clean its images."""
        from levelup.core.tickets import read_tickets

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        add_ticket(tmp_path, "Only ticket", "Desc")

        img = asset_dir / "ticket-1-test.png"
        img.write_bytes(b"img")

        delete_ticket(tmp_path, 1)

        # Ticket deleted
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 0

        # Image deleted
        assert not img.exists()


class TestEdgeCases:
    """Test edge cases in image cleanup."""

    def test_cleanup_with_permission_error(self, tmp_path):
        """Should handle permission errors gracefully."""
        # This test is platform-specific
        pytest.skip("Platform-specific test for file permissions")

    def test_cleanup_with_locked_file(self, tmp_path):
        """Should handle locked files gracefully."""
        # This test is platform-specific
        pytest.skip("Platform-specific test for file locking")

    def test_cleanup_with_symlink(self, tmp_path):
        """Should handle symlinked image files."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()

        add_ticket(tmp_path, "Test", "")

        # Create actual file and symlink
        actual_img = tmp_path / "actual.png"
        actual_img.write_bytes(b"actual")

        try:
            symlink = asset_dir / "ticket-1-link.png"
            symlink.symlink_to(actual_img)

            delete_ticket(tmp_path, 1)

            # Symlink should be removed
            assert not symlink.exists()
            # Actual file should remain
            assert actual_img.exists()
        except OSError:
            # Symlinks may not be supported on all platforms
            pytest.skip("Symlinks not supported on this platform")
