"""Mock sublime_plugin module for testing."""


class ApplicationCommand:
    """Mock ApplicationCommand class."""

    def run(self):
        """Run the command."""
        pass


class EventListener:
    """Mock EventListener class."""

    @classmethod
    def is_applicable(cls, settings):
        """Check if listener is applicable."""
        return True


class ViewEventListener:
    """Mock ViewEventListener class."""

    def __init__(self, view):
        self.view = view

    @classmethod
    def is_applicable(cls, settings):
        """Check if listener is applicable."""
        return True
