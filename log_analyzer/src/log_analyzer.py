#!/usr/bin/env python3
"""
System Log Analyzer & Report Generator
A CLI tool to analyze system/application log files and generate meaningful reports.
"""

import re
import os
import csv
import sys
import json
import time
import threading
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path


# ─────────────────────────────────────────────
#  ANSI Color Codes for CLI Output
# ─────────────────────────────────────────────
class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    CYAN    = "\033[96m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"

    @staticmethod
    def error(text):   return f"{Colors.RED}{Colors.BOLD}{text}{Colors.RESET}"
    @staticmethod
    def warning(text): return f"{Colors.YELLOW}{Colors.BOLD}{text}{Colors.RESET}"
    @staticmethod
    def info(text):    return f"{Colors.CYAN}{text}{Colors.RESET}"
    @staticmethod
    def success(text): return f"{Colors.GREEN}{text}{Colors.RESET}"
    @staticmethod
    def header(text):  return f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.RESET}"
    @staticmethod
    def dim(text):     return f"{Colors.DIM}{text}{Colors.RESET}"


# ─────────────────────────────────────────────
#  Log Entry Data Class
# ─────────────────────────────────────────────
class LogEntry:
    """Represents a single parsed log entry."""

    LOG_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
        r'\s+(?P<level>ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL|FATAL)'
        r'\s+(?P<message>.+)$',
        re.IGNORECASE
    )
    FALLBACK_PATTERN = re.compile(
        r'(?P<level>ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL|FATAL)',
        re.IGNORECASE
    )

    def __init__(self, raw_line: str, line_number: int):
        self.raw        = raw_line.strip()
        self.line_num   = line_number
        self.timestamp  = None
        self.level      = "UNKNOWN"
        self.message    = self.raw
        self._parse()

    def _parse(self):
        m = self.LOG_PATTERN.match(self.raw)
        if m:
            ts_str = m.group("timestamp")
            try:
                self.timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                self.timestamp = None
            raw_lvl = m.group("level").upper(); self.level = "WARNING" if raw_lvl in ("WARN", "WARNING") else raw_lvl
            self.message = m.group("message").strip()
        else:
            fb = self.FALLBACK_PATTERN.search(self.raw)
            if fb:
                self.level = fb.group("level").upper().replace("WARN", "WARNING")

    @property
    def date_str(self):
        return self.timestamp.strftime("%Y-%m-%d") if self.timestamp else "unknown"

    def __repr__(self):
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else "no-timestamp"
        return f"[{ts}] {self.level:8s} | {self.message}"


