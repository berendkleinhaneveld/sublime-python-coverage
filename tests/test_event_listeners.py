"""Tests for event listeners."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPythonCoverageDataFileListener:
    """Tests for PythonCoverageDataFileListener."""

    def test_is_applicable(self):
        """Test is_applicable returns True."""
        from python_coverage import PythonCoverageDataFileListener

        assert PythonCoverageDataFileListener.is_applicable({}) is True

    def test_update_available_coverage_files_disabled(self, mocker, sublime_window, temp_coverage_file):
        """Test update_available_coverage_files when feature is disabled."""
        from python_coverage import PythonCoverageDataFileListener

        mock_settings = mocker.MagicMock()
        mock_settings.__getitem__.return_value = False  # show_missing_lines = False

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageDataFileListener()
            listener.update_available_coverage_files(sublime_window)

            # Should not add any coverage files
            from python_coverage import COVERAGE_FILES
            assert len(COVERAGE_FILES) == 0

    def test_update_available_coverage_files_enabled(
        self,
        mocker,
        sublime_window,
        tmp_path,
        mock_file_observer
    ):
        """Test update_available_coverage_files when feature is enabled."""
        from python_coverage import PythonCoverageDataFileListener, COVERAGE_FILES

        # Create a .coverage file in the temp directory
        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Update window to point to temp directory
        sublime_window._folders = [str(tmp_path)]

        mock_settings = mocker.MagicMock()
        mock_settings.__getitem__.return_value = True  # show_missing_lines = True

        with patch("sublime.load_settings", return_value=mock_settings), \
             patch("python_coverage.FileWatcher"), \
             patch("python_coverage.FILE_OBSERVER", mock_file_observer), \
             patch("coverage.Coverage"):

            listener = PythonCoverageDataFileListener()
            listener.update_available_coverage_files(sublime_window)

            # Should add the coverage file
            assert len(COVERAGE_FILES) == 1
            assert coverage_file in COVERAGE_FILES


class TestPythonCoverageEventListener:
    """Tests for PythonCoverageEventListener."""

    def test_is_applicable_python_file(self):
        """Test is_applicable returns True for Python files."""
        from python_coverage import PythonCoverageEventListener

        settings = {"syntax": "Packages/Python/Python.sublime-syntax"}
        assert PythonCoverageEventListener.is_applicable(settings) is True

    def test_is_applicable_non_python_file(self):
        """Test is_applicable returns False for non-Python files."""
        from python_coverage import PythonCoverageEventListener

        settings = {"syntax": "Packages/JavaScript/JavaScript.sublime-syntax"}
        assert PythonCoverageEventListener.is_applicable(settings) is False

    def test_on_activated_async_feature_disabled(self, mocker, sublime_view):
        """Test on_activated_async when feature is disabled."""
        from python_coverage import PythonCoverageEventListener

        mock_settings = mocker.MagicMock()
        mock_settings.__getitem__.return_value = False  # show_missing_lines = False

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageEventListener(sublime_view)
            listener.on_activated_async()

            # Should erase regions
            assert "python-coverage" not in sublime_view._regions

    def test_on_activated_async_no_filename(self, mocker, sublime_view):
        """Test on_activated_async when view has no filename."""
        from python_coverage import PythonCoverageEventListener

        sublime_view._file_name = None

        mock_settings = mocker.MagicMock()
        mock_settings.__getitem__.return_value = True  # show_missing_lines = True

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageEventListener(sublime_view)
            listener.on_activated_async()

            # Should not add any regions
            assert "python-coverage" not in sublime_view._regions

    def test_update_regions_no_coverage_file(self, mocker, sublime_view):
        """Test _update_regions when no coverage file is found."""
        from python_coverage import PythonCoverageEventListener

        listener = PythonCoverageEventListener(sublime_view)
        listener._update_regions()

        # Should erase regions when no coverage file found
        assert "python-coverage" not in sublime_view._regions
