# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-01-15

### Added
- Details mode now preserves the selected field position when navigating between entries
- Fullscreen field view with scrolling support

### Fixed
- Details mode now preserves the current line when new log entries arrive

## [0.3.0] - 2026-01-01

### Added
- Support for piping data into juffi (e.g., `cat file.log | juffi`)
- Python 3.10 compatibility

### Changed
- Default sort order is now ascending for non-JSON files to preserve multi-line log order

### Fixed
- Go to line functionality now correctly navigates to row positions in filtered view instead of original file line numbers
- Follow mode now correctly displays new log entries as they are added to the file
- Reset functionality (Ctrl+R) now properly reloads the file and resets all state
- Window resize handling improved to prevent display glitches
- Improved input responsiveness for smoother navigation

### Documentation
- Enhanced README with detailed information and screenshots
- Updated build instructions

## [0.2.0] - 2025-10-23

### Added
- Initial public release of Juffi
- Terminal User Interface (TUI) for viewing JSON log files
- Automatic column detection from JSON fields
- Sortable columns functionality
- Column reordering
- Horizontal scrolling for wide tables
- Filtering by any column
- Search across all fields
- Real-time log following (tail -f mode)
- Help screen with keyboard shortcuts
- Support for Python 3.11+
- No external dependencies required

[0.4.0]: https://github.com/YotamAlon/juffi/releases/tag/v0.4.0
[0.3.0]: https://github.com/YotamAlon/juffi/releases/tag/v0.3.0
[0.2.0]: https://github.com/YotamAlon/juffi/releases/tag/v0.2.0
