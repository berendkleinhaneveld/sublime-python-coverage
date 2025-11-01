"""Pytest configuration and fixtures."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add mocks to sys.modules before importing the plugin
TEST_DIR = Path(__file__).parent
MOCK_DIR = TEST_DIR / "mocks"

sys.path.insert(0, str(MOCK_DIR))

# Mock sublime and sublime_plugin modules
from tests.mocks import sublime, sublime_plugin  # noqa: E402

sys.modules["sublime"] = sublime
sys.modules["sublime_plugin"] = sublime_plugin

# Load the main plugin module (python-coverage.py) and add it to sys.modules
PLUGIN_PATH = TEST_DIR.parent / "python-coverage.py"
spec = importlib.util.spec_from_file_location("python_coverage", PLUGIN_PATH)
python_coverage = importlib.util.module_from_spec(spec)
sys.modules["python_coverage"] = python_coverage

# Try to execute the module (may fail due to missing deps, that's ok)
try:
    spec.loader.exec_module(python_coverage)
except Exception as e:
    # Some imports may fail in test environment, that's expected
    print(f"Note: Plugin module partially loaded (expected): {e}")


@pytest.fixture
def temp_coverage_file(tmp_path):
    """Create a temporary coverage file."""
    coverage_file = tmp_path / ".coverage"
    coverage_file.touch()
    return coverage_file


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """def hello(name):
    if name:
        print(f"Hello, {name}!")
    else:
        print("Hello, World!")
    return True
"""


@pytest.fixture
def mock_coverage_data(mocker):
    """Mock coverage.Coverage and CoverageData."""
    mock_data = mocker.MagicMock()
    mock_data.measured_files.return_value = ["/path/to/file.py"]
    mock_data.lines.return_value = [1, 2, 3, 5]  # Line 4 is missing
    mock_data.read.return_value = None

    mock_coverage = mocker.MagicMock()
    mock_coverage.get_data.return_value = mock_data

    mock_coverage_class = mocker.patch("coverage.Coverage")
    mock_coverage_class.return_value = mock_coverage

    return mock_data


@pytest.fixture
def mock_python_parser(mocker):
    """Mock coverage.parser.PythonParser."""
    mock_parser = mocker.MagicMock()
    mock_parser.statements = {1, 2, 3, 4, 5}  # All executable lines

    mock_parser_class = mocker.patch("coverage.parser.PythonParser")
    mock_parser_class.return_value = mock_parser

    return mock_parser


@pytest.fixture
def mock_file_observer(mocker):
    """Mock watchdog Observer."""
    mock_observer = mocker.MagicMock()
    mock_observer_class = mocker.patch("watchdog.observers.Observer")
    mock_observer_class.return_value = mock_observer
    return mock_observer


@pytest.fixture
def sublime_view():
    """Create a mock Sublime View."""
    return sublime.View(file_name="/path/to/file.py")


@pytest.fixture
def sublime_window(tmp_path):
    """Create a mock Sublime Window."""
    return sublime.Window(folders=[str(tmp_path)])


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state before each test."""
    import python_coverage as pc

    # Clear global state if attributes exist
    if hasattr(pc, "ACTIVE_VIEWS") and pc.ACTIVE_VIEWS:
        pc.ACTIVE_VIEWS.clear()

    # Reset coverage manager if it exists
    if hasattr(pc, "COVERAGE_MANAGER") and pc.COVERAGE_MANAGER:
        # Shutdown existing manager
        try:
            pc.COVERAGE_MANAGER.shutdown()
        except Exception:
            pass
        pc.COVERAGE_MANAGER = None

    yield

    # Cleanup after test
    if hasattr(pc, "ACTIVE_VIEWS") and pc.ACTIVE_VIEWS:
        pc.ACTIVE_VIEWS.clear()

    if hasattr(pc, "COVERAGE_MANAGER") and pc.COVERAGE_MANAGER:
        try:
            pc.COVERAGE_MANAGER.shutdown()
        except Exception:
            pass
        pc.COVERAGE_MANAGER = None
