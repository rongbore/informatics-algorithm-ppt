import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dsu_trace_v29 import generate_trace
from render_dsu_frames_v29 import render_trace

NS = {"s": "http://www.w3.org/2000/svg"}


class DsuFrameTests(unittest.TestCase):
    def test_every_step_has_a_valid_svg_with_correct_edges(self):
        trace = generate_trace(4, [
            {"kind":"union","x":1,"y":2},
            {"kind":"union","x":3,"y":4},
            {"kind":"union","x":2,"y":4},
            {"kind":"find","x":1}])
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)/"frames"
            manifest = render_trace(trace,directory)
            self.assertEqual(len(manifest["frames"]),len(trace["steps"])+1)
            self.assertFalse(manifest["source_verified"])
            self.assertFalse(manifest["speech_bound"])
            states = [trace["initial"]]+[s["after"] for s in trace["steps"]]
            for frame,state in zip(manifest["frames"],states):
                raw = (directory/frame["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),frame["sha256"])
                svg = ET.fromstring(raw)
                self.assertEqual(len(svg.findall(".//s:circle",NS)),4)
                self.assertEqual(len(svg.findall(".//s:line",NS)),
                                 sum(i!=p for i,p in enumerate(state["parent"],1)))
            index = next(s["index"] for s in trace["steps"] if s["kind"]=="compress")
            svg = ET.parse(directory/manifest["frames"][index+1]["file"])
            self.assertEqual(len(svg.findall(".//s:line[@stroke='#15803D']",NS)),1)

    def test_tampered_trace_does_not_create_output(self):
        trace = generate_trace(2,[{"kind":"union","x":1,"y":2}])
        trace["steps"][-1]["after"]["parent"][0]=1
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/"frames"
            with self.assertRaises(ValueError):
                render_trace(trace,directory)
            self.assertFalse(directory.exists())

    def test_large_trace_rejected_for_legibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                render_trace(generate_trace(25,[]),Path(tmp)/"frames")
