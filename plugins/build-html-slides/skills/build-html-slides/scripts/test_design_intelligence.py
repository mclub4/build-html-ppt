from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent


class DesignIntelligenceTest(unittest.TestCase):
    def run_json(self, script: str, *args: str) -> dict:
        result = subprocess.run(
            ["python3", str(SCRIPTS / script), *args, "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_design_search_returns_three_distinct_candidates(self) -> None:
        result = self.run_json(
            "suggest_design_directions.py",
            "--subject-family", "hardware-semiconductor-manufacturing",
            "--communication-job", "research-sharing",
            "--luminosity", "mixed",
            "--density", "7",
            "--media-need", "9",
            "--variance", "6",
            "--motion", "3",
        )
        candidates = result["candidates"]
        self.assertEqual(len(candidates), 3)
        self.assertEqual(len({candidate["id"] for candidate in candidates}), 3)
        self.assertTrue(any("hardware-semiconductor-manufacturing" in candidate["subject_families"] for candidate in candidates))

    def test_design_search_does_not_accept_raw_prompt(self) -> None:
        result = subprocess.run(
            ["python3", str(SCRIPTS / "suggest_design_directions.py"), "--prompt", "dark AI architecture"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--subject-family", result.stderr)

    def test_chart_search_marks_overloaded_form_as_avoid(self) -> None:
        result = self.run_json(
            "suggest_chart.py",
            "--data-shape", "part-to-whole",
            "--category-count", "9",
        )
        self.assertEqual(result["charts"][0]["id"], "stacked-bar")
        self.assertEqual(result["charts"][0]["fit"], "avoid")
        self.assertIn("exceeds", result["charts"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
