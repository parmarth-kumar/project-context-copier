# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0-beta] - 2026-07-20

### Added

- Header-integrated Recent Projects dropdown with hover tooltip showing full path.
- Live per-mode size/token preview in the Copy Mode dropdown (e.g. "Compact Context (~4.2 KB)").
- Inline mode description label showing estimated token savings per copy mode.
- Search match highlighting in the file tree, plus a one-click clear ("×") button.
- Selected-file row highlighting in the tree view.
- Per-file right-click context menu: copy single file (Normal/Compact/Structure), copy relative path, open in Explorer.
- Scroll position is preserved per file when switching between files or copy modes.
- Advanced settings panel visibility and active tab now persist across restarts.
- Toast notifications now queue instead of interrupting each other.
- Large-file warnings in the status bar auto-clear after 4 seconds without overwriting newer messages.
- Reset-to-defaults now requires confirmation via a themed popup (Enter/Escape supported).

### Changed

- "Skeleton Mode" renamed to "Code Structure" throughout the UI and docs.
- "Compact" mode renamed to "Compact Context" throughout the UI and docs.
- Copy Mode selector changed from a native OptionMenu to a themed ttk Combobox.
- Files exceeding the large-file threshold are now skipped (with a note) rather than included in full when bundling.
- Git Diff mode returns a clear "no changes" message instead of an ambiguous empty result.

### Fixed

- Clipboard copy no longer crashes when sharing over LAN.
- "Strip Comments" mode no longer inserts literal `\n` characters instead of real line breaks.
- Git diff and Mermaid graph output no longer contain literal `\n` text instead of line breaks.
- Reset Defaults no longer references a non-existent settings variable.
- LAN share toggle now correctly starts the server when triggered directly.
- Single-file copy and "copy relative path" no longer produce incorrect paths when no folder is loaded.
- Recent-projects list now shows folder name (and disambiguating parent) instead of a truncated full path.

## [0.1.0-alpha] - 2026-07-15

### Added

- Initial release of Project Context Copier.
- Comprehensive UI with Dark and Light themes.
- Smart filtering (Extensions, Folders, Wildcards, Regex, .gitignore).
- Context compression (Full Source, Compact, Skeleton Mode, Mermaid Graph, Git Diff).
- LAN Sharing capability for easy context transfer.
- Live preview for selected files.
- Recent projects tracking.
- Quick Presets for common tech stacks (Python, React, Android, Markdown).
