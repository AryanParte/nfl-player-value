"""Check the frozen evidence registry or reject an unsupported score request."""

import argparse
import json
from pathlib import Path
import sys

from nfl_value.admission import load_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--registry", type=Path, default=Path("config/admission-2026-v1.json"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    require = commands.add_parser("require-score")
    require.add_argument("module_id")
    require.add_argument("--role", required=True)
    require.add_argument("--registry-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        path = (
            args.registry if args.registry.is_absolute() else args.repository_root / args.registry
        )
        registry = load_registry(
            path,
            repository_root=args.repository_root,
            expected_sha256=getattr(args, "registry_sha256", None),
        )
        if args.command == "require-score":
            registry.require_score(args.module_id, args.role)
        print(json.dumps(registry.summary(), indent=2, sort_keys=True))
    except (ValueError, OSError, TypeError) as exc:
        print(f"Admission check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
