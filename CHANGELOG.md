# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
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

[Unreleased]: https://github.com/YotamAlon/juffi/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/YotamAlon/juffi/releases/tag/v0.2.0
