"""Basic tests to verify the plugin structure."""

from pathlib import Path


def test_plugin_file_exists():
    """Test that the main plugin file exists."""
    plugin_file = Path(__file__).parent.parent / "python-coverage.py"
    assert plugin_file.exists(), "Main plugin file should exist"


def test_sublime_commands_file_exists():
    """Test that the sublime commands file exists."""
    commands_file = Path(__file__).parent.parent / "python-coverage.sublime-commands"
    assert commands_file.exists(), "Sublime commands file should exist"


def test_sublime_settings_file_exists():
    """Test that the sublime settings file exists."""
    settings_file = Path(__file__).parent.parent / "python-coverage.sublime-settings"
    assert settings_file.exists(), "Sublime settings file should exist"
