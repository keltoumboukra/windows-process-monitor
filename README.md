# Windows Process Monitor

A lightweight, open-source tool for monitoring Windows processes and system resources in real-time.

## Features

- **Process Exploration**: View all active processes with PID, name, status, CPU, and memory usage
- **Process Hierarchy**: Display parent-child process relationships
- **System Monitoring**: Real-time tracking of system-wide resource usage

## Installation

1. Clone this repository:
```bash
git clone keltoumboukra/windows-process-monitor
cd windows-process-monitor
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Process Listing
```bash
python main.py
```

### View Process Hierarchy
```bash
python main.py --hierarchy
```

### System Summary
```bash
python main.py --summary
```

## Requirements

- Python 3.11+
- Windows 10/11
- Administrator privileges (for full process access)

## Dependencies

- `psutil`: Cross-platform process and system utilities
- `tabulate`: Formatted table output