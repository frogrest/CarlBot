"""Reset all simulator and agent runtime state.

Usage:
    python scripts/reset_lab.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runtime = ROOT / "data" / "runtime"

count = 0
for path in runtime.glob("*.json"):
    path.unlink()
    count += 1

print(f"Reset complete — removed {count} runtime state file(s) from {runtime}")
print("Services will regenerate seed data on next start.")
