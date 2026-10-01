import json
import tempfile
import unittest
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from portfolio_cli import SpecError, load_spec, prepare  # noqa: E402


class PortfolioCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.image = self.base / "hero.jpg"
        self.image.write_bytes(b"sample")
        self.spec_path = self.base / "portfolio.json"
        self.data = {
            "profile": {"name": "A Person", "headline": "Designer", "hero_image": "hero.jpg"},
            "projects": [{"title": "Case", "summary": "Verified summary.", "images": ["hero.jpg"]}],
            "output": {"indd": "out/folio.indd", "pdf": "out/folio.pdf"},
        }

    def load(self):
        self.spec_path.write_text(json.dumps(self.data), encoding="utf-8")
        return load_spec(self.spec_path)

    def test_paths_resolve_from_spec_and_runner_is_valid(self):
        spec = self.load()
        self.assertEqual(spec["profile"]["hero_image"], str(self.image.resolve()))
        self.assertEqual(spec["output"]["indd"], str((self.base / "out" / "folio.indd").resolve()))
        runner = prepare(spec, self.base / "runner.jsx")
        source = runner.read_text(encoding="utf-8")
        self.assertIn("var PORTFOLIO_SPEC = ", source)
        self.assertIn("InDesign ExtendScript", source)
        prepare(spec, runner)
        runner.write_text("personal script", encoding="utf-8")
        with self.assertRaises(SpecError):
            prepare(spec, runner)

    def test_missing_image_blocks_generation(self):
        self.data["projects"][0]["hero_image"] = "missing.jpg"
        with self.assertRaisesRegex(SpecError, "does not exist"):
            self.load()

    def test_invalid_color_and_output_extension_block_generation(self):
        self.data["theme"] = {"accent": "red"}
        with self.assertRaisesRegex(SpecError, "hex color"):
            self.load()
        self.data["theme"] = {"accent": "#AABBCC"}
        self.data["output"]["indd"] = "out/folio.pdf"
        with self.assertRaisesRegex(SpecError, "Output paths"):
            self.load()


if __name__ == "__main__":
    unittest.main()
