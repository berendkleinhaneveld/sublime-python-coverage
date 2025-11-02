"""Tests for plugin commands."""

from unittest.mock import patch


def test_toggle_missing_lines_command_enables(mocker):
    """Test ToggleMissingLinesCommand toggles from False to True."""
    from tests.mocks.sublime import Settings

    mock_settings = Settings()
    mock_settings["show_missing_lines"] = False  # Currently disabled

    with patch("sublime.load_settings", return_value=mock_settings), patch(
        "sublime.save_settings"
    ) as mock_save, patch("builtins.print") as mock_print:
        from python_coverage import ToggleMissingLinesCommand

        cmd = ToggleMissingLinesCommand()
        cmd.run()

        # Should set to True
        assert mock_settings["show_missing_lines"] is True
        mock_save.assert_called_once()
        mock_print.assert_called_once()
        assert "Enabled" in str(mock_print.call_args)


def test_toggle_missing_lines_command_disables(mocker):
    """Test ToggleMissingLinesCommand toggles from True to False."""
    from tests.mocks.sublime import Settings

    mock_settings = Settings()
    mock_settings["show_missing_lines"] = True  # Currently enabled

    with patch("sublime.load_settings", return_value=mock_settings), patch(
        "sublime.save_settings"
    ) as mock_save, patch("builtins.print") as mock_print:
        from python_coverage import ToggleMissingLinesCommand

        cmd = ToggleMissingLinesCommand()
        cmd.run()

        # Should set to False
        assert mock_settings["show_missing_lines"] is False
        mock_save.assert_called_once()
        mock_print.assert_called_once()
        assert "Disabled" in str(mock_print.call_args)
