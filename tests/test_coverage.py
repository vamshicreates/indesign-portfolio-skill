import unittest
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_coverage import check  # noqa: E402


class CoverageTests(unittest.TestCase):
    def test_every_file_needs_a_reviewed_decision(self):
        inventory = {"source_folder": "/work", "files": [{"relative_path": "one.ai"}, {"relative_path": "two.pdf"}]}
        ledger = {"source_folder": "/work", "decisions": [
            {"relative_path": "one.ai", "status": "selected", "project": "Campaign", "reason": ""},
            {"relative_path": "two.pdf", "status": "unreviewed", "project": "", "reason": ""},
        ]}
        self.assertTrue(any("Unreviewed" in error for error in check(inventory, ledger)))
        ledger["decisions"][1].update({"status": "excluded", "reason": "Unrelated invoice"})
        self.assertEqual(check(inventory, ledger), [])


if __name__ == "__main__":
    unittest.main()
