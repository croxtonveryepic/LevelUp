"""Unit tests for CLI ticket commands with image references."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.tickets import add_ticket, read_tickets


class TestCLITicketListWithImages:
    """Test that 'levelup tickets list' displays tickets with images correctly."""

    def test_list_tickets_with_images_no_crash(self, tmp_path):
        """List command should not crash on tickets with image references."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket with image reference
        description = "Bug description:\n![Screenshot](levelup/ticket-assets/bug.png)"
        add_ticket(tmp_path, "Bug report", description)

        tickets = read_tickets(tmp_path)

        # Should read successfully
        assert len(tickets) == 1
        assert "![Screenshot]" in tickets[0].description or "bug.png" in tickets[0].description

    def test_list_shows_image_markdown_syntax(self, tmp_path):
        """List should display markdown image syntax as-is."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "![Error](levelup/ticket-assets/error.png)"
        add_ticket(tmp_path, "Test", description)

        tickets = read_tickets(tmp_path)

        # Should preserve markdown syntax
        assert "![" in tickets[0].description
        assert "error.png" in tickets[0].description

    def test_list_multiple_tickets_with_images(self, tmp_path):
        """List should handle multiple tickets with images."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        add_ticket(tmp_path, "Ticket 1", "![Img1](levelup/ticket-assets/img1.png)")
        add_ticket(tmp_path, "Ticket 2", "Plain text")
        add_ticket(tmp_path, "Ticket 3", "![Img3](levelup/ticket-assets/img3.png)")

        tickets = read_tickets(tmp_path)

        assert len(tickets) == 3
        assert "img1.png" in tickets[0].description
        assert "Plain text" in tickets[1].description
        assert "img3.png" in tickets[2].description


class TestCLITicketNextWithImages:
    """Test that 'levelup tickets next' works with image references."""

    def test_next_ticket_with_images(self, tmp_path):
        """Next command should work with tickets containing images."""
        from levelup.core.tickets import get_next_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "Steps to reproduce:\n![Step 1](levelup/ticket-assets/step1.png)"
        add_ticket(tmp_path, "Reproduce bug", description)

        next_ticket = get_next_ticket(tmp_path)

        assert next_ticket is not None
        assert "step1.png" in next_ticket.description


class TestCLITicketToTaskInput:
    """Test Ticket.to_task_input() preserves markdown format."""

    def test_to_task_input_preserves_markdown(self, tmp_path):
        """to_task_input should preserve markdown image syntax."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "Bug:\n![Screenshot](levelup/ticket-assets/bug.png)\nDetails here"
        ticket = add_ticket(tmp_path, "Bug", description)

        task_input = ticket.to_task_input()

        # Should preserve markdown format
        assert "![Screenshot]" in task_input.description or "bug.png" in task_input.description
        assert "Details here" in task_input.description

    def test_to_task_input_multiple_images(self, tmp_path):
        """to_task_input should preserve multiple image references."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = """Problem:
![Before](levelup/ticket-assets/before.png)
After fix:
![After](levelup/ticket-assets/after.png)"""

        ticket = add_ticket(tmp_path, "Test", description)
        task_input = ticket.to_task_input()

        # Both images should be preserved
        assert "before.png" in task_input.description
        assert "after.png" in task_input.description


class TestAgentAccessToImagePaths:
    """Test that agents can access image paths from ticket descriptions."""

    def test_agent_sees_image_paths_in_markdown(self, tmp_path):
        """Agents receive ticket description with visible image paths."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "The error shown in ![this screenshot](levelup/ticket-assets/error.png) occurs"
        ticket = add_ticket(tmp_path, "Error", description)

        task_input = ticket.to_task_input()

        # Agent can see the path in markdown
        assert "levelup/ticket-assets/error.png" in task_input.description

    def test_agent_can_read_referenced_image_files(self, tmp_path):
        """Agents can use file tools to read referenced images if needed."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create actual image file
        asset_dir = tickets_dir / "ticket-assets"
        asset_dir.mkdir()
        img_path = asset_dir / "error.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header

        description = "![Error](levelup/ticket-assets/error.png)"
        ticket = add_ticket(tmp_path, "Bug", description)

        task_input = ticket.to_task_input()

        # Agent knows the path
        assert "error.png" in task_input.description

        # Agent could read the file if needed
        full_path = tmp_path / "levelup" / "ticket-assets" / "error.png"
        assert full_path.exists()
        assert full_path.read_bytes().startswith(b"\x89PNG")


class TestMarkdownDisplayInCLI:
    """Test that markdown image syntax displays acceptably in CLI."""

    def test_markdown_syntax_readable_in_cli(self, tmp_path):
        """Markdown image syntax should be readable in CLI output."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "Check ![this error screenshot](levelup/ticket-assets/error.png) for details"
        ticket = add_ticket(tmp_path, "Test", description)

        # CLI would display raw markdown, which is readable
        # "Check ![this error screenshot](levelup/ticket-assets/error.png) for details"
        # User can still understand what the ticket is about

        assert "![this error screenshot]" in ticket.description
        assert "for details" in ticket.description

    def test_multiple_images_cli_display(self, tmp_path):
        """Multiple images in CLI should still be understandable."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = """Steps:
