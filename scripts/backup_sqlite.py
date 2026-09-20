"""Create a consistent local SQLite backup, never exposed by HTTP."""

import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("destination", type=Path)
args = parser.parse_args()
source = Path(__file__).resolve().parent.parent / "instance" / "gyanpath.db"
if not source.exists():
    raise SystemExit("Local database not found.")
if args.destination.exists():
    raise SystemExit("Destination exists; choose a new file.")
with sqlite3.connect(source) as src, sqlite3.connect(args.destination) as dst:
    src.backup(dst)
print("Backup created. Store privately; it contains personal information.")
