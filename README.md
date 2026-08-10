# SLE4442 Manager

A comprehensive tool for reading, writing, and managing SLE4442 smart cards with both GUI (PyQt5) and CLI support.

<p align="center"><img width="700" alt="SLE4442 Manager GUI" src="https://github.com/user-attachments/assets/9298edc5-a93b-4b7c-aacd-925f1c2f8aa0" /></p>


## Acknowledgments

Thanks to [@luu176](https://github.com/luu176/SLE4442-Card-Manager) and [@hvfrancesco](https://github.com/hvfrancesco/SLE4442-card-manager) for their previous work.

## Features
- **Read and Write card memory**
- **Import/Export** raw HEX format files
- **Read security memory** (error counter and protection bits)
- **Unlock and Change PSC** (PIN)
- **Send raw APDU commands** for advanced operations
- **Multiple reader support** with automatic detection
- **APDU logging** for debugging
- **Full CLI support** for automation and scripting

**GUI Overhaul (added by [@edomari](https://github.com/edomari)):**
- **Interactive byte-by-byte grid editing** with unsaved changes tracking (highlights modified bytes)
- **Dynamic grid formatting** (switch between 8, 16, and 32 columns instantly)
- **Theme support** featuring a retro Windows XP mode

## Screenshots

### Interactive Memory Grid
<p align="center"><img width="700" alt="Interactive memory grid with unsaved changes" src="images/grid.png" /></p>

### Read Operations
<p align="center"><img width="700" alt="Read card memory" src="https://github.com/user-attachments/assets/9298edc5-a93b-4b7c-aacd-925f1c2f8aa0" /></p>

### Export and Import
<p align="center"><img width="700" alt="Export and Import functionality" src="https://github.com/user-attachments/assets/aad7e501-ca75-43e0-9e3a-cb9dc5784fb1" /></p>
<p align="center"><img width="700" alt="Export and Import functionality" src="https://github.com/user-attachments/assets/de0fda02-649b-42a7-915d-60bd4e40809a" /></p>

### Write Operations
<p align="center"><img width="700" alt="Write to card" src="https://github.com/user-attachments/assets/bde4e301-222b-48db-9a06-a279744ed7d2" /></p>

### Write one or more bytes
<p align="center"><img width="700" alt="PIN unlock and error handling" src="images/write_memory.png" /></p>

### PIN Management and Exception Handling
<p align="center"><img width="700" alt="PIN unlock and error handling" src="https://github.com/user-attachments/assets/41599225-f303-4ffa-9acd-4b22d2a3ac6f" /></p>

### Raw APDU and Logs
<p align="center"><img width="700" alt="Raw APDU commands and logging" src="https://github.com/user-attachments/assets/61274054-01b9-42db-99ad-3398b07c3bfd" /></p>

### Windows XP Theme
<p align="center"><img width="700" alt="Windows XP Theme" src="images/windowsxp_theme.png" /></p>

## Quick Start

```bash
pip install pyscard
pip install PyQt5 # Optional, for GUI mode

python sle4442_manager.py
python sle4442_manager.py --nogui # for CLI mode