"""Tests for CoverageManager class."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_coverage_manager_initialization(mock_file_observer):
    """Test CoverageManager initializes correctly."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    assert manager._initialized is True
    assert manager.file_observer is not None
    assert manager.FileWatcher is not None
    assert len(manager.coverage_files) == 0


def test_coverage_manager_add_coverage_file(
    temp_coverage_file,
    mock_coverage_data,
    mock_file_observer
):
    """Test adding a coverage file to the manager."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    success = manager.add_coverage_file(temp_coverage_file)

    assert success is True
    assert temp_coverage_file in manager.coverage_files


def test_coverage_manager_add_duplicate_coverage_file(
    temp_coverage_file,
    mock_coverage_data,
    mock_file_observer
):
    """Test adding a duplicate coverage file returns False."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    manager.add_coverage_file(temp_coverage_file)
    success = manager.add_coverage_file(temp_coverage_file)

    assert success is False


def test_coverage_manager_add_nonexistent_file(mock_file_observer):
    """Test adding a nonexistent coverage file returns False."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    nonexistent = Path("/nonexistent/.coverage")
    success = manager.add_coverage_file(nonexistent)

    assert success is False


def test_coverage_manager_remove_coverage_file(
    temp_coverage_file,
    mock_coverage_data,
    mock_file_observer
):
    """Test removing a coverage file from the manager."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    manager.add_coverage_file(temp_coverage_file)
    success = manager.remove_coverage_file(temp_coverage_file)

    assert success is True
    assert temp_coverage_file not in manager.coverage_files


def test_coverage_manager_get_coverage_for_file(
    temp_coverage_file,
    mock_coverage_data,
    mock_file_observer
):
    """Test getting coverage for a file."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    # File within the coverage directory
    file_path = str(temp_coverage_file.parent / "test.py")

    # Mock measured_files to include our test file
    mock_coverage_data.measured_files.return_value = [file_path]

    cov = manager.get_coverage_for_file(file_path)

    # Should find the coverage file if in_coverage_data returns True
    assert cov is not None


def test_coverage_manager_cleanup_stale_files(
    tmp_path,
    mock_coverage_data,
    mock_file_observer
):
    """Test cleanup of stale coverage files."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    # Create a temporary coverage file
    coverage_file = tmp_path / ".coverage"
    coverage_file.touch()
    manager.add_coverage_file(coverage_file)

    # Delete the file to make it stale
    coverage_file.unlink()

    # Cleanup stale files
    manager.cleanup_stale_files()

    # Should be removed
    assert coverage_file not in manager.coverage_files


def test_coverage_manager_shutdown(
    temp_coverage_file,
    mock_coverage_data,
    mock_file_observer
):
    """Test shutting down the coverage manager."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    manager.shutdown()

    assert len(manager.coverage_files) == 0
    assert manager.file_observer is None
    assert manager._initialized is False