1. Open app ![app](levelup/ticket-assets/app.png)
2. Click button ![button](levelup/ticket-assets/btn.png)
3. Error appears"""

        ticket = add_ticket(tmp_path, "Steps", description)

        # Should be readable in CLI
        assert "Steps:" in ticket.description
        assert "Error appears" in ticket.description


class TestImageReferencesInDifferentFormats:
    """Test handling of different image reference formats."""

    def test_relative_path_preserved(self, tmp_path):
        """Relative paths in markdown should be preserved."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "![Test](levelup/ticket-assets/test.png)"
        ticket = add_ticket(tmp_path, "Test", description)

        task_input = ticket.to_task_input()
        assert "levelup/ticket-assets/test.png" in task_input.description

    def test_forward_slashes_in_paths(self, tmp_path):
        """Forward slashes in paths should be preserved."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "![Test](levelup/ticket-assets/sub/test.png)"
        ticket = add_ticket(tmp_path, "Test", description)

        # Should preserve forward slashes
        assert "levelup/ticket-assets/sub/test.png" in ticket.description

    def test_image_with_spaces_in_alt_text(self, tmp_path):
        """Alt text with spaces should be handled."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        description = "![Error message screenshot](levelup/ticket-assets/error.png)"
        ticket = add_ticket(tmp_path, "Test", description)

        assert "Error message screenshot" in ticket.description


class TestBackwardCompatibilityWithCLI:
    """Test backward compatibility for existing tickets."""

    def test_old_tickets_without_images_work_in_cli(self, tmp_path):
        """Old tickets without images should work normally."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Old-style plain text ticket
        ticket = add_ticket(tmp_path, "Old ticket", "Just plain text description")

        task_input = ticket.to_task_input()

        assert task_input.description == "Just plain text description"

    def test_mixed_old_and_new_tickets_in_cli(self, tmp_path):
        """CLI should handle mix of old and new tickets."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Old ticket
        add_ticket(tmp_path, "Old", "Plain text")

        # New ticket with image
        add_ticket(tmp_path, "New", "![Img](levelup/ticket-assets/img.png)")

        tickets = read_tickets(tmp_path)

        assert len(tickets) == 2
        assert tickets[0].description == "Plain text"
        assert "img.png" in tickets[1].description


class TestTicketDescriptionParsing:
    """Test that ticket description parsing handles images correctly."""

    def test_parse_preserves_image_syntax(self, tmp_path):
        """Parsing tickets.md should preserve image markdown."""
        from levelup.core.tickets import parse_tickets

        markdown = """## Bug report
![Screenshot](levelup/ticket-assets/bug.png)
The button is broken.
"""

        tickets = parse_tickets(markdown)

        assert len(tickets) == 1
        assert "![Screenshot]" in tickets[0].description
        assert "bug.png" in tickets[0].description
        assert "button is broken" in tickets[0].description

    def test_parse_multiple_images_in_description(self, tmp_path):
        """Parser should handle multiple images in description."""
        from levelup.core.tickets import parse_tickets

        markdown = """## Test
First ![img1](levelup/ticket-assets/1.png)
Second ![img2](levelup/ticket-assets/2.png)
"""

        tickets = parse_tickets(markdown)

        assert "1.png" in tickets[0].description
        assert "2.png" in tickets[0].description

    def test_parse_image_in_code_block_ignored(self, tmp_path):
        """Images in code blocks should be treated as code."""
        from levelup.core.tickets import parse_tickets

        markdown = """## Ticket
Regular image: ![real](levelup/ticket-assets/real.png)

```markdown
Example: ![fake](levelup/ticket-assets/fake.png)
```
"""

        tickets = parse_tickets(markdown)

        # Both should be in description (parser doesn't interpret markdown semantics)
        assert "real.png" in tickets[0].description
        assert "fake.png" in tickets[0].description


class TestCLIErrorHandling:
    """Test error handling in CLI with image references."""

    def test_missing_image_file_doesnt_break_cli(self, tmp_path):
        """Missing image file shouldn't prevent CLI from working."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Reference non-existent image
        description = "![Missing](levelup/ticket-assets/missing.png)"
        ticket = add_ticket(tmp_path, "Test", description)

        # Should read successfully
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1

        # Description should still be there
        assert "missing.png" in tickets[0].description

    def test_malformed_image_markdown_doesnt_crash(self, tmp_path):
        """Malformed image markdown shouldn't crash CLI."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Malformed markdown
        description = "![No closing paren](levelup/ticket-assets/test.png"
        ticket = add_ticket(tmp_path, "Test", description)

        # Should still work
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
