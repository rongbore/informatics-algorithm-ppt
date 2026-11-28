"""Exercise the actual FFmpeg camera filter and inspect decoded frames."""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from render_lesson_v2_4 import camera_filter


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required")
class CameraMediaTests(unittest.TestCase):
    def test_camera_cuts_change_real_frames_and_restore_full_view(self):
        width, height, fps = 320, 180, 10
        timeline = [
            {"start": 1, "end": 3, "zoom": 2, "x": 0, "y": 0},
            {"start": 4, "end": 6, "zoom": 2, "x": 160, "y": 0},
        ]
        # Left red, right blue. A zoom on either half should fill the frame.
        source = "color=red:s=320x180:r=10:d=7,drawbox=x=160:y=0:w=160:h=180:color=blue:t=fill"
        result = subprocess.run([
            "ffmpeg", "-v", "error", "-filter_threads", "1",
            "-f", "lavfi", "-i", source,
            "-vf", camera_filter(timeline, width, height, fps),
            "-pix_fmt", "rgb24", "-f", "rawvideo", "-threads", "1", "-"
        ], capture_output=True, check=True, timeout=30)
        frame_bytes = width * height * 3
        self.assertEqual(len(result.stdout), 70 * frame_bytes)
        def pixel(frame, x):
            offset = frame * frame_bytes + (90 * width + x) * 3
            return result.stdout[offset:offset+3]
        def is_red(rgb):
            return rgb[0] > rgb[2] + 100
        def is_blue(rgb):
            return rgb[2] > rgb[0] + 100
        for frame in (5, 35, 65):
            self.assertTrue(is_red(pixel(frame, 40)))
            self.assertTrue(is_blue(pixel(frame, 280)))
        self.assertTrue(is_red(pixel(15, 280)))
        self.assertTrue(is_blue(pixel(45, 40)))

if __name__ == "__main__":
    unittest.main()
