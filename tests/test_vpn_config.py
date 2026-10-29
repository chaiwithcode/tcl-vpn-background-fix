# Created by Deepak Sharma on 29/10/2026.
# Copyright © 2026 ChaiWithCode. All rights reserved.
"""Hermetic tests for local configuration preparation; no TV access."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "skills/tcl-vpn-fix/scripts/vpn_config.py"
SPEC = importlib.util.spec_from_file_location("vpn_config", SCRIPT)
vpn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vpn)
PACKAGE = "org.example.vpn"
SERIAL = "test.invalid:5555"


def original_config():
    return [
        {"name": "KillWhiteList", "value": ["keep.one"]},
        {"name": "OneKeyCleanWhiteList", "value": ["keep.two"]},
        {"name": "OtherSetting", "value": {"nested": [True, 42, None]}},
    ]


def decode_command(command):
    """Model both shell parses and the TV's documented binding escape parser."""
    host = shlex.split(command)
    if host[:4] != ["adb", "-s", SERIAL, "shell"] or len(host) != 5:
        raise AssertionError("Unexpected host arguments")
    remote = shlex.split(host[4])
    if remote[:5] != ["content", "update", "--uri", vpn.URI, "--bind"] or len(remote) != 6:
        raise AssertionError("Unexpected remote arguments")
    pieces, value, escaped = [], "", False
    for character in remote[5]:
        if escaped:
            value += character
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            pieces.append(value)
            value = ""
        else:
            value += character
    if escaped:
        raise AssertionError("Trailing binding escape")
    pieces.append(value)
    if len(pieces) != 3 or pieces[:2] != ["config_content", "s"]:
        raise AssertionError("Unexpected content binding")
    return json.loads(pieces[2])


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tcl-vpn-tests-")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        # Even a future accidental ADB invocation cannot touch a real device.
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.adb_marker = self.root / "adb-was-called"
        fake_adb = self.bin / "adb"
        fake_adb.write_text("#!/bin/sh\n: > \"$ADB_TEST_MARKER\"\nexit 97\n")
        fake_adb.chmod(0o700)
        self.environment = dict(os.environ, PATH=str(self.bin), ADB_TEST_MARKER=str(self.adb_marker))

    def write(self, name, config, provider_row=False):
        destination = self.root / name
        value = json.dumps(config)
        destination.write_text((vpn.PREFIX if provider_row else "") + value, encoding="utf-8")
        return destination

    def cli(self, *arguments):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *map(str, arguments)],
            cwd=self.root, env=self.environment, text=True, capture_output=True, check=False,
        )
        self.assertFalse(self.adb_marker.exists(), "The local helper unexpectedly invoked ADB")
        return result

    def prepare(self, config=None, output="backup", package=PACKAGE):
        source = self.write("query.txt", original_config() if config is None else config, provider_row=True)
        return self.cli("prepare", "--query", source, "--serial", SERIAL,
                        "--package", package, "--output", self.root / output)

    def test_only_selected_package_is_added_without_mutating_input(self):
        config = original_config()
        expected = copy.deepcopy(config)
        expected[0]["value"].append(PACKAGE)
        expected[1]["value"].append(PACKAGE)
        self.assertEqual(vpn.add_package(config, PACKAGE), expected)
        self.assertEqual(config, original_config())
        self.assertEqual(vpn.add_package(expected, PACKAGE), expected)

    def test_preexisting_entry_is_not_duplicated(self):
        config = original_config()
        config[0]["value"].append(PACKAGE)
        result = vpn.add_package(config, PACKAGE)
        self.assertEqual(result[0], config[0])
        self.assertEqual(result[1]["value"], ["keep.two", PACKAGE])

    def test_provider_row_and_plain_backup_are_supported(self):
        config = original_config()
        for name, row in (("query.txt", True), ("backup.json", False)):
            with self.subTest(name=name):
                self.assertEqual(vpn.read_config(self.write(name, config, row)), config)

    def test_schema_and_multiple_provider_rows_are_rejected(self):
        for config in (
            {}, original_config()[1:], original_config() + [original_config()[0]],
            [{"name": "KillWhiteList", "value": 42}, original_config()[1]],
            [{"name": "KillWhiteList", "value": [True]}, original_config()[1]],
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                vpn.read_config(self.write("bad.json", config))
        multirow = self.root / "multirow.txt"
        multirow.write_text(vpn.PREFIX + json.dumps(original_config()) + "\nRow: 1 project_id=other")
        with self.assertRaises(ValueError):
            vpn.read_config(multirow)

    def test_commands_round_trip_adversarial_strings(self):
        config = original_config()
        config[2]["value"] = "quote ' and \" colon: backslash \\ newline\n 雪 $(touch BAD) `touch BAD` ; & |"
        self.assertEqual(decode_command(vpn.update_command(config, SERIAL)), config)
        self.assertFalse((self.root / "BAD").exists())

    def test_invalid_package_or_placeholder_serial_stops_before_output(self):
        for index, package in enumerate(("", "YOUR_VPN_PACKAGE", "bad package", "org.app;touch BAD")):
            with self.subTest(package=package):
                result = self.prepare(output=f"invalid-{index}", package=package)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / f"invalid-{index}").exists())
        for serial in ("", "TV_IP:5555", "bad serial", "-d"):
            with self.subTest(serial=serial), self.assertRaises(ValueError):
                vpn.update_command(original_config(), serial)

    def test_prepare_cli_creates_exact_backups_without_running_adb(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / "backup"
        self.assertEqual(json.loads((output / "before.json").read_text()), original_config())
        expected = vpn.add_package(original_config(), PACKAGE)
        self.assertEqual(json.loads((output / "after.json").read_text()), expected)
        self.assertEqual(decode_command((output / "apply-command.txt").read_text()), expected)

    def test_existing_backup_directory_is_never_overwritten(self):
        output = self.root / "backup"
        output.mkdir()
        marker = output / "before.json"
        marker.write_text("original-backup")
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "original-backup")
        self.assertFalse((output / "after.json").exists())

    def test_already_excluded_package_produces_no_apply_command(self):
        config = vpn.add_package(original_config(), PACKAGE)
        result = self.prepare(config)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No update needed", result.stdout)
        self.assertFalse((self.root / "backup/apply-command.txt").exists())

    def test_verify_cli_distinguishes_match_from_stale_config(self):
        expected = self.write("expected.json", original_config())
        current = self.write("current.txt", original_config(), provider_row=True)
        match = self.cli("verify", "--query", current, "--expected", expected)
        self.assertEqual(match.returncode, 0, match.stderr)
        self.write("current.txt", vpn.add_package(original_config(), PACKAGE), provider_row=True)
        mismatch = self.cli("verify", "--query", current, "--expected", expected)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("differs", mismatch.stderr)

    def rollback(self, original, applied, current):
        before = self.write("before.json", original)
        after = self.write("after.json", applied)
        query = self.write("current.txt", current, provider_row=True)
        return self.cli("rollback", "--query", query, "--before", before, "--after", after,
                        "--package", PACKAGE, "--serial", SERIAL)

    def test_valid_rollback_restores_exact_original(self):
        original = original_config()
        original[0]["value"].append(PACKAGE)
        applied = vpn.add_package(original, PACKAGE)
        result = self.rollback(original, applied, applied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(decode_command(result.stdout), original)

    def test_rollback_rejects_later_changes_and_tampered_record(self):
        original = original_config()
        applied = vpn.add_package(original, PACKAGE)
        changed = copy.deepcopy(applied)
        changed[2]["value"] = "later firmware setting"
        result = self.rollback(original, applied, changed)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        tampered = self.rollback(original, changed, changed)
        self.assertNotEqual(tampered.returncode, 0)
        self.assertEqual(tampered.stdout, "")

    def test_noop_rollback_prints_no_restore_command(self):
        config = vpn.add_package(original_config(), PACKAGE)
        result = self.rollback(config, config, config)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No rollback needed", result.stdout)
        self.assertNotIn("adb -s", result.stdout)


if __name__ == "__main__":
    unittest.main()
