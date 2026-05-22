# sc64deployer_gui

A PyQt6 desktop application that wraps the [SummerCart64](https://github.com/Polprzewodnikowy/SummerCart64) `sc64deployer` CLI tool in a graphical interface. Designed for N64 hobbyists and developers who prefer a point-and-click workflow over the command line.

## Features

- **Dynamic Command Interface** — buttons and inputs generated from a data-driven command/option/parameter schema
- **SD Card Explorer** — tree-based file browser with upload, download, rename, delete, and drag & drop support (including native macOS file promises)
- **ROM Upload** — with save type, TV type, and CIC seed options
- **Firmware & Update Management** — check and apply updates for sc64deployer, sc64menu.n64, and SC64 firmware via GitHub Releases
- **Debug & Memory Operations** — connect in debug mode, dump memory regions
- **Cross-Platform** — Windows, Linux (with `sudo` support), and macOS

## Requirements

- Python 3.8+
- PyQt6
- requests
- packaging

## Installation

```bash
pip install PyQt6 requests packaging
```

## Usage

```bash
python main.py
```

On first launch, select the `sc64deployer` binary via **File → Select sc64deployer**. The path is saved for subsequent sessions.

## Packaging

Build a standalone executable with PyInstaller:

```bash
pyinstaller sc64deployer_gui.spec
```

## Project Structure

```
sc64deployer_gui/
├── main.py                          # Application entry point, main UI, update logic
├── sd_explorer.py                   # SD Card file explorer widget
├── exec_runner.py                   # Background worker for subprocess execution
├── sc64_lists_command_options.py     # Data-driven command/option/parameter definitions
├── sc64deployer_gui.spec            # PyInstaller build spec
├── 64dd_ipl/                        # 64DD IPL files
└── build/                           # PyInstaller build output
```

## Documentation

| Document | Description |
|----------|-------------|
| [USER_MANUAL.md](USER_MANUAL.md) | End-user guide |
| [SD_EXPLORER_QUICKSTART.md](SD_EXPLORER_QUICKSTART.md) | Quick start for the SD Card Explorer |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture overview |
| [ARCHITECTURE_SD_EXPLORER.md](ARCHITECTURE_SD_EXPLORER.md) | SD Explorer architecture details |
| [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | Full documentation navigation guide |

## Platform Notes

| Platform | Notes |
|----------|-------|
| Windows  | File dialog filters `*.exe`; executable named `sc64deployer.exe` |
| Linux    | Prepends `sudo -n` to all commands (see [Notes.md](Notes.md) for sudoers setup) |
| macOS    | Native file promise drag & drop support |

## License

This project is licensed under the [MIT License](LICENSE).
