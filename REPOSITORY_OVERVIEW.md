# Sublime Python Coverage - Repository Overview

## Project Summary

**Sublime Python Coverage** is a Sublime Text plugin that visually highlights missing lines of Python code coverage directly in the editor. It provides real-time feedback to developers about which lines of their Python code are not covered by tests, using data from Python's coverage.py tool.

**Author**: Berend Klein Haneveld (berendkleinhaneveld@gmail.com)
**License**: MIT License (2023)
**Version**: 0.1.0

## Purpose

This plugin helps developers improve their test coverage by:
- Displaying uncovered lines directly in the editor with visual indicators
- Automatically updating when coverage data changes
- Providing an unobtrusive way to track testing progress
- Supporting multiple Python projects simultaneously

## Repository Structure

```
sublime-python-coverage/
├── python-coverage.py                    # Main plugin code
├── python-coverage.sublime-settings      # Plugin settings
├── python-coverage.sublime-commands      # Command palette entries
├── pyproject.toml                        # Poetry configuration
├── poetry.lock                           # Poetry lock file
├── README.md                             # Project documentation
├── LICENSE                               # MIT license
├── line.png                              # Legacy icon (not used)
├── images/                               # Icon resources
│   ├── line.png
│   ├── diamond.png
│   └── triangle.png                      # Current gutter icon
└── libs/                                 # Bundled dependencies (wheels)
    ├── coverage-7.2.3-*.whl              # Coverage.py for various platforms
    ├── watchdog-3.0.0-*.whl              # File system monitoring
    └── packaging-23.1-py3-none-any.whl   # Package version handling
```

## Key Components

### Main Plugin File (`python-coverage.py`)

The plugin consists of several key components:

#### 1. **Plugin Lifecycle Management**
- `plugin_loaded()` (lines 24-82): Initializes the plugin by:
  - Loading platform-specific wheels for `coverage` and `watchdog` libraries
  - Starting a file system observer to watch for `.coverage` file changes
  - Dynamically detecting the correct wheel based on Python tags

- `plugin_unloaded()` (lines 85-95): Cleans up resources when plugin is disabled

#### 2. **CoverageFile Class** (lines 98-131)
Manages individual coverage data files:
- Reads and parses `.coverage` files using coverage.py API
- Watches for changes to coverage files and triggers updates
- Calculates missing lines by comparing executed lines with code statements
- Uses `PythonParser` to identify all executable statements

#### 3. **ToggleMissingLinesCommand** (lines 134-143)
Application command that enables/disables coverage visualization:
- Toggles the `show_missing_lines` setting
- Accessible via Command Palette: "Python Coverage: Toggle Missing Lines"

#### 4. **PythonCoverageDataFileListener** (lines 146-193)
Event listener for project-level events:
- Monitors project loading, saving, and closing
- Automatically discovers `.coverage` files in project folders
- Registers coverage files for tracking when projects are opened

#### 5. **PythonCoverageEventListener** (lines 196-290)
View-specific event listener for Python files:
- Only applies to views with Python syntax
- Updates coverage visualization when views are activated
- Shows orange triangle icons in the gutter for uncovered lines
- Displays tooltip on hover: "Coverage: uncovered line"
- Key method: `_update_regions()` (lines 228-264) handles the visual display

### Configuration Files

#### `python-coverage.sublime-settings`
Default settings:
- `show_missing_lines`: false (coverage display is off by default)

#### `python-coverage.sublime-commands`
Provides two command palette entries:
1. "Preferences: Python Coverage" - Opens settings editor
2. "Python Coverage: Toggle Missing Lines" - Toggles coverage display

### Visual Assets

The plugin uses a small triangle icon (`images/triangle.png`) displayed in the gutter to mark uncovered lines. The regions are highlighted with an "orangish" color scope.

## Technical Implementation Details

### Dependency Management
- Uses pre-built wheel files for cross-platform compatibility
- Supports multiple platforms: macOS (x86_64, ARM64), Linux (various), Windows
- Dynamically selects the correct wheel based on Python implementation tags
- Bundled dependencies:
  - `coverage` 7.2.3: For reading coverage data
  - `watchdog` 3.0.0: For file system monitoring
  - `packaging` 23.1: For platform detection

### File Watching
- Uses `watchdog` library to monitor `.coverage` files
- Automatically refreshes coverage display when coverage data is updated
- Each coverage file has its own watcher instance

### Coverage Calculation
The plugin calculates missing lines by:
1. Reading executed lines from `.coverage` file
2. Parsing the current file to identify all executable statements
3. Computing the difference: `statements - executed_lines`
4. Displaying the missing lines in the gutter

### Performance Considerations
- Event listeners run asynchronously (`*_async` methods) to avoid blocking UI
- Coverage data is only loaded for active projects
- Regions are updated only when views are activated
- TODO noted in code: Consider caching parsed statements

## Development Setup

### Dependencies (Dev)
- Python ^3.8
- black: Code formatting
- pre-commit: Git hooks
- ruff: Linting with rules for E, F, I, B, N, A, PTH

### Development Workflow
1. Poetry is used for dependency management
2. Pre-commit hooks ensure code quality
3. Ruff checks for code style issues

## Usage Flow

1. User opens a Python project in Sublime Text
2. Plugin detects `.coverage` file in project folders
3. User runs "Python Coverage: Toggle Missing Lines" command
4. Plugin reads coverage data and identifies uncovered lines
5. Orange triangles appear in gutter next to uncovered lines
6. When `.coverage` file is updated (e.g., after running tests), display auto-updates
7. Hovering over indicators shows "Coverage: uncovered line" tooltip

## Key Features

- **Automatic Discovery**: Finds `.coverage` files in project folders
- **Real-time Updates**: Watches for coverage file changes
- **Non-intrusive**: Uses gutter icons and subtle highlighting
- **Multi-project Support**: Can track coverage for multiple projects simultaneously
- **On-demand**: Can be toggled on/off via command palette
- **Platform Support**: Works on macOS, Linux, and Windows

## Future Improvements (TODOs in Code)

1. Line 51: Only start file watching when plugin is actively showing missing lines
2. Line 126: Consider caching parsed statements and invalidating via file watcher
3. Line 210: Clear modified regions when file is edited

## References

The code includes references to:
- Coverage.py API documentation
- Sublime Text API reference
- Related project: sublime-doorstop
- Watchdog documentation

## Architecture Highlights

- **Event-driven**: Uses Sublime Text's event system for efficiency
- **Lazy loading**: Coverage data loaded only when needed
- **Modular**: Clear separation between coverage data handling and UI updates
- **Cross-platform**: Handles platform differences transparently via wheel selection
- **Pythonic**: Follows Python best practices and style guidelines
