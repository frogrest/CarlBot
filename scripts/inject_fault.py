"""Quick fault injection helper for manual testing.

Usage:
    python scripts/inject_fault.py <asset_id> <fault>
    python scripts/inject_fault.py --clear <asset_id>
    python scripts/inject_fault.py --clear-all
    python scripts/inject_fault.py --list

Examples:
    python scripts/inject_fault.py CAM-001 rtsp_down
    python scripts/inject_fault.py --clear CAM-001
    python scripts/inject_fault.py --clear-all
    python scripts/inject_fault.py --list
"""
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.common.config import RUNTIME

DB = RUNTIME / "portal.json"


def load():
    if not DB.exists():
        print("No portal state found. Start the portal service first.")
        sys.exit(1)
    return json.loads(DB.read_text(encoding="utf-8"))


def save(data):
    DB.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    if args[0] == "--list":
        data = load()
        print("Active faults:")
        faults = data.get("faults", {})
        if not faults:
            print("  (none)")
        for aid, fs in faults.items():
            print(f"  {aid}: {', '.join(fs)}")
        return

    if args[0] == "--clear-all":
        data = load()
        data["faults"] = {}
        save(data)
        print("All faults cleared.")
        return

    if args[0] == "--clear":
        if len(args) < 2:
            print("Usage: --clear <asset_id>")
            sys.exit(1)
        asset_id = args[1]
        data = load()
        cleared = data["faults"].pop(asset_id, [])
        save(data)
        print(f"Cleared faults on {asset_id}: {cleared}")
        return

    if len(args) < 2:
        print("Usage: <asset_id> <fault>")
        sys.exit(1)

    asset_id, fault = args[0], args[1]
    data = load()
    data["faults"].setdefault(asset_id, [])
    if fault not in data["faults"][asset_id]:
        data["faults"][asset_id].append(fault)
    save(data)
    print(f"Injected fault '{fault}' on {asset_id}")


if __name__ == "__main__":
    main()
