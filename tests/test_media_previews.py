import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from media_previews import frame_times, prepare  # noqa: E402


class MediaPreviewTests(unittest.TestCase):
    def test_manifest_covers_images_video_and_native_design(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            image = folder / "photo.jpg"
            image.write_bytes(b"test")
            inventory = {"source_folder": str(folder), "files": [
                {"relative_path": "photo.jpg", "path": str(image), "kind": "image", "extension": ".jpg"},
                {"relative_path": "film.mp4", "path": str(folder / "film.mp4"), "kind": "video", "extension": ".mp4"},
                {"relative_path": "layout.indd", "path": str(folder / "layout.indd"), "kind": "native_project", "extension": ".indd"},
            ]}
            result = prepare(inventory, folder / "previews", ffmpeg="")
            self.assertEqual(len(result["entries"]), 3)
            self.assertEqual(result["entries"][0]["preview_paths"], [str(image)])
            self.assertIn("ffmpeg_unavailable", result["entries"][1]["review_method"])
            self.assertIn("native_app", result["entries"][2]["review_method"])

    def test_video_samples_start_middle_and_end(self):
        points = frame_times(90)
        self.assertGreaterEqual(len(points), 3)
        self.assertLess(points[0], 30)
        self.assertGreater(points[-1], 60)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is optional")
    def test_extracts_review_frames_from_a_video(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            video = folder / "clip.mp4"
            subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
                            "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1", "-an", str(video)],
                           check=True, capture_output=True, timeout=20)
            inventory = {"source_folder": str(folder), "files": [
                {"relative_path": "clip.mp4", "path": str(video), "kind": "video", "extension": ".mp4",
                 "metadata": {"duration_seconds": 1.0}},
            ]}
            result = prepare(inventory, folder / "previews")
            frames = result["entries"][0]["preview_paths"]
            self.assertEqual(len(frames), 3)
            self.assertTrue(all(Path(path).stat().st_size > 0 for path in frames))


if __name__ == "__main__":
    unittest.main()
