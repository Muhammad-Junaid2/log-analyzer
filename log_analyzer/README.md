#  System Log Analyzer & Report Generator

A professional CLI-based Python tool for analyzing system and application log files, detecting issues, and generating detailed reports.

---

##  Features

| Feature | Details |
|---|---|
| **Log Loading** | Supports `.log` and `.txt` files with line-by-line parsing |
| **Smart Parsing** | Regex-based detection of timestamps, log levels, and messages |
| **Multi-level Detection** | ERROR, WARNING, INFO, DEBUG, CRITICAL, FATAL |
| **Keyword Search** | Case-insensitive full-text search across all entries |
| **Filtering** | Filter by log level and/or date (YYYY-MM-DD) |
| **TXT Report** | Detailed summary saved to a formatted text file |
| **CSV Report** | All entries exported as a spreadsheet-compatible CSV |
| **Visual Report** | Multi-panel PNG chart (pie + bar + timeline + KPIs) |
| **Real-time Monitor** | Tail a live log file with colour-coded streaming output |
| **Critical Error Highlight** | Automatically flags crashes, OOM errors, exceptions |
| **Error Handling** | Graceful handling of missing files, empty files, bad formats |
| **Coloured CLI** | ANSI-coloured output: red=errors, yellow=warnings, cyan=info |

---

##  Project Structure

```
log_analyzer/
├── src/
│   ├── log_analyzer.py      # Main CLI application + all core modules
│   └── visual_report.py     # Bonus: matplotlib chart generator
├── samples/
│   └── system.log           # Sample log file for testing
├── reports/                 # Auto-created; stores generated reports
│   ├── report.txt
│   ├── report.csv
│   └── visual_report.png
├── generate_demo_reports.py # Quick demo script (generates all reports)
└── README.md
```

---

##  How to Run

### Prerequisites

- Python 3.10+
- `matplotlib` (optional — only needed for visual PNG report)

```bash
pip install matplotlib
```

## Run the Interactive CLI

```bash
cd log_analyzer
python src/log_analyzer.py
```

### Generate All Demo Reports at Once

```bash
python generate_demo_reports.py
```

---

##  CLI Menu

```
  ── MAIN MENU ──
  [1]  Load Log File
  [2]  Analyze Logs
  [3]  Search Logs
  [4]  Filter Logs
  [5]  Generate Report (TXT)
  [6]  Generate Report (CSV)
  [7]  Real-time Monitor
  [8]  Show Loaded Entries
  [0]  Exit
```

### Typical Workflow

1. Press **1** → Enter path to your `.log` or `.txt` file
2. Press **2** → View instant analysis (counts, error rate, peak hours, critical errors)
3. Press **3** → Search for a keyword (e.g., "timeout", "exception")
4. Press **4** → Filter by level (`ERROR`) and/or date (`2024-01-15`)
5. Press **5** → Save TXT summary report
6. Press **6** → Export CSV for spreadsheet analysis
7. Press **7** → Monitor a live log file in real time

---

##  Sample Report Output

```
============================================================
      SYSTEM LOG ANALYSIS REPORT
      Generated: 2024-01-15 12:00:00
============================================================

[ SUMMARY ]
------------------------------------------------------------
  Log Period      : 2024-01-15 08:00:01  →  2024-01-15 11:30:01
  Total Entries   : 67
  ERROR           : 18
  WARNING         : 14
  INFO            : 35
  Error Rate      : 26.87%

[ PEAK ACTIVITY HOURS ]
------------------------------------------------------------
  08:00  ████████████████████  (24)
  09:00  ████████████  (14)
  10:00  ██████████  (12)
```

---

##  Supported Log Format

The parser handles the standard format:

```
YYYY-MM-DD HH:MM:SS  LEVEL  Message text here
```

**Examples:**
```
2024-01-15 08:03:30 ERROR  Failed to connect to external API: timeout after 30s
2024-01-15 08:04:00 WARNING Response time exceeded threshold: 2500ms
2024-01-15 08:05:01 INFO  Fallback to read replica activated
```

Lines that don't match are still parsed using fallback regex to extract any recognizable log level.

---

##  Module Overview

| Module | Function | Description |
|---|---|---|
| `log_analyzer.py` | `load_log_file()` | Reads and parses a log file into `LogEntry` objects |
| `log_analyzer.py` | `analyze_logs()` | Returns stats dict: counts, hourly, critical events |
| `log_analyzer.py` | `search_logs()` | Case-insensitive keyword search |
| `log_analyzer.py` | `filter_logs()` | Filter by level and/or date |
| `log_analyzer.py` | `generate_report()` | Save TXT or CSV report |
| `log_analyzer.py` | `LogMonitor` | Real-time tail with coloured output |
| `visual_report.py` | `generate_visual_report()` | PNG multi-panel chart via matplotlib |

---

##  Bonus Features Implemented

- ✅ **Visual report** (matplotlib) — pie chart, hourly bar, stacked date bar, KPI panel
- ✅ **Real-time log monitoring** — live tailing with colour-coded output
- ✅ **Critical error highlighting** — detects OOM, crashes, exceptions automatically
- ✅ **Modular architecture** — each feature is an independent, testable function
- ✅ **Efficient for large files** — line-by-line streaming, no full-file buffering

---

##  License

MIT — free to use, modify, and distribute.
# log-analyzer
