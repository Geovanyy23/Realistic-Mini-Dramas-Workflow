"""mini-drama CLI — no credentials, no network, no spend.

  mini-drama validate <pack-dir>
  mini-drama plan <pack-dir> --dry-run [--state PATH]
  mini-drama privacy-scan [<dir>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import plan
from .privacy import scan
from .state import Store
from .validate import validate_pack


def cmd_validate(args) -> int:
    res = validate_pack(Path(args.pack))
    if res["ok"]:
        shots = res["pack"]["shots"]
        print(f"OK: {len(shots)} shots validated ({', '.join(s['id'] for s in sorted(shots, key=lambda s: s['ordinal']))}); "
              f"schemas + continuity rules passed.")
        return 0
    print("INVALID:")
    for e in res["errors"]:
        print(f"  - {e}")
    return 1


def cmd_plan(args) -> int:
    if not args.dry_run:
        print("Refusing: only --dry-run is implemented in this build. Live submission requires an owner-approved run "
              "and an armed adapter (see skills/realistic-mini-dramas/references/recovery.md).", file=sys.stderr)
        return 2
    res = validate_pack(Path(args.pack))
    if not res["ok"]:
        print("Pack invalid; run `mini-drama validate` first.", file=sys.stderr)
        for e in res["errors"]:
            print(f"  - {e}", file=sys.stderr)
        return 1
    state_path = Path(args.state) if args.state else Path(args.pack) / ".state" / "state.json"
    store = Store(state_path)
    report = plan(res["pack"], store, dry_run=True)
    print(json.dumps(report, indent=2))
    print(f"\nState written atomically to {state_path}")
    if report["approval_needed"]:
        print("APPROVAL NEEDED before any real generation — see blockers above.")
    return 0


def cmd_privacy(args) -> int:
    hits = scan(Path(args.dir))
    if hits:
        print("PRIVATE/SECRET CONTENT FOUND:")
        for h in hits:
            print(f"  - {h}")
        return 1
    print("privacy scan clean")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mini-drama")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate"); v.add_argument("pack"); v.set_defaults(fn=cmd_validate)
    pl = sub.add_parser("plan"); pl.add_argument("pack"); pl.add_argument("--dry-run", action="store_true")
    pl.add_argument("--state"); pl.set_defaults(fn=cmd_plan)
    pr = sub.add_parser("privacy-scan"); pr.add_argument("dir", nargs="?", default="."); pr.set_defaults(fn=cmd_privacy)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
