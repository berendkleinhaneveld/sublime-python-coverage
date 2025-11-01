"""Mock sublime module for testing."""

from typing import Any, Callable, Optional


class RegionFlags:
    """Mock RegionFlags."""

    HIDDEN = 1
    PERSISTENT = 16


class HoverZone:
    """Mock HoverZone."""

    TEXT = 1
    GUTTER = 2
    MARGIN = 3


HIDE_ON_MOUSE_MOVE_AWAY = 1


class Region:
    """Mock Region class."""

    def __init__(self, a: int, b: int = None):
        self.a = a
        self.b = b if b is not None else a

    def contains(self, point: int) -> bool:
        """Check if point is within region."""
        return self.a <= point <= self.b

    def __repr__(self):
        return f"Region({self.a}, {self.b})"


class View:
    """Mock View class."""

    _id_counter = 1

    def __init__(self, file_name: Optional[str] = None):
        self._file_name = file_name
        self._regions = {}
        self._size = 1000
        self._lines = []
        self._id = View._id_counter
        View._id_counter += 1

    def id(self) -> int:
        """Return the unique ID of this view."""
        return self._id

    def file_name(self) -> Optional[str]:
        """Return the file name."""
        return self._file_name

    def size(self) -> int:
        """Return the size of the view."""
        return self._size

    def substr(self, region: Region) -> str:
        """Return the string within the region."""
        return ""

    def lines(self, region: Region) -> list:
        """Return lines within the region."""
        return self._lines

    def add_regions(self, key: str, regions: list, scope: str = "", icon: str = "", flags: int = 0):
        """Add regions to the view."""
        self._regions[key] = {"regions": regions, "scope": scope, "icon": icon, "flags": flags}

    def erase_regions(self, key: str):
        """Erase regions from the view."""
        if key in self._regions:
            del self._regions[key]

    def get_regions(self, key: str) -> list:
        """Get regions by key."""
        if key in self._regions:
            return self._regions[key]["regions"]
        return []

    def show_popup(
        self,
        content: str,
        flags: int = 0,
        location: int = -1,
        max_width: int = 320,
        max_height: int = 240,
        on_navigate: Optional[Callable] = None,
    ):
        """Show a popup."""
        pass

    def window(self):
        """Return the window containing this view."""
        return Window()


class Window:
    """Mock Window class."""

    def __init__(self, folders: Optional[list] = None):
        self._folders = folders or []

    def folders(self) -> list:
        """Return the list of folders in the window."""
        return self._folders


class Settings:
    """Mock Settings class."""

    def __init__(self):
        self._settings = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value."""
        self._settings[key] = value

    def __getitem__(self, key: str) -> Any:
        """Get a setting using bracket notation."""
        return self._settings[key]

    def __setitem__(self, key: str, value: Any):
        """Set a setting using bracket notation."""
        self._settings[key] = value


_settings = {}


def load_settings(base_name: str) -> Settings:
    """Load settings file."""
    if base_name not in _settings:
        _settings[base_name] = Settings()
    return _settings[base_name]


def save_settings(base_name: str):
    """Save settings file."""
    pass
