#!/usr/bin/env python3
"""
generate_demo_reports.py
Run this script to produce TXT, CSV, and PNG reports from the sample log file.
Usage:  python generate_demo_reports.py
"""

import sys
import os

# allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from log_analyzer import load_log_file, analyze_logs, generate_report
from visual_report import generate_visual_report

SAMPLE_LOG = os.path.join(os.path.dirname(__file__), "samples", "system.log")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def main():
    print("\n  Loading sample log file…")
    entries = load_log_file(SAMPLE_LOG)
    print(f"  Loaded {len(entries)} entries.")

    print("  Analyzing…")
    stats = analyze_logs(entries)

    # TXT report
    txt_path = os.path.join(REPORTS_DIR, "report.txt")
    saved = generate_report(entries, stats, txt_path, fmt="txt")
    print(f"  ✔ TXT report  →  {saved}")

    # CSV report
    csv_path = os.path.join(REPORTS_DIR, "report.csv")
    saved = generate_report(entries, stats, csv_path, fmt="csv")
    print(f"  ✔ CSV report  →  {saved}")

    # Visual PNG report (requires matplotlib)
    try:
        import matplotlib
        png_path = os.path.join(REPORTS_DIR, "visual_report.png")
        saved = generate_visual_report(entries, stats, png_path)
        if saved:
            print(f"  ✔ Visual PNG  →  {saved}")
    except ImportError:
        print("  ℹ  matplotlib not installed — skipping visual report.")

    print("\n  All reports generated successfully.\n")


if __name__ == "__main__":
    main()
