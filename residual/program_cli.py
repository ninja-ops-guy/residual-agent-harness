"""CLI for RESIDUAL Program Control."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .core import ContractError
from .program_control import DISPOSITIONS, PRIORITIES, RELATION_KINDS, STATES, ProgramControl

DEFAULT_REPO = os.environ.get("RESIDUAL_PROGRAM_REPO", "ninja-ops-guy/residual-agent-harness")
DEFAULT_DATA = os.environ.get("RESIDUAL_PROGRAM_DATA", str(Path.home() / ".residual" / "program"))


def _print(value, as_json=False):
    if as_json:
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return
    if isinstance(value, dict) and "item_id" in value:
        print(f"{value['item_id']}  {value['state']}  {value['v1_disposition']}  {value['title']}")
        if value.get("next_action"):
            print(f"  next: {value['next_action']}")
        return
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="RESIDUAL Program Control")
    parser.add_argument("--data", default=DEFAULT_DATA)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync", help="Import and freeze the current open GitHub inventory")
    sync.add_argument("--json", action="store_true")

    status = sub.add_parser("status", help="Show current program summary")
    status.add_argument("--json", action="store_true")

    listing = sub.add_parser("list", help="List normalized program items")
    listing.add_argument("--state", choices=sorted(STATES))
    listing.add_argument("--disposition", choices=sorted(DISPOSITIONS))
    listing.add_argument("--workstream")
    listing.add_argument("--all", action="store_true", help="Include terminal/superseded items")
    listing.add_argument("--json", action="store_true")

    show = sub.add_parser("show", help="Show one program item")
    show.add_argument("item_id")
    show.add_argument("--json", action="store_true")

    owner = sub.add_parser("owner", help="Show items requiring owner action")
    owner.add_argument("--json", action="store_true")

    setp = sub.add_parser("set", help="Set authoritative RESIDUAL program state for an item")
    setp.add_argument("item_id")
    setp.add_argument("--state", choices=sorted(STATES))
    setp.add_argument("--disposition", choices=sorted(DISPOSITIONS))
    setp.add_argument("--workstream")
    setp.add_argument("--priority", choices=sorted(PRIORITIES))
    setp.add_argument("--owner")
    setp.add_argument("--next-action")
    setp.add_argument("--owner-action", choices=["yes", "no"])
    setp.add_argument("--note", action="append", default=[])
    setp.add_argument("--bind-current-head", action="store_true")

    link = sub.add_parser("link", help="Add an explicit dependency/supersession relation")
    link.add_argument("source")
    link.add_argument("kind", choices=sorted(RELATION_KINDS))
    link.add_argument("target")

    seed = sub.add_parser("seed", help="Apply an explicit program disposition/relation seed after sync")
    seed.add_argument("path")

    add = sub.add_parser("add", help="Add a non-GitHub program item")
    add.add_argument("title")
    add.add_argument("--state", choices=sorted(STATES), default="DISCOVERED")
    add.add_argument("--disposition", choices=sorted(DISPOSITIONS), default="UNCLASSIFIED")
    add.add_argument("--workstream", default="BACKLOG")
    add.add_argument("--priority", choices=sorted(PRIORITIES), default="P2")
    add.add_argument("--next-action")
    add.add_argument("--owner-action", action="store_true")

    export = sub.add_parser("export", help="Write the current immutable projection to a file")
    export.add_argument("output")

    args = parser.parse_args(argv)
    control = ProgramControl(args.data)

    try:
        if args.command == "sync":
            snapshot = control.sync(args.repo, token=os.environ.get("GITHUB_TOKEN"))
            value = {
                "snapshot_sha256": snapshot["snapshot_sha256"],
                "inventory_sha256": snapshot["inventory_sha256"],
                "summary": snapshot["summary"],
            }
            _print(value, args.json)
            return 0

        if args.command == "status":
            _print(control.dashboard(), args.json)
            return 0

        if args.command == "list":
            items = control.current()["items"]
            if not args.all:
                items = [x for x in items if x.get("active")]
            if args.state:
                items = [x for x in items if x["state"] == args.state]
            if args.disposition:
                items = [x for x in items if x["v1_disposition"] == args.disposition]
            if args.workstream:
                items = [x for x in items if x["workstream"] == args.workstream]
            if args.json:
                _print(items, True)
            else:
                for item in items:
                    _print(item)
            return 0

        if args.command == "show":
            _print(control.item(args.item_id), args.json)
            return 0

        if args.command == "owner":
            value = control.dashboard()["owner_actions"]
            if args.json:
                _print(value, True)
            else:
                for item in value:
                    _print(item)
            return 0

        if args.command == "set":
            patch = {}
            if args.state:
                patch["state"] = args.state
            if args.disposition:
                patch["v1_disposition"] = args.disposition
            if args.workstream is not None:
                patch["workstream"] = args.workstream
            if args.priority:
                patch["priority"] = args.priority
            if args.owner is not None:
                patch["owner"] = args.owner
            if args.next_action is not None:
                patch["next_action"] = args.next_action
            if args.owner_action:
                patch["owner_action_required"] = args.owner_action == "yes"
            if args.note:
                patch["notes"] = args.note
            if not patch:
                raise ContractError("set requires at least one field")
            record = control.set_item(
                args.item_id,
                patch,
                bind_head="current" if args.bind_current_head else None,
            )
            _print(record, True)
            return 0

        if args.command == "link":
            control.link(args.source, args.target, args.kind)
            print(f"{args.source} {args.kind} {args.target}")
            return 0

        if args.command == "add":
            item_id = control.add_manual(
                args.title,
                state=args.state,
                disposition=args.disposition,
                workstream=args.workstream,
                priority=args.priority,
                next_action=args.next_action,
                owner_action_required=args.owner_action,
            )
            print(item_id)
            return 0

        if args.command == "seed":
            value = json.loads(Path(args.path).read_text(encoding="utf-8"))
            _print(control.apply_seed(value), True)
            return 0

        if args.command == "export":
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(control.current(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(str(output))
            return 0

        raise ContractError("unknown program command")
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"residual program: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
