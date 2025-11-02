"""Tests for event listeners."""

from unittest.mock import patch


class TestPythonCoverageDataFileListener:
    """Tests for PythonCoverageDataFileListener."""

    def test_is_applicable(self):
        """Test is_applicable returns True."""
        from python_coverage import PythonCoverageDataFileListener

        assert PythonCoverageDataFileListener.is_applicable({}) is True

    def test_update_available_coverage_files_disabled(
        self, mocker, sublime_window, temp_coverage_file
    ):
        """Test update_available_coverage_files when feature is disabled."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageDataFileListener

        # Initialize manager
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()

        mock_settings = mocker.MagicMock()
        mock_settings.get.return_value = False  # show_missing_lines = False

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageDataFileListener()
            listener.update_available_coverage_files(sublime_window)

            # Should not add any coverage files
            assert len(pc.COVERAGE_MANAGER.coverage_files) == 0

    def test_update_available_coverage_files_enabled(
        self, mocker, sublime_window, tmp_path, mock_file_observer, mock_coverage_data
    ):
        """Test update_available_coverage_files when feature is enabled."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageDataFileListener

        # Create a .coverage file in the temp directory
        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Update window to point to temp directory
        sublime_window._folders = [str(tmp_path)]

        # Initialize coverage manager
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()

        mock_settings = mocker.MagicMock()

        # Configure get() to return appropriate values based on key
        def settings_get(key, default=None):
            if key == "show_missing_lines":
                return True
            if key == "coverage_file_name":
                return ".coverage"
            return default

        mock_settings.get.side_effect = settings_get

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageDataFileListener()
            listener.update_available_coverage_files(sublime_window)

            # Should add the coverage file
            assert len(pc.COVERAGE_MANAGER.coverage_files) == 1
            assert coverage_file in pc.COVERAGE_MANAGER.coverage_files

    def test_on_new_project_async(
        self, mocker, sublime_window, tmp_path, mock_file_observer, mock_coverage_data
    ):
        """Test on_new_project_async calls update_available_coverage_files."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageDataFileListener

        # Create a .coverage file in the temp directory
        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Update window to point to temp directory
        sublime_window._folders = [str(tmp_path)]

        # Initialize coverage manager
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()

        mock_settings = mocker.MagicMock()

        # Configure get() to return appropriate values based on key
        def settings_get(key, default=None):
            if key == "show_missing_lines":
                return True
            if key == "coverage_file_name":
                return ".coverage"
            return default

        mock_settings.get.side_effect = settings_get

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageDataFileListener()
            listener.on_new_project_async(sublime_window)

            # Should add the coverage file
            assert coverage_file in pc.COVERAGE_MANAGER.coverage_files

    def test_on_load_project_async(
        self, mocker, sublime_window, tmp_path, mock_file_observer, mock_coverage_data
    ):
        """Test on_load_project_async calls update_available_coverage_files."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageDataFileListener

        # Create a .coverage file in the temp directory
        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Update window to point to temp directory
        sublime_window._folders = [str(tmp_path)]

        # Initialize coverage manager
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()

        mock_settings = mocker.MagicMock()

        # Configure get() to return appropriate values based on key
        def settings_get(key, default=None):
            if key == "show_missing_lines":
                return True
            if key == "coverage_file_name":
                return ".coverage"
            return default

        mock_settings.get.side_effect = settings_get

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageDataFileListener()
            listener.on_load_project_async(sublime_window)

            # Should add the coverage file
            assert coverage_file in pc.COVERAGE_MANAGER.coverage_files

    def test_on_pre_close_project(
        self, mocker, sublime_window, tmp_path, mock_file_observer, mock_coverage_data
    ):
        """Test on_pre_close_project removes coverage files."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageDataFileListener

        # Create a .coverage file in the temp directory
        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Update window to point to temp directory
        sublime_window._folders = [str(tmp_path)]

        # Initialize coverage manager and add the file
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()
        pc.COVERAGE_MANAGER.add_coverage_file(coverage_file)

        assert coverage_file in pc.COVERAGE_MANAGER.coverage_files

        listener = PythonCoverageDataFileListener()
        listener.on_pre_close_project(sublime_window)

        # Should remove the coverage file
        assert coverage_file not in pc.COVERAGE_MANAGER.coverage_files

    def test_on_activated_async_calls_update(
        self, mocker, sublime_window, tmp_path, mock_file_observer, mock_coverage_data
    ):
        """Test on_activated_async calls update_available_coverage_files."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageDataFileListener

        # Create a .coverage file in the temp directory
        coverage_file = tmp_path / ".coverage"
        coverage_file.touch()

        # Mock the view
        mock_view = mocker.MagicMock()
        mock_view.window.return_value = sublime_window

        # Update window to point to temp directory
        sublime_window._folders = [str(tmp_path)]

        # Initialize coverage manager
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()

        mock_settings = mocker.MagicMock()

        # Configure get() to return appropriate values based on key
        def settings_get(key, default=None):
            if key == "show_missing_lines":
                return True
            if key == "coverage_file_name":
                return ".coverage"
            return default

        mock_settings.get.side_effect = settings_get

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageDataFileListener()
            listener.on_activated_async(mock_view)

            # Should add the coverage file
            assert coverage_file in pc.COVERAGE_MANAGER.coverage_files


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

    def test_update_regions_with_missing_lines(
        self, mocker, sublime_view, temp_coverage_file, mock_coverage_data, mock_file_observer
    ):
        """Test _update_regions when coverage file has missing lines."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageEventListener

        # Initialize manager and add coverage file
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()
        pc.COVERAGE_MANAGER.add_coverage_file(temp_coverage_file)

        # Set up the view with a file in the coverage directory
        test_file = str(temp_coverage_file.parent / "test.py")
        sublime_view._file_name = test_file
        sublime_view._content = "def foo():\n    pass\n"
        sublime_view._size = len(sublime_view._content)

        # Mock measured_files to include our test file
        mock_coverage_data.measured_files.return_value = [test_file]

        # Mock missing_lines to return some missing lines
        cov_file = pc.COVERAGE_MANAGER.coverage_files[temp_coverage_file]
        mocker.patch.object(cov_file, "missing_lines", return_value=[1, 2])

        listener = PythonCoverageEventListener(sublime_view)
        listener._update_regions()

        # Should add regions for missing lines
        assert "python-coverage" in sublime_view._regions
        regions = sublime_view._regions["python-coverage"]["regions"]
        assert len(regions) == 2

        # Cleanup
        pc.COVERAGE_MANAGER.shutdown()
        pc.COVERAGE_MANAGER = None

    def test_update_regions_all_lines_covered(
        self, mocker, sublime_view, temp_coverage_file, mock_coverage_data, mock_file_observer
    ):
        """Test _update_regions when all lines are covered."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageEventListener

        # Initialize manager and add coverage file
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()
        pc.COVERAGE_MANAGER.add_coverage_file(temp_coverage_file)

        # Set up the view
        test_file = str(temp_coverage_file.parent / "test.py")
        sublime_view._file_name = test_file
        sublime_view._content = "def foo():\n    pass\n"
        sublime_view._size = len(sublime_view._content)

        # Mock measured_files
        mock_coverage_data.measured_files.return_value = [test_file]

        # Mock missing_lines to return no missing lines
        cov_file = pc.COVERAGE_MANAGER.coverage_files[temp_coverage_file]
        mocker.patch.object(cov_file, "missing_lines", return_value=[])

        listener = PythonCoverageEventListener(sublime_view)
        listener._update_regions()

        # Should erase regions when no missing lines
        assert "python-coverage" not in sublime_view._regions

        # Cleanup
        pc.COVERAGE_MANAGER.shutdown()
        pc.COVERAGE_MANAGER = None

    def test_update_regions_handles_errors(
        self, mocker, sublime_view, temp_coverage_file, mock_coverage_data, mock_file_observer
    ):
        """Test _update_regions handles errors gracefully."""
        import python_coverage as pc
        from python_coverage import CoverageManager, PythonCoverageEventListener

        # Initialize manager and add coverage file
        pc.COVERAGE_MANAGER = CoverageManager()
        pc.COVERAGE_MANAGER.initialize()
        pc.COVERAGE_MANAGER.add_coverage_file(temp_coverage_file)

        # Set up the view
        test_file = str(temp_coverage_file.parent / "test.py")
        sublime_view._file_name = test_file

        # Mock measured_files
        mock_coverage_data.measured_files.return_value = [test_file]

        # Mock missing_lines to raise an exception
        cov_file = pc.COVERAGE_MANAGER.coverage_files[temp_coverage_file]
        mocker.patch.object(cov_file, "missing_lines", side_effect=Exception("Test error"))

        listener = PythonCoverageEventListener(sublime_view)
        listener._update_regions()

        # Should erase regions on error
        assert "python-coverage" not in sublime_view._regions

        # Cleanup
        pc.COVERAGE_MANAGER.shutdown()
        pc.COVERAGE_MANAGER = None

    def test_on_modified_async_clears_regions(self, mocker, sublime_view):
        """Test on_modified_async clears regions."""
        from python_coverage import PythonCoverageEventListener

        # Add some regions first
        from tests.mocks.sublime import Region

        sublime_view._regions["python-coverage"] = [Region(0, 10)]

        # Mock settings to enable feature
        mock_settings = mocker.MagicMock()
        mock_settings.get.return_value = True

        with patch("sublime.load_settings", return_value=mock_settings):
            listener = PythonCoverageEventListener(sublime_view)
            listener.on_modified_async()

            # Should erase regions on modification
            assert "python-coverage" not in sublime_view._regions

    def test_on_close_removes_from_active_views(self, mocker, sublime_view):
        """Test on_close removes view from active views."""
        import python_coverage as pc
        from python_coverage import PythonCoverageEventListener

        listener = PythonCoverageEventListener(sublime_view)

        # Add to active views
        view_id = sublime_view.id()
        pc.ACTIVE_VIEWS[view_id] = listener

        listener.on_close()

        # Should be removed from active views
        assert view_id not in pc.ACTIVE_VIEWS

        # Cleanup
        pc.ACTIVE_VIEWS = {}
