#!/usr/bin/env python3
# Created by Deepak Sharma on 29/10/2026.
# Copyright © 2026 ChaiWithCode. All rights reserved.
"""Prepare and verify TCL cleaner edits locally; never invoke ADB."""

import argparse
import copy
import json
import re
import shlex
from pathlib import Path


URI = "content://com.tcl.providers.config/TGuardMemoryManager"
PREFIX = "Row: 0 project_id=TGuardMemoryManager, config_content="
LISTS = ("KillWhiteList", "OneKeyCleanWhiteList")


def lists(config):
    if not isinstance(config, list):
        raise ValueError("Expected a configuration array.")
    result = {}
    for name in LISTS:
        matches = [item for item in config
                   if isinstance(item, dict) and item.get("name") == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {name} entry.")
        values = matches[0].get("value")
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError(f"Expected package-name strings in {name}.")
        result[name] = values
    return result


def read_config(filename):
    raw = Path(filename).read_text(encoding="utf-8").strip()
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX):]
    elif not raw.startswith("["):
        raise ValueError("Unexpected provider response; expected the matching project row or a JSON array.")
    config = json.loads(raw)
    lists(config)
    return config


def validate_serial(serial):
    if not serial or "TV_IP" in serial or any(c.isspace() for c in serial) or serial.startswith("-"):
        raise ValueError("Use the exact authorized TV serial/address from adb devices -l.")


def add_package(config, package):
    if (package == "YOUR_VPN_PACKAGE"
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", package)):
        raise ValueError("Use the verified installed VPN package name.")
    updated = copy.deepcopy(config)
    for values in lists(updated).values():
        if package not in values:
            values.append(package)
    return updated


def update_command(config, serial):
    validate_serial(serial)
    payload = json.dumps(config, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    escaped = payload.replace("\\", "\\\\").replace(":", "\\:")
    remote = "content update --uri " + URI + " --bind " + shlex.quote("config_content:s:" + escaped)
    return shlex.join(["adb", "-s", serial, "shell", remote])


def prepare(args):
    original = read_config(args.query)
    updated = add_package(original, args.package)
    command = update_command(updated, args.serial)
    output = Path(args.output)
    # Refuse reuse, even when the existing directory is empty.
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, value in (("before.json", original), ("after.json", updated)):
        with (output / name).open("x", encoding="utf-8") as file:
            json.dump(value, file, indent=2, ensure_ascii=True, allow_nan=False)
            file.write("\n")
    if original == updated:
        print("No update needed: package is already in both saved exclusion lists.")
    else:
        (output / "apply-command.txt").write_text(command + "\n", encoding="utf-8")
        for name in LISTS:
            if args.package not in lists(original)[name]:
                print(f"{name}: add {args.package}")
        print(f"Prepared {output / 'apply-command.txt'}; no TV command was run.")
    print("Before applying, review before.json/after.json and verify a fresh TV query against before.json.")


def verify(args):
    if read_config(args.query) != read_config(args.expected):
        raise ValueError("Configuration differs from expected. Do not apply a stale command or full rollback.")
    print("Configuration matches expected.")


def rollback(args):
    current = read_config(args.query)
    original = read_config(args.before)
    applied = read_config(args.after)
    # Validate the rollback record is exactly the claimed package-only change.
    if add_package(original, args.package) != applied:
        raise ValueError("Backup pair is not the expected two-list package-only change.")
    if current != applied:
        raise ValueError("Current configuration changed. Merge only the recorded additions instead of full rollback.")
    if current == original:
        print("No rollback needed: the recorded operation made no changes.")
        return
    print(update_command(original, args.serial))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="Create fresh local backups and an apply command.")
    prepare_parser.add_argument("--query", required=True)
    prepare_parser.add_argument("--package", required=True)
    prepare_parser.add_argument("--serial", required=True)
    prepare_parser.add_argument("--output", required=True)
    prepare_parser.set_defaults(run=prepare)
    verify_parser = commands.add_parser("verify", help="Compare a fresh query with an expected config.")
    verify_parser.add_argument("--query", required=True)
    verify_parser.add_argument("--expected", required=True)
    verify_parser.set_defaults(run=verify)
    rollback_parser = commands.add_parser("rollback", help="Print rollback only if the record and current config match.")
    for name in ("query", "before", "after", "package", "serial"):
        rollback_parser.add_argument("--" + name, required=True)
    rollback_parser.set_defaults(run=rollback)
    args = parser.parse_args()
    try:
        args.run(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
