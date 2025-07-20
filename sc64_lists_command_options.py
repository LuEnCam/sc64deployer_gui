from enum import Enum

class Types(Enum):
    TEXT = 1
    PATH = 2
    RADIO = 3
    SPINNER = 4
    ADDRESS = 5
    HEX_4 = 6
    ADDRESS_LENGTH_PATH = 7
    PATH_RADIO = 8
    PATH_HEX_4 = 9

list_of_commands = [
    ["list", "List connected SC64 devices"],
    ["upload", "Upload ROM (and save) to the SC64"], 
    ["download", "Download specific memory region and write it to file"], 
    ["64dd", "Upload ROM (and save), 64DD IPL then run disk/debug server"], 
    ["debug", "Enter debug mode"], 
    ["dump", "Dump data from arbitrary location in SC64 memory space"], 
    ["sd", "Perform operations on the SD card"], 
    ["info", "Print information about connected SC64 device"], 
    ["reset", "Reset SC64 state (same as after power-up)"],
    ["set", "Update persistent settings on SC64 device"], 
    ["firmware", "Print firmware metadata / update or backup SC64 firmware"], 
    ["test", "Test SC64 hardware"], 
    ["fifo-read", "Read data from FIFO"], 
    ["server", "Expose SC64 device over network"], 
    ["help", "Print this message or the help of the given subcommand(s)"],
    ["--version", "Print sc64_deployer exe version"]
]

