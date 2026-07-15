# Project Context Copier

> Build, compress, and copy your project's context for AI assistants like ChatGPT, Claude, Gemini, Copilot, and Cursor.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)  ![Platform](https://img.shields.io/badge/Platform-Windows-success.svg)  ![License](https://img.shields.io/badge/License-MIT-green.svg)  ![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)

---

## Overview

Project Context Copier is a desktop utility designed to prepare source code for Large Language Models (LLMs).

Instead of manually copying dozens of files, the application automatically:

- Loads an entire project
- Filters unnecessary files
- Removes comments
- Generates compact skeletons
- Creates Mermaid project graphs
- Includes Git changes
- Packages everything into one optimized context
- Copies directly to your clipboard

Perfect for ChatGPT, Claude, Gemini, Cursor, GitHub Copilot and other AI coding assistants.

---

# Features

## Project Loading

- Load entire folders
- Load individual files
- Drag & Drop support
- Live project preview

---

## Smart Filtering

Filter by:

- Extensions
- Folders
- Wildcards
- Regex (optional)
- .gitignore support

Exclude:

- node_modules
- .venv
- __pycache__
- build folders
- generated files

---

## Context Compression

Three copy modes:

### Full Source

Copies complete project source.

### Compact

Removes:

- comments
- extra blank lines
- unnecessary indentation

while preserving functionality.

### Skeleton Mode

Generates structural code only.

Useful for architecture discussions.

---

## Git Integration

- Git Diff mode
- Include only changed files
- Review unstaged modifications

---

## Mermaid Graph

Generate project call graphs automatically.

Useful for:

- Documentation
- Architecture reviews
- AI understanding

---

## Live Preview

Preview selected files before copying.

Supports:

- Code
- Markdown
- Rich formatting

---

## LAN Sharing

Start a lightweight local HTTP server.

Open the generated URL on another device to retrieve the packaged project context.

---

## Themes

- Dark Mode
- Light Mode

---

## Recent Projects

Quickly reopen recently used folders.

---

## Clipboard Ready

One click copies the generated project context directly into the system clipboard.

---

# Screenshots

(Add screenshots here)

```
screenshots/main-dark.png

screenshots/main-light.png

screenshots/settings.png
```

---

# Installation

## Download

Download the latest executable from the GitHub Releases page.

No Python installation is required.

---

## Run

Simply launch

```
ProjectContextCopier.exe
```

---

# Build From Source

Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/project-context-copier.git

cd project-context-copier
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run

```bash
python main.py
```

---

# Requirements

- Windows 10/11
- Python 3.10+

---

# Roadmap

## v0.1

- Project loading
- Compression
- Skeleton generation
- Git Diff
- Mermaid graphs
- LAN sharing

---

## v0.2

- Search improvements
- More presets
- Better statistics

---

## v0.3

- Plugin system
- Custom exporters

---

## v0.5

- Multi-language parsing
- Better UI animations

---

## v1.0

- Stable release
- Automatic updates
- Plugin marketplace

---

# Why this project?

Modern AI coding assistants work best when given the right context.

Project Context Copier automates that process by preparing a clean, compact, and structured representation of your codebase.

---

# License

MIT License

---

# Contributing

Contributions, issues and feature requests are welcome.

---

# Author

Developed by Parth
