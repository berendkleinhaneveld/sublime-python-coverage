import logging
import sys
import threading
from pathlib import Path
from typing import Dict, Optional

import sublime
import sublime_plugin

HERE = Path(__file__).parent

# References:
# https://coverage.readthedocs.io/en/stable/api_coveragedata.html#coverage.CoverageData
# https://www.sublimetext.com/docs/api_reference.html#sublime.View
# https://github.com/berendkleinhaneveld/sublime-doorstop/blob/main/doorstop_plugin.py
# https://python-watchdog.readthedocs.io/en/stable/

# Global state - will be managed by CoverageManager singleton
COVERAGE_MANAGER: Optional["CoverageManager"] = None
ACTIVE_VIEWS = {}  # Map view_id -> PythonCoverageEventListener instance

SETTINGS_FILE = "python-coverage.sublime-settings"

# Debounce delay for coverage file updates (in seconds)
# This handles rapid file system events (delete->create->write)
COVERAGE_UPDATE_DEBOUNCE_DELAY = 0.5

# Set up logging
logger = logging.getLogger("sublime-python-coverage")
logger.setLevel(logging.INFO)
# Log to Sublime console
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("Python Coverage [%(levelname)s]: %(message)s"))
logger.addHandler(handler)


class CoverageManager:
    """
    Manages coverage files and file watching.
    Centralizes resource management to prevent leaks.
    Includes debouncing to handle rapid file system events gracefully.
    """

    def __init__(self):
        self.coverage_files: Dict[Path, "CoverageFile"] = {}
        self.file_observer = None
        self.FileWatcher = None
        self._initialized = False
        # Debounce timers for each coverage file
        self._update_timers: Dict[Path, threading.Timer] = {}
        self._timer_lock = threading.Lock()

    def initialize(self, start_observer=True):
        """
        Initialize the file observer and watcher class.

        Args:
            start_observer: Whether to start the file observer immediately.
                          If False, it will be started when coverage files are added.
        """
        if self._initialized:
            logger.warning("CoverageManager already initialized")
            return

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            # Create observer but only start if requested
            self.file_observer = Observer()
            if start_observer:
                self.file_observer.start()
                logger.debug("File observer started")

            class _FileWatcher(FileSystemEventHandler):
                def __init__(self, manager, file):
                    super().__init__()
                    self.manager = manager
                    self.file = file

                def _schedule_update(self, event_type="modified"):
                    """
                    Schedule a debounced update for the coverage file.

                    This handles the common pattern where coverage.py:
                    1. Deletes .coverage file
                    2. Creates new .coverage file
                    3. Writes data to it

                    By debouncing, we wait for the file system events to settle
                    before attempting to reload coverage data.
                    """
                    logger.debug(f"Coverage file {event_type}: {self.file}")
                    self.manager._schedule_debounced_update(self.file)

                def on_modified(self, event):
                    is_coverage = event.src_path.endswith(".coverage")
                    is_our_file = str(event.src_path) == str(self.file)
                    if is_coverage and is_our_file:
                        self._schedule_update("modified")

                def on_created(self, event):
                    is_coverage = event.src_path.endswith(".coverage")
                    is_our_file = str(event.src_path) == str(self.file)
                    if is_coverage and is_our_file:
                        self._schedule_update("created")

                def on_deleted(self, event):
                    is_coverage = event.src_path.endswith(".coverage")
                    is_our_file = str(event.src_path) == str(self.file)
                    if is_coverage and is_our_file:
                        logger.debug(f"Coverage file deleted: {self.file}")
                        # File might be recreated soon, schedule update to check
                        self._schedule_update("deleted")

            self.FileWatcher = _FileWatcher
            self._initialized = True
            logger.info("CoverageManager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize CoverageManager: {e}", exc_info=True)
            raise

    def _schedule_debounced_update(self, coverage_file_path: Path):
        """
        Schedule a debounced update for a coverage file.

        If an update is already scheduled, cancel it and schedule a new one.
        This ensures we only update once after rapid file system events settle.
        """
        with self._timer_lock:
            # Cancel existing timer if any
            if coverage_file_path in self._update_timers:
                self._update_timers[coverage_file_path].cancel()
                logger.debug(f"Cancelled pending update for {coverage_file_path}")

            # Schedule new update
            timer = threading.Timer(
                COVERAGE_UPDATE_DEBOUNCE_DELAY,
                self._perform_debounced_update,
                args=(coverage_file_path,),
            )
            timer.daemon = True
            self._update_timers[coverage_file_path] = timer
            timer.start()
            logger.debug(f"Scheduled debounced update for {coverage_file_path}")

    def _perform_debounced_update(self, coverage_file_path: Path):
        """
        Perform the actual coverage file update after debounce delay.

        Handles cases where file might have been deleted and not recreated,
        or is in the process of being written.
        """
        try:
            with self._timer_lock:
                # Remove timer from tracking
                if coverage_file_path in self._update_timers:
                    del self._update_timers[coverage_file_path]

            # Check if file still exists
            if not coverage_file_path.exists():
                logger.info(f"Coverage file no longer exists, removing: {coverage_file_path}")
                self.remove_coverage_file(coverage_file_path)
                return

            # Check if we're still tracking this file
            if coverage_file_path not in self.coverage_files:
                logger.debug(f"Coverage file no longer tracked: {coverage_file_path}")
                return

            # Update the coverage data
            cov_file = self.coverage_files[coverage_file_path]
            cov_file.update()
            logger.debug(f"Coverage data updated for {coverage_file_path}")

            # Update all active views
            for view_listener in ACTIVE_VIEWS.values():
                try:
                    view_listener._update_regions()
                except Exception as e:
                    logger.error(f"Error updating view regions: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in debounced update for {coverage_file_path}: {e}", exc_info=True)

    def add_coverage_file(self, coverage_file_path: Path) -> bool:
        """
        Add a coverage file to track.

        If this is the first coverage file and observer isn't running, start it.

        Args:
            coverage_file_path: Path to the .coverage file

        Returns:
            True if successfully added, False otherwise
        """
        if coverage_file_path in self.coverage_files:
            logger.debug(f"Coverage file already tracked: {coverage_file_path}")
            return False

        try:
            if not coverage_file_path.exists():
                logger.warning(f"Coverage file does not exist: {coverage_file_path}")
                return False

            # Start observer if this is the first file and observer isn't running
            if not self.coverage_files and self.file_observer and not self.file_observer.is_alive():
                self.file_observer.start()
                logger.info("Started file observer (first coverage file added)")

            cov_file = CoverageFile(self, coverage_file_path)
            self.coverage_files[coverage_file_path] = cov_file
            logger.info(f"Added coverage file: {coverage_file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to add coverage file {coverage_file_path}: {e}", exc_info=True)
            return False

    def remove_coverage_file(self, coverage_file_path: Path) -> bool:
        """
        Remove a coverage file and cleanup its resources.

        If this is the last coverage file, stop the observer to save resources.

        Args:
            coverage_file_path: Path to the .coverage file

        Returns:
            True if successfully removed, False otherwise
        """
        if coverage_file_path not in self.coverage_files:
            logger.debug(f"Coverage file not tracked: {coverage_file_path}")
            return False

        try:
            cov_file = self.coverage_files[coverage_file_path]
            cov_file.cleanup()
            del self.coverage_files[coverage_file_path]
            logger.info(f"Removed coverage file: {coverage_file_path}")

            # Stop observer if no more files being tracked
            if not self.coverage_files and self.file_observer and self.file_observer.is_alive():
                self.file_observer.stop()
                logger.info("Stopped file observer (no coverage files remaining)")

            return True

        except Exception as e:
            logger.error(f"Failed to remove coverage file {coverage_file_path}: {e}", exc_info=True)
            return False

    def get_coverage_file(self, coverage_file_path: Path) -> Optional["CoverageFile"]:
        """Get a coverage file if it exists."""
        return self.coverage_files.get(coverage_file_path)

    def get_coverage_for_file(self, file_path: str) -> Optional["CoverageFile"]:
        """
        Find the appropriate coverage file for a given source file.

        Args:
            file_path: Path to the source file

        Returns:
            CoverageFile if found, None otherwise
        """
        file_path_obj = Path(file_path).resolve()

        for coverage_file_path, cov_file in self.coverage_files.items():
            # Check if the file is within the same directory tree as the coverage file
            try:
                file_path_obj.relative_to(coverage_file_path.parent)
                if cov_file.in_coverage_data(file_path):
                    return cov_file
            except ValueError:
                # Not in the same tree
                continue

        return None

    def cleanup_stale_files(self):
        """Remove coverage files that no longer exist."""
        stale_files = [path for path in self.coverage_files.keys() if not path.exists()]

        for path in stale_files:
            logger.info(f"Cleaning up stale coverage file: {path}")
            self.remove_coverage_file(path)

    def shutdown(self):
        """Shutdown the coverage manager and cleanup all resources."""
        logger.info("Shutting down CoverageManager")

        # Cancel all pending update timers
        with self._timer_lock:
            for coverage_file_path, timer in list(self._update_timers.items()):
                try:
                    timer.cancel()
                    logger.debug(f"Cancelled pending timer for {coverage_file_path}")
                except Exception as e:
                    logger.error(f"Error cancelling timer: {e}")
            self._update_timers.clear()

        # Remove all coverage files (which will cleanup watchers)
        for coverage_file_path in list(self.coverage_files.keys()):
            self.remove_coverage_file(coverage_file_path)

        # Stop the file observer
        if self.file_observer:
            try:
                self.file_observer.stop()
                self.file_observer.join(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping file observer: {e}", exc_info=True)
            finally:
                self.file_observer = None

        self._initialized = False
        logger.info("CoverageManager shutdown complete")


def plugin_loaded():
    """
    Hook that is called by Sublime when plugin is loaded.
    """
    global COVERAGE_MANAGER

    try:
        # Load platform-specific wheels
        packaging_wheel = HERE / "libs" / "packaging-23.1-py3-none-any.whl"
        if not packaging_wheel.exists():
            sublime.error_message(
                "Python Coverage: Missing packaging library.\nPlease reinstall the plugin."
            )
            return

        if str(packaging_wheel) not in sys.path:
            sys.path.append(str(packaging_wheel))

        from packaging.tags import sys_tags

        tags = [str(tag) for tag in sys_tags()]

        for prefix in {"coverage*", "watchdog*"}:
            # Figure out the right whl for the platform
            wheel_found = False
            for wheel in (HERE / "libs").glob(prefix):
                wheel_tag = "-".join(wheel.stem.split("-")[2:])
                if wheel_tag in tags:
                    wheel_found = True
                    break

            if not wheel_found:
                lib_name = prefix.replace("*", "")
                sublime.error_message(
                    f"Python Coverage: Could not find compatible {lib_name} "
                    f"library for your platform.\n\n"
                    f"Platform tags: {tags[:3]}...\n"
                    f"Please report this issue on GitHub."
                )
                return

            if str(wheel) not in sys.path:
                sys.path.append(str(wheel))

        # Initialize the coverage manager
        COVERAGE_MANAGER = CoverageManager()
        COVERAGE_MANAGER.initialize()

        logger.info("Python Coverage plugin loaded successfully")

    except Exception as e:
        sublime.error_message(
            f"Python Coverage: Failed to load plugin.\n\n"
            f"Error: {e}\n\n"
            f"Please report this issue on GitHub."
        )
        logger.error(f"Plugin load error: {e}", exc_info=True)


def plugin_unloaded():
    """
    Hook that is called by Sublime when plugin is unloaded.
    """
    global COVERAGE_MANAGER

    # Clear active views
    ACTIVE_VIEWS.clear()

    # Shutdown coverage manager
    if COVERAGE_MANAGER:
        COVERAGE_MANAGER.shutdown()
        COVERAGE_MANAGER = None

    logger.info("Python Coverage plugin unloaded")


class CoverageFile:
    """
    Represents a .coverage file and manages its data and file watcher.

    Uses lazy loading and caching to handle rapid file updates gracefully.
    """

    def __init__(self, manager: CoverageManager, coverage_file: Path):
        """
        Initialize a coverage file.

        Args:
            manager: The CoverageManager instance
            coverage_file: Path to the .coverage file
        """
        import coverage

        self.manager = manager
        self.coverage_file = coverage_file
        self.data = None
        self.handler = None
        self.watcher = None

        # Cache for parsed Python statements: {file_path: (mtime, statements)}
        self._statement_cache: Dict[str, tuple] = {}

        try:
            # Lazy load coverage data - load on first use
            # This is safer when file might be in process of being created
            self.data = coverage.Coverage(data_file=str(coverage_file)).get_data()
            self._load_data_with_retry()

            # Set up file watcher
            if manager.FileWatcher and manager.file_observer:
                self.handler = manager.FileWatcher(manager, coverage_file)
                self.watcher = manager.file_observer.schedule(
                    self.handler, str(coverage_file.parent), recursive=False
                )
                logger.debug(f"File watcher scheduled for {coverage_file}")

        except Exception as e:
            logger.error(f"Error initializing CoverageFile for {coverage_file}: {e}")
            raise

    def _load_data_with_retry(self, max_retries=3):
        """
        Load coverage data with retry logic.

        Coverage files might be in the process of being written,
        so we retry a few times with a small delay.
        """
        import time

        for attempt in range(max_retries):
            try:
                if not self.coverage_file.exists():
                    if attempt < max_retries - 1:
                        logger.debug(f"Coverage file not ready, retry {attempt + 1}/{max_retries}")
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.warning(
                            f"Coverage file does not exist after retries: {self.coverage_file}"
                        )
                        return False

                self.data.read()
                logger.debug(f"Successfully loaded coverage data for {self.coverage_file}")
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Error loading coverage data (attempt {attempt + 1}): {e}")
                    time.sleep(0.1 * (attempt + 1))
                else:
                    logger.error(f"Failed to load coverage data after {max_retries} attempts: {e}")
                    raise

        return False

    def update(self):
        """
        Re-read coverage data from disk.

        Uses retry logic to handle cases where file is being rewritten.
        Invalidates statement cache since coverage data changed.
        """
        try:
            if self.data:
                success = self._load_data_with_retry()
                if success:
                    # Invalidate statement cache when coverage data changes
                    self._statement_cache.clear()
                    logger.debug(f"Updated coverage data for {self.coverage_file}")
        except Exception as e:
            logger.error(f"Error updating coverage data: {e}", exc_info=True)

    def in_coverage_data(self, file: str) -> bool:
        """
        Check if a file is in the coverage data.

        Args:
            file: Path to the source file

        Returns:
            True if file is in coverage data, False otherwise
        """
        try:
            if not self.data:
                return False
            return str(file) in self.data.measured_files()
        except Exception as e:
            logger.error(f"Error checking coverage data: {e}", exc_info=True)
            return False

    def missing_lines(self, file: str, text: str):
        """
        Calculate missing lines for a given file.

        Uses cached parsed statements when file hasn't changed to avoid
        reparsing on every view activation.

        Args:
            file: Path to the source file
            text: Source code text

        Returns:
            List of missing line numbers (descending order), or None if error
        """
        import hashlib

        from coverage.exceptions import DataError
        from coverage.parser import PythonParser

        try:
            if not self.data:
                return None

            lines = self.data.lines(file)
        except DataError as e:
            logger.debug(f"DataError for {file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting lines for {file}: {e}", exc_info=True)
            return None

        if lines is None:
            return None

        try:
            # Check cache for parsed statements
            # Use hash of text content as cache key since we get text from view
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cache_key = f"{file}:{text_hash}"

            if cache_key in self._statement_cache:
                statements = self._statement_cache[cache_key]
                logger.debug(f"Using cached statements for {file}")
            else:
                # Parse the file to find all executable statements
                python_parser = PythonParser(text=text)
                python_parser.parse_source()
                statements = python_parser.statements

                # Cache the parsed statements
                self._statement_cache[cache_key] = statements
                logger.debug(f"Cached statements for {file}")

            # Calculate missing lines (statements not executed)
            missing = sorted(list(statements - set(lines)), reverse=True)
            return missing

        except Exception as e:
            logger.error(f"Error parsing file {file}: {e}", exc_info=True)
            return None

    def cleanup(self):
        """Cleanup resources associated with this coverage file."""
        try:
            # Unschedule the file watcher
            if self.watcher and self.manager.file_observer:
                self.manager.file_observer.unschedule(self.watcher)
                logger.debug(f"Unscheduled watcher for {self.coverage_file}")
                self.watcher = None

            self.handler = None
            self.data = None
            self._statement_cache.clear()

        except Exception as e:
            logger.error(f"Error cleaning up CoverageFile: {e}", exc_info=True)


class ToggleMissingLinesCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        settings = sublime.load_settings(SETTINGS_FILE)
        settings["show_missing_lines"] = not settings["show_missing_lines"]
        sublime.save_settings(SETTINGS_FILE)
        print(
            "Python Coverage: "
            f"{'Enabled' if settings['show_missing_lines'] else 'Disabled'}"
            " show missing lines"
        )


class PythonCoverageDataFileListener(sublime_plugin.EventListener):
    @classmethod
    def is_applicable(cls, _settings):
        """
        Returns:
            Whether this listener should apply to a view with the given Settings.
        """
        return True

    def on_new_project_async(self, window):
        """
        Called right after a new project is created, passed the Window object.
        Runs in a separate thread, and does not block the application.
        """
        self.update_available_coverage_files(window)

    def on_load_project_async(self, window):
        """
        Called right after a project is loaded, passed the Window object.
        Runs in a separate thread, and does not block the application.
        """
        self.update_available_coverage_files(window)

    def on_post_save_project_async(self, window):
        """
        Called right after a project is saved, passed the Window object.
        Runs in a separate thread, and does not block the application.
        """
        self.update_available_coverage_files(window)

    def on_pre_close_project(self, window):
        """
        Called right before a project is closed, passed the Window object.
        Cleanup coverage files for closing project.
        """
        if not COVERAGE_MANAGER:
            return

        # Remove coverage files for folders in this project
        for folder in window.folders():
            folder = Path(folder)
            coverage_file = folder / ".coverage"
            if coverage_file in COVERAGE_MANAGER.coverage_files:
                COVERAGE_MANAGER.remove_coverage_file(coverage_file)

        # Cleanup stale files
        COVERAGE_MANAGER.cleanup_stale_files()

    def on_activated_async(self, view):
        self.update_available_coverage_files(view.window())

    def update_available_coverage_files(self, window):
        """Scan for and add coverage files in project folders."""
        if not COVERAGE_MANAGER:
            return

        settings = sublime.load_settings(SETTINGS_FILE)
        if not settings.get("show_missing_lines", False):
            return

        try:
            for folder in window.folders():
                folder = Path(folder)
                coverage_file = folder / ".coverage"

                # Add coverage file if it exists and not already tracked
                if coverage_file.is_file():
                    COVERAGE_MANAGER.add_coverage_file(coverage_file)

        except Exception as e:
            logger.error(f"Error updating coverage files: {e}", exc_info=True)


class PythonCoverageEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        """
        Returns:
            Whether this listener should apply to a view with the given Settings.
        """
        return "Python" in settings.get("syntax", "")

    def on_modified_async(self):
        """
        Called after changes have been made to the view.
        Runs in a separate thread, and does not block the application.
        """
        try:
            # Clear coverage markers when file is modified
            # They may no longer be accurate since the code has changed
            settings = sublime.load_settings(SETTINGS_FILE)
            if settings.get("show_missing_lines", False):
                self.view.erase_regions(key="python-coverage")
        except Exception as e:
            logger.error(f"Error in on_modified_async: {e}", exc_info=True)

    def on_activated_async(self):
        """
        Called when a view gains input focus. Runs in a separate thread,
        and does not block the application.
        """
        try:
            settings = sublime.load_settings(SETTINGS_FILE)
            if not settings.get("show_missing_lines", False):
                self.view.erase_regions(key="python-coverage")
                # Remove from active views if present
                view_id = self.view.id()
                ACTIVE_VIEWS.pop(view_id, None)
                return

            # Add this view to active views
            view_id = self.view.id()
            ACTIVE_VIEWS[view_id] = self

            self._update_regions()

        except Exception as e:
            logger.error(f"Error in on_activated_async: {e}", exc_info=True)

    def on_close(self):
        """
        Called when a view is closed. Runs in the main thread.
        """
        # Remove from active views when closed
        view_id = self.view.id()
        ACTIVE_VIEWS.pop(view_id, None)

    def _update_regions(self):
        """Update coverage regions for this view."""
        file_name = self.view.file_name()
        if not file_name:
            return

        if not COVERAGE_MANAGER:
            self.view.erase_regions(key="python-coverage")
            return

        try:
            # Use the manager's improved path matching
            cov = COVERAGE_MANAGER.get_coverage_for_file(file_name)
            if not cov:
                self.view.erase_regions(key="python-coverage")
                return

            # Get file content
            full_file_region = sublime.Region(0, self.view.size())
            text = self.view.substr(full_file_region)

            # Calculate missing lines
            missing = cov.missing_lines(file_name, text)
            if not missing:
                self.view.erase_regions(key="python-coverage")
                return

            # Convert line numbers to regions
            all_lines_regions = self.view.lines(full_file_region)
            missing_regions = [all_lines_regions[line - 1] for line in missing]

            # Add visual indicators
            self.view.add_regions(
                key="python-coverage",
                regions=missing_regions,
                scope="region.orangish",
                icon="Packages/sublime-python-coverage/images/triangle.png",
                flags=sublime.RegionFlags.HIDDEN,
            )
            logger.debug(f"Updated regions for {file_name}: {len(missing)} missing lines")

        except Exception as e:
            logger.error(f"Error updating regions for {file_name}: {e}", exc_info=True)
            self.view.erase_regions(key="python-coverage")

    def on_hover(self, point, hover_zone):
        """
        Called when the user's mouse hovers over a view for a short period.
        """
        if hover_zone != sublime.HoverZone.GUTTER:
            return

        regions = self.view.get_regions("python-coverage")
        if not regions:
            return

        for region in regions:
            if region.contains(point):
                break
        else:
            return

        self.view.show_popup(
            "Coverage: uncovered line",
            sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            point,
            500,
            500,
            None,
        )
