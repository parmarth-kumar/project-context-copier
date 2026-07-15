# Contributing

## Development Setup

Clone

```bash
git clone https://github.com/parmarth-kumar/project-context-copier.git

cd project-context-copier
```

Install

```bash
pip install -r requirements.txt
```

Run

```bash
python main.py
```

Build Executable

```bash
pyinstaller ^
--onefile ^
--windowed ^
--add-data "assets;assets" ^
--icon assets/icon.ico ^
--name ProjectContextCopier ^
main.py
```

## Pull Requests

Contributions, bug reports and feature requests are welcome.