# Options for commands
# Each option is a list with the following structure:
# [command, option, argument_count, description]
# command: the command this option belongs to (or "---" for global options)
# option: the option name (e.g., "--port")
# argument_count: number of arguments this option takes (0 for no arguments)
# type: the type of arguments (1 for text input, 2 for path file, 3 for radio buttons, 4 for spinner)
# description: a brief description of the option
list_of_options = [
    ["---", "--port", 1, Types.SPINNER ,"Connect to SC64 device on provided local port"],
    ["---", "--remote", 1, Types.ADDRESS, "Connect to SC64 device on provided remote address"],   
    ["---", "--help", 0, None, "Print help"],

    # list don't have options

    ["upload", "--reboot", 0, Types.PATH, "Attempt to reboot the console (requires specific support in the running game)"],
    ["upload", "--save", 1, Types.PATH, "Path to the save file <SAVE>"],
    ["upload", "--save-type", 1, Types.PATH_RADIO, "Override autodetected save type <SAVE_TYPE> [possible values: none, eeprom4k, eeprom16k, sram, sram-banked, sram1m, flashram]"],
    ["upload", "--direct", 0, Types.PATH, "Use direct boot mode (skip bootloader)"],
    ["upload", "--no-shadow", 0, Types.PATH, "Do not put last 128 kiB of ROM inside flash memory (can corrupt non EEPROM saves)"],
    ["upload", "--tv", 1, Types.PATH_RADIO, "Force TV type [possible values: pal, ntsc, mpal]"],
    ["upload", "--cic-seed", 1, Types.PATH_HEX_4, "Force CIC seed <CIC_SEED>"],
    ["upload", "", 0, Types.PATH, "Just upload ROM without any options"],

    ["download", "save", 1, Types.PATH, "Download save and write it to file <PATH>"],

    # special case for 64DD that could have 2 or more inputs other than the options of the command
    # Usage: sc64deployer.exe 64dd [OPTIONS] <DDIPL> [DISK]...
    ["64dd", "---", 0, None, "Upload 64DD IPL and DISK ROM.\nArguments:\n<DDIPL> Path to the 64DD IPL file.\n[DISK]...  Path to the 64DD disk file (.ndd format, can be specified multiple times)"],
    ["64dd", "--rom", 1, Types.PATH, "Path to the ROM cartridge file <ROM>"],
    ["64dd", "--save", 1, Types.PATH, "Path to the save file <SAVE> (also used by save writeback mechanism)"],
    ["64dd", "--save-type", 1, Types.RADIO, "Override autodetected save type <SAVE_TYPE> [possible values: none, eeprom4k, eeprom16k, sram, sram-banked, sram1m, flashram]"],
    ["64dd", "--direct", 0, None, "Use direct boot mode (skip bootloader)"],
    ["64dd", "--tv", 1, Types.RADIO, "Force TV type [possible values: pal, ntsc, mpal]"],
    ["64dd", "--cic-seed", 1, Types.HEX_4, "Force CIC seed <CIC_SEED>"],

    ["debug", "--save", 1, Types.PATH, "Path to the save file <SAVE> (also used by save writeback mechanism)"],
    ["debug", "--isv", 1, Types.ADDRESS, "Enable IS-Viewer64 and set listening address at ROM offset <offset> (in most cases it's fixed at 0x03FF0000)"],
    ["debug", "--euc-jp", 0, None, "Use EUC-JP encoding for text printing"],
    ["debug", "--no-writeback", 0, None, "Do not enable save writeback via USB"],
    ["debug", "--init", 1, Types.TEXT, "List of commands to send after connecting to the SC64, semicolon separated (;)"],

    ["dump", "---", 3, Types.ADDRESS_LENGTH_PATH, "Dump data from arbitrary location in SC64 memory space.\nArguments:\n<ADDRESS>  Starting memory address\n<LENGTH>   Dump length\n<PATH>     Path to the dump file"],

    ["sd", "ls", 1, Types.PATH, "List files of a directory <PATH> on the SD card"],
    ["sd", "stat", 1, Types.PATH, "Display a file or directory status <PATH>"],
    ["sd", "mv", 2, Types.PATH, "Move or rename a file or directory <SOURCE> to <DESTINATION>"],
    ["sd", "rm", 1, Types.PATH, "Remove a file or empty directory <PATH>"],
    ["sd", "download", 2, Types.PATH, "Download a file <SOURCE> from the SD card to the PC <DESTINATION>"],
    ["sd", "upload", 2, Types.PATH, "Upload a file <SOURCE> from the PC to the SD card <DESTINATION>"],
    ["sd", "mkfs", 0, None, "Format the SD card"],

    # info don't have options

    # reset don't have options

    ["set", "rtc", 0, None, "Synchronize real time clock (RTC) on the SC64 with local system time"],    
    ["set", "blink-on", 0, None, "Enable LED I/O activity blinking"], 
    ["set", "blink-off", 0, None, "Disable LED I/O activity blinking"], 

    ["firmware", "info", 1, Types.PATH, "Print metadata included inside SC64 firmware file <FIRMWARE>"],  
    ["firmware", "backup", 1, Types.PATH, "Download current SC64 firmware and save it to provided file <FIRMWARE>"],  
    # second argument is optional
    ["firmware", "update", 2, Types.PATH_RADIO, "Update SC64 firmware from provided file <FIRMWARE>\n --use-flash-memory  Put firmware update in the Flash memory instead of SDRAM"],  

    # test don't have options

    # fifo-read don't have options

    ["server", "---", 1, Types.ADDRESS, "Expose SC64 device over network\nArguments:\n[ADDRESS]  Listen on provided address:port [default: 127.0.0.1:9064]"]
]

# Parameters for commands (only useful for Types.RADIO or Types.PATH_RADIO)
list_of_parameters = [
    ["upload", "--save-type", ["none", "eeprom4k", "eeprom16k", "sram", "sram-banked", "sram1m", "flashram"]],
    ["64dd", "--save-type", ["none", "eeprom4k", "eeprom16k", "sram", "sram-banked", "sram1m", "flashram"]],
    ["upload", "--tv", ["pal", "ntsc", "mpal"]],
    ["64dd", "--tv", ["pal", "ntsc", "mpal"]],
    ["firmware", "--update", ["use-flash-memory"]],
]