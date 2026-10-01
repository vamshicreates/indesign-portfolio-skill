import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scan_folder import main, scan  # noqa: E402


class ScanFolderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "work"
        self.root.mkdir()

    def test_inventories_nested_work_and_extracts_docx_text(self):
        project = self.root / "Project Alpha"
        project.mkdir()
        (project / "notes.md").write_text("Directed and edited the short film.", encoding="utf-8")
        with zipfile.ZipFile(project / "case.docx", "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="x"><w:body><w:p><w:r><w:t>Festival screening</w:t></w:r></w:p></w:body></w:document>')
        (self.root / "poster.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (1080).to_bytes(4, "big") + (1350).to_bytes(4, "big") + b"\x00" * 8)
        hidden = self.root / ".indesign-portfolio"
        hidden.mkdir()
        (hidden / "old.json").write_text("{}", encoding="utf-8")

        result = scan(self.root)
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["groups"]["Project Alpha"]["files"], 2)
        files = {item["relative_path"]: item for item in result["files"]}
        self.assertIn("Festival screening", files["Project Alpha/case.docx"]["text_excerpt"])
        self.assertEqual(files["poster.png"]["metadata"], {"width": 1080, "height": 1350})
        self.assertEqual(files["poster.png"]["group_hint"], "(root files; grouping requires review)")

    def test_cli_writes_inventory_and_limit_fails(self):
        (self.root / "one.txt").write_text("A", encoding="utf-8")
        (self.root / "two.txt").write_text("B", encoding="utf-8")
        output = Path(self.temp.name) / "analysis" / "inventory.json"
        self.assertEqual(main(["--folder", str(self.root), "--output", str(output)]), 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["file_count"], 2)
        ledger_path = output.with_name("coverage-ledger.json")
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(len(ledger["decisions"]), 2)
        ledger["decisions"][0].update({"project": "Project One", "status": "selected", "reason": "Strongest example"})
        ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
        self.assertEqual(main(["--folder", str(self.root), "--output", str(output)]), 0)
        refreshed = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(refreshed["decisions"][0]["status"], "selected")
        with self.assertRaisesRegex(ValueError, "More than 1 files"):
            scan(self.root, max_files=1)


if __name__ == "__main__":
    unittest.main()
