"""Tests for CoverageManager class."""

from pathlib import Path


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
    temp_coverage_file, mock_coverage_data, mock_file_observer
):
    """Test adding a coverage file to the manager."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    success = manager.add_coverage_file(temp_coverage_file)

    assert success is True
    assert temp_coverage_file in manager.coverage_files


def test_coverage_manager_add_duplicate_coverage_file(
    temp_coverage_file, mock_coverage_data, mock_file_observer
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
    temp_coverage_file, mock_coverage_data, mock_file_observer
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
    temp_coverage_file, mock_coverage_data, mock_file_observer
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


def test_coverage_manager_cleanup_stale_files(tmp_path, mock_coverage_data, mock_file_observer):
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


def test_coverage_manager_shutdown(temp_coverage_file, mock_coverage_data, mock_file_observer):
    """Test shutting down the coverage manager."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    manager.shutdown()

    assert len(manager.coverage_files) == 0
    assert manager.file_observer is None
    assert manager._initialized is False


def test_debounced_update_schedules_timer(
    temp_coverage_file, mock_coverage_data, mock_file_observer
):
    """Test that _schedule_debounced_update schedules a timer."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    # Schedule an update
    manager._schedule_debounced_update(temp_coverage_file)

    # Verify timer was created
    assert temp_coverage_file in manager._update_timers
    timer = manager._update_timers[temp_coverage_file]
    assert timer.is_alive()

    # Cleanup
    timer.cancel()


def test_debounced_update_cancels_existing_timer(
    temp_coverage_file, mock_coverage_data, mock_file_observer
):
    """Test that scheduling a new update cancels the existing timer."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    # Schedule first update
    manager._schedule_debounced_update(temp_coverage_file)
    first_timer = manager._update_timers[temp_coverage_file]

    # Schedule second update
    manager._schedule_debounced_update(temp_coverage_file)
    second_timer = manager._update_timers[temp_coverage_file]

    # First timer should be cancelled, second should be active
    assert first_timer is not second_timer
    assert not first_timer.is_alive()
    assert second_timer.is_alive()

    # Cleanup
    second_timer.cancel()


def test_perform_debounced_update_updates_coverage(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test that _perform_debounced_update updates the coverage file."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    cov_file = manager.coverage_files[temp_coverage_file]
    spy = mocker.spy(cov_file, "update")

    # Perform the update
    manager._perform_debounced_update(temp_coverage_file)

    # Verify update was called
    spy.assert_called_once()


def test_perform_debounced_update_removes_nonexistent_file(
    temp_coverage_file, mock_coverage_data, mock_file_observer
):
    """Test that _perform_debounced_update removes file if it no longer exists."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    # Delete the file
    temp_coverage_file.unlink()

    # Perform the update
    manager._perform_debounced_update(temp_coverage_file)

    # File should be removed from manager
    assert temp_coverage_file not in manager.coverage_files


def test_perform_debounced_update_handles_untracked_file(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test that _perform_debounced_update handles untracked files gracefully."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()

    # Don't add the file to manager, but try to update it
    # This should not raise an exception
    manager._perform_debounced_update(temp_coverage_file)

    # No assertions needed - just verifying no exception is raised


def test_perform_debounced_update_updates_active_views(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker, sublime_view
):
    """Test that _perform_debounced_update updates all active views."""
    import python_coverage as pc
    from python_coverage import CoverageManager

    # Create a mock view listener
    mock_listener = mocker.MagicMock()
    mock_listener._update_regions = mocker.MagicMock()

    # Add to active views
    pc.ACTIVE_VIEWS = {1: mock_listener}

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    # Perform the update
    manager._perform_debounced_update(temp_coverage_file)

    # Verify _update_regions was called
    mock_listener._update_regions.assert_called_once()

    # Cleanup
    pc.ACTIVE_VIEWS = {}


def test_file_watcher_on_modified(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test FileWatcher.on_modified triggers debounced update."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    # Create a FileWatcher instance
    watcher = manager.FileWatcher(manager, temp_coverage_file)

    # Create a mock event
    mock_event = mocker.MagicMock()
    mock_event.src_path = str(temp_coverage_file)

    # Spy on _schedule_debounced_update
    spy = mocker.spy(manager, "_schedule_debounced_update")

    # Trigger the event
    watcher.on_modified(mock_event)

    # Verify debounced update was scheduled
    spy.assert_called_once_with(temp_coverage_file)


def test_file_watcher_on_created(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test FileWatcher.on_created triggers debounced update."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    watcher = manager.FileWatcher(manager, temp_coverage_file)

    mock_event = mocker.MagicMock()
    mock_event.src_path = str(temp_coverage_file)

    spy = mocker.spy(manager, "_schedule_debounced_update")

    watcher.on_created(mock_event)

    spy.assert_called_once_with(temp_coverage_file)


def test_file_watcher_on_deleted(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test FileWatcher.on_deleted triggers debounced update."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    watcher = manager.FileWatcher(manager, temp_coverage_file)

    mock_event = mocker.MagicMock()
    mock_event.src_path = str(temp_coverage_file)

    spy = mocker.spy(manager, "_schedule_debounced_update")

    watcher.on_deleted(mock_event)

    spy.assert_called_once_with(temp_coverage_file)


def test_file_watcher_ignores_wrong_file(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test FileWatcher ignores events for different files."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    watcher = manager.FileWatcher(manager, temp_coverage_file)

    # Create event for a different file
    mock_event = mocker.MagicMock()
    mock_event.src_path = str(temp_coverage_file.parent / "other_file.txt")

    spy = mocker.spy(manager, "_schedule_debounced_update")

    # Trigger events
    watcher.on_modified(mock_event)
    watcher.on_created(mock_event)
    watcher.on_deleted(mock_event)

    # Verify debounced update was NOT called
    spy.assert_not_called()


def test_file_watcher_ignores_non_coverage_files(
    temp_coverage_file, mock_coverage_data, mock_file_observer, mocker
):
    """Test FileWatcher ignores non-.coverage files."""
    from python_coverage import CoverageManager

    manager = CoverageManager()
    manager.initialize()
    manager.add_coverage_file(temp_coverage_file)

    watcher = manager.FileWatcher(manager, temp_coverage_file)

    # Create event for a .py file
    mock_event = mocker.MagicMock()
    mock_event.src_path = str(temp_coverage_file.parent / "test.py")

    spy = mocker.spy(manager, "_schedule_debounced_update")

    # Trigger events
    watcher.on_modified(mock_event)
    watcher.on_created(mock_event)
    watcher.on_deleted(mock_event)

    # Verify debounced update was NOT called
    spy.assert_not_called()
