import sys
from pathlib import Path

import sublime
import sublime_plugin

HERE = Path(__file__).parent

# References:
# https://coverage.readthedocs.io/en/stable/api_coveragedata.html#coverage.CoverageData
# https://www.sublimetext.com/docs/api_reference.html#sublime.View
# https://github.com/berendkleinhaneveld/sublime-doorstop/blob/main/doorstop_plugin.py
# https://python-watchdog.readthedocs.io/en/stable/

COVERAGE_FILES = {}
FILE_OBSERVER = None

FileWatcher = None
ACTIVE_VIEWS = {}  # Map view_id -> PythonCoverageEventListener instance

SETTINGS_FILE = "python-coverage.sublime-settings"


def plugin_loaded():
    """
    Hook that is called by Sublime when plugin is loaded.
    """
    try:
        packaging_wheel = HERE / "libs" / "packaging-23.1-py3-none-any.whl"
        if not packaging_wheel.exists():
            sublime.error_message(
                "Python Coverage: Missing packaging library.\n"
                "Please reinstall the plugin."
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

        from watchdog.observers import Observer

        # TODO: only start watching when plugin is showing missing lines
        global FILE_OBSERVER
        FILE_OBSERVER = Observer()
        FILE_OBSERVER.start()

        from watchdog.events import FileSystemEventHandler

        class _FileWatcher(FileSystemEventHandler):
            def __init__(self, file):
                super().__init__()
                self.file = file

            def _update(self, event):
                if not event.src_path.endswith(".coverage"):
                    return

                if str(event.src_path) != str(self.file):
                    return

                try:
                    COVERAGE_FILES[self.file].update()

                    # Update all active views
                    for view_listener in ACTIVE_VIEWS.values():
                        view_listener._update_regions()
                except Exception as e:
                    print(f"Python Coverage: Error updating coverage data: {e}")

            def on_modified(self, event):
                self._update(event)

            def on_created(self, event):
                self._update(event)

        global FileWatcher
        FileWatcher = _FileWatcher

    except Exception as e:
        sublime.error_message(
            f"Python Coverage: Failed to load plugin.\n\n"
            f"Error: {e}\n\n"
            f"Please report this issue on GitHub."
        )
        print(f"Python Coverage: Plugin load error: {e}")
        import traceback
        traceback.print_exc()


def plugin_unloaded():
    """
    Hook that is called by Sublime when plugin is unloaded.
    """
    COVERAGE_FILES.clear()
    ACTIVE_VIEWS.clear()
    global FILE_OBSERVER
    if FILE_OBSERVER:
        FILE_OBSERVER.stop()
        FILE_OBSERVER.join()
        FILE_OBSERVER = None


class CoverageFile:
    def __init__(self, coverage_file):
        import coverage

        self.coverage_file = coverage_file
        self.data = coverage.Coverage(data_file=coverage_file).get_data()
        self.data.read()

        self.handler = FileWatcher(coverage_file)
        self.watcher = FILE_OBSERVER.schedule(self.handler, str(coverage_file.parent))

    def update(self):
        self.data.read()

    def in_coverage_data(self, file):
        return str(file) in self.data.measured_files()

    def missing_lines(self, file, text):
        from coverage.exceptions import DataError
        from coverage.parser import PythonParser

        try:
            lines = self.data.lines(file)
        except DataError:
            return None
        if lines is None:
            return None

        # TODO: Maybe this could be cached? And use file watcher to invalidate?
        python_parser = PythonParser(text=text)
        python_parser.parse_source()
        statements = python_parser.statements

        return sorted(list(statements - set(lines)), reverse=True)


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
    def is_applicable(cls, settings):
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
        """
        self.update_available_coverage_files(window)

    def on_activated_async(self, view):
        self.update_available_coverage_files(view.window())

    def update_available_coverage_files(self, window):
        settings = sublime.load_settings(SETTINGS_FILE)
        if not settings["show_missing_lines"]:
            return
        for folder in window.folders():
            folder = Path(folder)
            coverage_file = folder / ".coverage"
            if coverage_file.is_file() and coverage_file not in COVERAGE_FILES:
                COVERAGE_FILES[coverage_file] = CoverageFile(coverage_file)


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
        # Clear coverage markers when file is modified
        # They may no longer be accurate since the code has changed
        settings = sublime.load_settings(SETTINGS_FILE)
        if settings["show_missing_lines"]:
            self.view.erase_regions(key="python-coverage")

    def on_activated_async(self):
        """
        Called when a view gains input focus. Runs in a separate thread,
        and does not block the application.
        """
        settings = sublime.load_settings(SETTINGS_FILE)
        if not settings["show_missing_lines"]:
            self.view.erase_regions(key="python-coverage")
            # Remove from active views if present
            view_id = self.view.id()
            if view_id in ACTIVE_VIEWS:
                del ACTIVE_VIEWS[view_id]
            return

        # Add this view to active views
        view_id = self.view.id()
        ACTIVE_VIEWS[view_id] = self

        self._update_regions()

    def on_close(self):
        """
        Called when a view is closed. Runs in the main thread.
        """
        # Remove from active views when closed
        view_id = self.view.id()
        if view_id in ACTIVE_VIEWS:
            del ACTIVE_VIEWS[view_id]

    def _update_regions(self):
        file_name = self.view.file_name()
        if not file_name:
            return

        for coverage_file in COVERAGE_FILES:
            # Assume that the file is somewhere within the
            # same (sub)folder as the coverage file
            if str(coverage_file.parent) in file_name:
                break
        else:
            self.view.erase_regions(key="python-coverage")
            return

        cov = COVERAGE_FILES[coverage_file]
        if not cov.in_coverage_data(file_name):
            self.view.erase_regions(key="python-coverage")
            return

        full_file_region = sublime.Region(0, self.view.size())
        text = self.view.substr(full_file_region)

        missing = cov.missing_lines(file_name, text)
        if not missing:
            self.view.erase_regions(key="python-coverage")
            return

        all_lines_regions = self.view.lines(full_file_region)
        missing_regions = [all_lines_regions[line - 1] for line in missing]

        self.view.add_regions(
            key="python-coverage",
            regions=missing_regions,
            scope="region.orangish",
            icon="Packages/sublime-python-coverage/images/triangle.png",
            flags=sublime.RegionFlags.HIDDEN,
        )

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