# ─────────────────────────────────────────────
#  FILE LOADING MODULE
# ─────────────────────────────────────────────
def load_log_file(filepath: str) -> list[LogEntry]:
    """
    Load a .log or .txt file and parse each line into LogEntry objects.
    Raises FileNotFoundError or ValueError on problems.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if path.suffix.lower() not in (".log", ".txt"):
        raise ValueError(f"Unsupported file type '{path.suffix}'. Only .log and .txt are accepted.")
    if path.stat().st_size == 0:
        raise ValueError("The file is empty.")

    entries = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if line.strip():          # skip blank lines
                entries.append(LogEntry(line, line_num))

    if not entries:
        raise ValueError("File contains no readable log entries.")

    return entries


# ─────────────────────────────────────────────
#  LOG ANALYSIS MODULE
# ─────────────────────────────────────────────
def analyze_logs(entries: list[LogEntry]) -> dict:
    """
    Perform full analysis on parsed log entries.
    Returns a rich statistics dictionary.
    """
    level_counts = Counter(e.level for e in entries)
    date_counts  = Counter(e.date_str for e in entries)

    level_by_date = defaultdict(Counter)
    for e in entries:
        level_by_date[e.date_str][e.level] += 1

    hourly_counts = Counter()
    for e in entries:
        if e.timestamp:
            hourly_counts[e.timestamp.hour] += 1

    # Identify critical errors (ERROR / CRITICAL / FATAL)
    critical_keywords = ["critical", "fatal", "crash", "out of memory", "overflow",
                         "killed", "uncaught", "exception", "stack trace", "oom"]
    critical_entries = [
        e for e in entries
        if e.level in ("ERROR", "CRITICAL", "FATAL") and
        any(kw in e.message.lower() for kw in critical_keywords)
    ]

    timestamps = [e.timestamp for e in entries if e.timestamp]
    time_range = {
        "start": min(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else "N/A",
        "end":   max(timestamps).strftime("%Y-%m-%d %H:%M:%S") if timestamps else "N/A",
    }

    return {
        "total":           len(entries),
        "level_counts":    dict(level_counts),
        "date_counts":     dict(date_counts),
        "level_by_date":   {d: dict(c) for d, c in level_by_date.items()},
        "hourly_counts":   dict(hourly_counts),
        "critical_entries": critical_entries,
        "time_range":      time_range,
        "error_rate":      round(level_counts.get("ERROR", 0) / len(entries) * 100, 2),
    }


# ─────────────────────────────────────────────
#  SEARCH & FILTER MODULE
# ─────────────────────────────────────────────
def search_logs(entries: list[LogEntry], keyword: str) -> list[LogEntry]:
    """Case-insensitive keyword search across the full raw log line."""
    kw = keyword.lower()
    return [e for e in entries if kw in e.raw.lower()]


def filter_logs(entries: list[LogEntry],
                level: str = None,
                date: str  = None) -> list[LogEntry]:
    """
    Filter entries by log level and/or date string (YYYY-MM-DD).
    Both filters are AND-combined when supplied.
    """
    result = entries
    if level:
        lvl = level.upper().replace("WARN", "WARNING")
        result = [e for e in result if e.level == lvl]
    if date:
        result = [e for e in result if e.date_str == date]
    return result


# ─────────────────────────────────────────────
#  REPORT GENERATION MODULE
# ─────────────────────────────────────────────
def _build_report_text(entries: list[LogEntry], stats: dict) -> str:
    """Build a formatted plain-text summary report."""
    lines = []
    sep  = "=" * 60
    sep2 = "-" * 60

    lines.append(sep)
    lines.append("      SYSTEM LOG ANALYSIS REPORT")
    lines.append(f"      Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(sep)
    lines.append("")

    # ── Summary ──────────────────────────────
    lines.append("[ SUMMARY ]")
    lines.append(sep2)
    lines.append(f"  Log Period      : {stats['time_range']['start']}  →  {stats['time_range']['end']}")
    lines.append(f"  Total Entries   : {stats['total']}")
    lines.append(f"  ERROR           : {stats['level_counts'].get('ERROR', 0)}")
    lines.append(f"  WARNING         : {stats['level_counts'].get('WARNING', 0)}")
    lines.append(f"  INFO            : {stats['level_counts'].get('INFO', 0)}")
    lines.append(f"  DEBUG           : {stats['level_counts'].get('DEBUG', 0)}")
    lines.append(f"  Error Rate      : {stats['error_rate']}%")
    lines.append("")

    # ── Counts by date ────────────────────────
    lines.append("[ LOG COUNTS BY DATE ]")
    lines.append(sep2)
    for date, count in sorted(stats["date_counts"].items()):
        by_lvl = stats["level_by_date"].get(date, {})
        e = by_lvl.get("ERROR", 0)
        w = by_lvl.get("WARNING", 0)
        i = by_lvl.get("INFO", 0)
        lines.append(f"  {date}  Total:{count:5d}  ERROR:{e:4d}  WARN:{w:4d}  INFO:{i:4d}")
    lines.append("")

    # ── Peak hours ───────────────────────────
    if stats["hourly_counts"]:
        lines.append("[ PEAK ACTIVITY HOURS ]")
        lines.append(sep2)
        top_hours = sorted(stats["hourly_counts"].items(), key=lambda x: -x[1])[:5]
        for hour, count in top_hours:
            bar = "█" * min(count // 2, 30)
            lines.append(f"  {hour:02d}:00  {bar}  ({count})")
        lines.append("")

    # ── Critical errors ───────────────────────
    if stats["critical_entries"]:
        lines.append("[ CRITICAL ERRORS ]")
        lines.append(sep2)
        for e in stats["critical_entries"]:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else "N/A"
            lines.append(f"  [{ts}] Line {e.line_num:4d}: {e.message}")
        lines.append("")

    lines.append(sep)
    lines.append("  END OF REPORT")
    lines.append(sep)
    return "\n".join(lines)


def generate_report(entries: list[LogEntry],
                    stats: dict,
                    output_path: str,
                    fmt: str = "txt") -> str:
    """
    Save a summary report to output_path.
    fmt: 'txt' or 'csv'
    Returns the absolute path of the saved file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Line", "Timestamp", "Level", "Message"])
            for e in entries:
                ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else ""
                writer.writerow([e.line_num, ts, e.level, e.message])
    else:
        report_text = _build_report_text(entries, stats)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)

    return str(Path(output_path).resolve())


