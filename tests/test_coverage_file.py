"""Tests for CoverageFile class."""


def test_coverage_file_initialization(temp_coverage_file, mock_coverage_data, mock_file_observer):
    """Test CoverageFile initializes correctly."""
    from python_coverage import CoverageFile, CoverageManager

    # Create a manager
    manager = CoverageManager()
    manager.initialize()

    # Create a coverage file
    cov_file = CoverageFile(manager, temp_coverage_file)

    assert cov_file.coverage_file == temp_coverage_file
    assert cov_file.data is not None
    assert cov_file.manager is manager


def test_coverage_file_update(temp_coverage_file, mock_coverage_data, mock_file_observer):
    """Test CoverageFile.update() re-reads data."""
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)
    initial_read_count = mock_coverage_data.read.call_count

    cov_file.update()

    assert mock_coverage_data.read.call_count > initial_read_count


def test_coverage_file_in_coverage_data(temp_coverage_file, mock_coverage_data, mock_file_observer):
    """Test CoverageFile.in_coverage_data() checks file presence."""
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)

    assert cov_file.in_coverage_data("/path/to/file.py") is True
    assert cov_file.in_coverage_data("/other/file.py") is False


def test_coverage_file_missing_lines_success(
    temp_coverage_file,
    mock_coverage_data,
    mock_python_parser,
    mock_file_observer,
    sample_python_code,
):
    """Test CoverageFile.missing_lines() calculates missing lines correctly."""
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)

    # mock_coverage_data.lines returns [1, 2, 3, 5]
    # mock_python_parser.statements is {1, 2, 3, 4, 5}
    # Missing line should be [4]
    missing = cov_file.missing_lines("/path/to/file.py", sample_python_code)

    assert missing == [4]


def test_coverage_file_missing_lines_data_error(
    temp_coverage_file, mock_coverage_data, mock_file_observer
):
    """Test CoverageFile.missing_lines() handles DataError."""
    from coverage.exceptions import DataError
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)

    # Make lines() raise DataError
    mock_coverage_data.lines.side_effect = DataError("Test error")

    missing = cov_file.missing_lines("/path/to/file.py", "code")

    assert missing is None


def test_coverage_file_missing_lines_no_data(
    temp_coverage_file, mock_coverage_data, mock_file_observer
):
    """Test CoverageFile.missing_lines() handles no coverage data."""
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)

    # Make lines() return None
    mock_coverage_data.lines.return_value = None

    missing = cov_file.missing_lines("/path/to/file.py", "code")

    assert missing is None


def test_coverage_file_missing_lines_all_covered(
    temp_coverage_file,
    mock_coverage_data,
    mock_python_parser,
    mock_file_observer,
    sample_python_code,
):
    """Test CoverageFile.missing_lines() when all lines are covered."""
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)

    # All lines covered
    mock_coverage_data.lines.return_value = [1, 2, 3, 4, 5]
    mock_python_parser.statements = {1, 2, 3, 4, 5}

    missing = cov_file.missing_lines("/path/to/file.py", sample_python_code)

    assert missing == []


def test_coverage_file_missing_lines_sorted_descending(
    temp_coverage_file,
    mock_coverage_data,
    mock_python_parser,
    mock_file_observer,
    sample_python_code,
):
    """Test CoverageFile.missing_lines() returns lines in descending order."""
    from python_coverage import CoverageFile, CoverageManager

    manager = CoverageManager()
    manager.initialize()

    cov_file = CoverageFile(manager, temp_coverage_file)

    # Multiple missing lines: 2, 4, 7
    mock_coverage_data.lines.return_value = [1, 3, 5, 6, 8]
    mock_python_parser.statements = {1, 2, 3, 4, 5, 6, 7, 8}

    missing = cov_file.missing_lines("/path/to/file.py", sample_python_code)

    assert missing == [7, 4, 2]  # Descending order
