#!/usr/bin/env python3
"""Regression tests for the non-mutating environment preflight."""

from __future__ import annotations

import subprocess
import unittest

from scripts.check_environment import inspect_environment, parse_node_major


class EnvironmentPreflightTests(unittest.TestCase):
    def test_parse_node_major(self) -> None:
        self.assertEqual(parse_node_major("v18.20.4"), 18)
        self.assertEqual(parse_node_major("22.1.0"), 22)
        self.assertIsNone(parse_node_major("unknown"))

    def test_missing_node_blocks_browser_check_without_installing(self) -> None:
        calls: list[list[str]] = []

        def run(command, **_kwargs):
            calls.append(command)
            raise AssertionError("subprocess must not run when Node.js is missing")

        result = inspect_environment(which=lambda _name: None, run=run)
        by_name = {check["name"]: check for check in result["checks"]}
        self.assertFalse(result["ready"])
        self.assertEqual(by_name["node"]["status"], "fail")
        self.assertEqual(by_name["playwright_chromium"]["status"], "blocked")
        self.assertEqual(calls, [])
        self.assertTrue(result["installation_suggestions"])

    def test_ready_environment_passes_node_and_browser_checks(self) -> None:
        def run(command, **_kwargs):
            if command[1:] == ["--version"]:
                return subprocess.CompletedProcess(command, 0, stdout="v20.11.1\n", stderr="")
            if command[-1] == "--check":
                return subprocess.CompletedProcess(command, 0, stdout="OK: Chromium ready\n", stderr="")
            raise AssertionError(f"unexpected command: {command}")

        result = inspect_environment(which=lambda _name: "/usr/bin/node", run=run)
        self.assertTrue(result["ready"])
        self.assertTrue(all(check["status"] == "pass" for check in result["checks"]))
        self.assertEqual(result["installation_suggestions"], [])


if __name__ == "__main__":
    unittest.main()