# ─────────────────────────────────────────────
#  REAL-TIME MONITORING MODULE
# ─────────────────────────────────────────────
class LogMonitor:
    """
    Watches a log file for new lines and prints them coloured.
    Runs in a background thread; call .stop() to halt.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._stop_event = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _tail(self):
        try:
            with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)          # seek to EOF
                print(Colors.success(f"\n  Monitoring '{self.filepath}' — press Enter to stop...\n"))
                while not self._stop_event.is_set():
                    line = f.readline()
                    if line:
                        entry = LogEntry(line, 0)
                        self._print_colored(entry)
                    else:
                        time.sleep(0.3)
        except OSError as exc:
            print(Colors.error(f"  Monitor error: {exc}"))

    @staticmethod
    def _print_colored(entry: LogEntry):
        ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "--:--:--"
        if entry.level in ("ERROR", "CRITICAL", "FATAL"):
            lvl_str = Colors.error(f"[{entry.level:8s}]")
        elif entry.level == "WARNING":
            lvl_str = Colors.warning(f"[{entry.level:8s}]")
        else:
            lvl_str = Colors.info(f"[{entry.level:8s}]")
        print(f"  {Colors.dim(ts)}  {lvl_str}  {entry.message}")


# ─────────────────────────────────────────────
#  CLI DISPLAY HELPERS
# ─────────────────────────────────────────────
def _print_banner():
    banner = r"""
  ╔══════════════════════════════════════════════════════╗
  ║        SYSTEM LOG ANALYZER & REPORT GENERATOR       ║
  ║              Python CLI Tool  v1.0                   ║
  ╚══════════════════════════════════════════════════════╝"""
    print(Colors.BLUE + Colors.BOLD + banner + Colors.RESET)


def _print_menu():
    print(f"\n{Colors.header('  ── MAIN MENU ──')}")
    options = [
        ("1", "Load Log File"),
        ("2", "Analyze Logs"),
        ("3", "Search Logs"),
        ("4", "Filter Logs"),
        ("5", "Generate Report (TXT)"),
        ("6", "Generate Report (CSV)"),
        ("7", "Real-time Monitor"),
        ("8", "Show Loaded Entries"),
        ("0", "Exit"),
    ]
    for key, label in options:
        print(f"  {Colors.CYAN}[{key}]{Colors.RESET}  {label}")
    print()


def _print_entries(entries: list[LogEntry], limit: int = 50):
    """Print entries coloured by level, capped at `limit`."""
    if not entries:
        print(Colors.warning("  No entries to display."))
        return

    shown = entries[:limit]
    for e in shown:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S") if e.timestamp else " " * 19
        if e.level in ("ERROR", "CRITICAL", "FATAL"):
            print(f"  {Colors.dim(ts)}  {Colors.error(f'{e.level:8s}')}  {e.message}")
        elif e.level == "WARNING":
            print(f"  {Colors.dim(ts)}  {Colors.warning(f'{e.level:8s}')}  {e.message}")
        else:
            print(f"  {Colors.dim(ts)}  {Colors.info(f'{e.level:8s}')}  {e.message}")

    if len(entries) > limit:
        print(Colors.dim(f"  … {len(entries) - limit} more entries not shown (total {len(entries)})"))


def _print_stats(stats: dict):
    """Pretty-print analysis statistics."""
    sep = "─" * 52
    print(f"\n{Colors.header('  ── ANALYSIS RESULTS ──')}")
    print(f"  {sep}")
    print(f"  Period  : {stats['time_range']['start']}  →  {stats['time_range']['end']}")
    print(f"  {sep}")
    print(f"  Total entries : {Colors.BOLD}{stats['total']}{Colors.RESET}")
    print(f"  {Colors.error('ERROR  ')}       : {stats['level_counts'].get('ERROR', 0)}")
    print(f"  {Colors.warning('WARNING')}       : {stats['level_counts'].get('WARNING', 0)}")
    print(f"  {Colors.info('INFO   ')}       : {stats['level_counts'].get('INFO', 0)}")
    print(f"  DEBUG         : {stats['level_counts'].get('DEBUG', 0)}")
    print(f"  Error rate    : {stats['error_rate']}%")
    print(f"  {sep}")

    if stats["critical_entries"]:
        print(f"\n  {Colors.error('⚠ CRITICAL ERRORS DETECTED:')}")
        for e in stats["critical_entries"][:5]:
            ts = e.timestamp.strftime("%H:%M:%S") if e.timestamp else "??:??:??"
            print(f"    {Colors.dim(ts)}  {e.message[:70]}…" if len(e.message) > 70 else
                  f"    {Colors.dim(ts)}  {e.message}")
        if len(stats["critical_entries"]) > 5:
            print(f"    … and {len(stats['critical_entries']) - 5} more")

    if stats["hourly_counts"]:
        print(f"\n  {Colors.header('Peak hours:')}")
        top = sorted(stats["hourly_counts"].items(), key=lambda x: -x[1])[:3]
        for hour, cnt in top:
            print(f"    {hour:02d}:00  — {cnt} entries")


# ─────────────────────────────────────────────
#  MAIN CLI LOOP
# ─────────────────────────────────────────────
def main():
    _print_banner()
    entries: list[LogEntry] = []
    stats: dict | None = None
    current_file: str = ""

    while True:
        _print_menu()
        choice = input(f"  {Colors.CYAN}Enter choice:{Colors.RESET} ").strip()

        # ── 1. Load File ──────────────────────────────────────────────
        if choice == "1":
            filepath = input("  Enter path to .log or .txt file: ").strip()
            try:
                entries = load_log_file(filepath)
                current_file = filepath
                stats = None   # invalidate previous analysis
                print(Colors.success(
                    f"\n  ✔ Loaded {len(entries)} entries from '{Path(filepath).name}'"
                ))
            except (FileNotFoundError, ValueError, OSError) as exc:
                print(Colors.error(f"\n  ✘ {exc}"))

        # ── 2. Analyze ────────────────────────────────────────────────
        elif choice == "2":
            if not entries:
                print(Colors.warning("\n  Load a log file first (option 1)."))
                continue
            stats = analyze_logs(entries)
            _print_stats(stats)

        # ── 3. Search ─────────────────────────────────────────────────
        elif choice == "3":
            if not entries:
                print(Colors.warning("\n  Load a log file first (option 1)."))
                continue
            keyword = input("  Search keyword: ").strip()
            if not keyword:
                print(Colors.warning("  Keyword cannot be empty."))
                continue
            results = search_logs(entries, keyword)
            print(f"\n  Found {Colors.BOLD}{len(results)}{Colors.RESET} match(es) for '{keyword}':\n")
            _print_entries(results)

        # ── 4. Filter ─────────────────────────────────────────────────
        elif choice == "4":
            if not entries:
                print(Colors.warning("\n  Load a log file first (option 1)."))
                continue
            print("  Filter by level   (ERROR / WARNING / INFO / DEBUG — leave blank to skip):")
            level = input("  Level: ").strip()
            print("  Filter by date    (YYYY-MM-DD — leave blank to skip):")
            date  = input("  Date : ").strip()
            results = filter_logs(entries, level or None, date or None)
            print(f"\n  {Colors.BOLD}{len(results)}{Colors.RESET} entries match the filter:\n")
            _print_entries(results)

        # ── 5. TXT Report ─────────────────────────────────────────────
        elif choice == "5":
            if not entries:
                print(Colors.warning("\n  Load a log file first (option 1)."))
                continue
            if stats is None:
                stats = analyze_logs(entries)
            fname = input(
                "  Output filename [reports/report.txt]: "
            ).strip() or "reports/report.txt"
            try:
                saved = generate_report(entries, stats, fname, fmt="txt")
                print(Colors.success(f"\n  ✔ Report saved to: {saved}"))
            except OSError as exc:
                print(Colors.error(f"\n  ✘ Could not save report: {exc}"))

        # ── 6. CSV Report ─────────────────────────────────────────────
        elif choice == "6":
            if not entries:
                print(Colors.warning("\n  Load a log file first (option 1)."))
                continue
            if stats is None:
                stats = analyze_logs(entries)
            fname = input(
                "  Output filename [reports/report.csv]: "
            ).strip() or "reports/report.csv"
            try:
                saved = generate_report(entries, stats, fname, fmt="csv")
                print(Colors.success(f"\n  ✔ CSV report saved to: {saved}"))
            except OSError as exc:
                print(Colors.error(f"\n  ✘ Could not save report: {exc}"))

        # ── 7. Real-time Monitor ──────────────────────────────────────
        elif choice == "7":
            filepath = current_file or input(
                "  Enter path to monitor (leave blank to use loaded file): "
            ).strip()
            if not filepath:
                print(Colors.warning("  No file specified."))
                continue
            if not Path(filepath).exists():
                print(Colors.error(f"  File not found: {filepath}"))
                continue
            monitor = LogMonitor(filepath)
            monitor.start()
            input()          # block until Enter pressed
            monitor.stop()
            print(Colors.success("  Monitoring stopped."))

        # ── 8. Show Entries ───────────────────────────────────────────
        elif choice == "8":
            if not entries:
                print(Colors.warning("\n  Load a log file first (option 1)."))
                continue
            try:
                n = int(input(f"  How many entries to show? [50]: ").strip() or "50")
            except ValueError:
                n = 50
            _print_entries(entries, limit=n)

        # ── 0. Exit ───────────────────────────────────────────────────
        elif choice == "0":
            print(Colors.success("\n  Goodbye!\n"))
            sys.exit(0)

        else:
            print(Colors.warning(f"\n  Unknown option '{choice}'. Please choose from the menu."))


if __name__ == "__main__":
    main()
