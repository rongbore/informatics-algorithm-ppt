import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dsu_trace_v29 import generate_trace
from render_dsu_frames_v29 import render_trace
from compile_dsu_timeline_v29 import compile_timeline, digest


class DsuTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "frames"
        self.trace = generate_trace(2, [{"kind":"union","x":1,"y":2}])
        manifest = render_trace(self.trace, self.directory)
        events = [{"event_id":"e"+str(i),"phrase_index":0,"text":"step "+str(i),
                   "start":i*2,"end":i*2+1,"type":"narration"}
                  for i in range(len(manifest["frames"]))]
        self.timing = {"schema_version":"2.4.1","slide":1,
                       "duration_seconds":len(events)*2,"speech_events":events,
                       "pauses":[]}
        self.bindings = {"slide":1,"trace_sha256":digest(self.trace),
                         "timing_sha256":digest(self.timing),
                         "bindings":[{"frame_index":i,"event_id":e["event_id"],
                                      "phrase_index":0,"phrase_text":e["text"]}
                                     for i,e in enumerate(events)]}

    def compile(self):
        return compile_timeline(self.trace,self.directory,self.timing,self.bindings)

    def test_exact_measured_intervals(self):
        result = self.compile()
        self.assertEqual([(r["start"],r["end"]) for r in result["intervals"]],
                         [(e["start"],e["end"]) for e in self.timing["speech_events"]])
        self.assertFalse(result["source_verified"])
        self.assertFalse(result["auto_approved"])
        self.assertTrue(result["speech_timing_bound"])

    def test_tampered_frame(self):
        (self.directory/"frame_0000.svg").write_text("tampered")
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            self.compile()

    def test_missing_frame_binding(self):
        self.bindings["bindings"].pop()
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            self.compile()

    def test_reordered_steps(self):
        self.bindings["bindings"][0]["frame_index"]=1
        with self.assertRaisesRegex(ValueError,"replay order"):
            self.compile()

    def test_stale_phrase(self):
        self.bindings["bindings"][0]["phrase_text"]="changed"
        with self.assertRaisesRegex(ValueError,"Stale"):
            self.compile()

    def test_pause_overlap(self):
        self.timing["pauses"]=[{"start":0.5,"end":1.5}]
        self.bindings["timing_sha256"]=digest(self.timing)
        with self.assertRaisesRegex(ValueError,"pause-crossing"):
            self.compile()

    def test_duplicate_phrase(self):
        self.bindings["bindings"][1].update(event_id="e0",phrase_index=0,phrase_text="step 0")
        with self.assertRaisesRegex(ValueError,"duplicate speech"):
            self.compile()

    def test_stale_timing_hash(self):
        self.timing["duration_seconds"]+=1
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            self.compile()
