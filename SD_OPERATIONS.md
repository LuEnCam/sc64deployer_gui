I'll help you analyze the SD options in this project. Let me first explore the codebase to understand what SD options are available.   

Searched for regex `SD|sd.*option|option.*sd`, 20 results

Read [](file:///c%3A/Users/PC/Documents/GitHub/sc64deployer_gui/sc64_lists_command_options.py#1-1), lines 1 to 100

Read [](file:///c%3A/Users/PC/Documents/GitHub/sc64deployer_gui/ARCHITECTURE.md#1-1), lines 1 to 50

Read [](file:///c%3A/Users/PC/Documents/GitHub/sc64deployer_gui/sc64_lists_command_options.py#72-72), lines 72 to 90

Searched for text `PATH_SD|PATH_PC_SD|PATH_SD_PC|PATH_SD_DUO`, 14 results

## Analysis of SD Card Options

The sc64deployer_gui provides comprehensive SD card operations through the **`sd` command**. Here's a detailed breakdown:

### SD Command Overview
The `sd` command is used to "Perform operations on the SD card" connected to the SC64 (SummerCart64) device.

### Available SD Subcommands

| Subcommand | Arguments | Path Type | Purpose |
|---|---|---|---|
| **`ls`** | 1 | `PATH_SD` | List files in a directory on the SD card |
| **`stat`** | 1 | `PATH_SD` | Display file or directory metadata/status |
| **`mv`** | 2 | `PATH_SD_DUO` | Move or rename files/directories (SD→SD) |
| **`rm`** | 1 | `PATH_SD` | Remove a file or empty directory |
| **`download`** | 2 | `PATH_SD_PC` | Transfer file from SD card to PC |
| **`upload`** | 2 | `PATH_PC_SD` | Transfer file from PC to SD card |
| **`mkfs`** | 0 | (none) | Format/initialize the SD card |

### SD Path Types (Specialized UI Controls)

The GUI uses 4 specialized path input types for SD operations:

- **`PATH_SD`** (Type 11): Single SD path input with placeholder "Path on SD Card (\"/\" for root)"
- **`PATH_SD_DUO`** (Type 12): Two SD paths (source & destination) — used for `mv` operations
- **`PATH_PC_SD`** (Type 13): PC path → SD path — for uploading files to the device
- **`PATH_SD_PC`** (Type 14): SD path → PC path — for downloading files from the device

### Key Characteristics

1. **Root Path Support**: All SD paths accept `/` to reference the root directory
2. **Dual-Path Operations**: Some operations (`mv`, `download`, `upload`) handle both source and destination paths with contextual UI prompts
3. **File Management**: Supports listing, moving, renaming, and deleting files on the SD card
4. **Format Operation**: Includes destructive formatting capability (`mkfs`)
5. **PC Integration**: Special path types distinguish between reading from/writing to the PC vs. the SD card

### Usage in the GUI
The application dynamically generates input controls based on these path types, providing appropriate placeholders and file browser options for each operation.