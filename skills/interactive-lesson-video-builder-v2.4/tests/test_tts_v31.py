import importlib.util, json, os, pathlib, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]/"scripts"
def load(name):
 spec=importlib.util.spec_from_file_location(name[:-3],ROOT/name);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
tencent=load("tencent_tts_v31.py")
generator=load("generate_audio_v31.py")
class TencentFreeTierGuardTests(unittest.TestCase):
 def setUp(self):
  self.old={k:os.environ.get(k) for k in ["TENCENT_TTS_ALLOW_FREE_TIER","TENCENT_TTS_POSTPAID_DISABLED","TENCENTCLOUD_SECRET_ID","TENCENTCLOUD_SECRET_KEY","TENCENT_TTS_FREE_BUDGET_CHARS","TENCENT_TTS_BUDGET_STATE"]}
  self.tmp=tempfile.TemporaryDirectory()
  os.environ["TENCENT_TTS_BUDGET_STATE"]=str(pathlib.Path(self.tmp.name)/"ledger.json")
 def tearDown(self):
  for k,v in self.old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.tmp.cleanup()
 def test_cloud_disabled_by_default(self):
  for k in ["TENCENT_TTS_ALLOW_FREE_TIER","TENCENT_TTS_POSTPAID_DISABLED","TENCENTCLOUD_SECRET_ID","TENCENTCLOUD_SECRET_KEY","TENCENT_TTS_FREE_BUDGET_CHARS"]:os.environ.pop(k,None)
  ok,reason=tencent.free_tier_ready();self.assertFalse(ok);self.assertIn("TENCENT_TTS_ALLOW_FREE_TIER",reason)
 def test_missing_budget_blocks_cloud(self):
  os.environ.update({"TENCENT_TTS_ALLOW_FREE_TIER":"true","TENCENT_TTS_POSTPAID_DISABLED":"true","TENCENTCLOUD_SECRET_ID":"x","TENCENTCLOUD_SECRET_KEY":"y","TENCENT_TTS_FREE_BUDGET_CHARS":"0"})
  self.assertFalse(tencent.free_tier_ready()[0])
 def test_budget_reservations_never_exceed_cap(self):
  os.environ.update({"TENCENT_TTS_FREE_BUDGET_CHARS":"100"})
  self.assertEqual(tencent.reserve_free_chars(60)["remaining_chars"],40)
  with self.assertRaisesRegex(RuntimeError,"exceed configured cap"):tencent.reserve_free_chars(41)
 def test_budget_is_persistent_across_runs(self):
  os.environ["TENCENT_TTS_FREE_BUDGET_CHARS"]="100"
  tencent.reserve_free_chars(70)
  self.assertEqual(tencent.budget_status()["remaining_configured_chars"],30)
 def test_no_refund_after_uncertain_failure_policy(self):
  os.environ["TENCENT_TTS_FREE_BUDGET_CHARS"]="100"
  tencent.reserve_free_chars(20)
  self.assertEqual(tencent.budget_status()["reserved_chars"],20)
class PhraseSplitTests(unittest.TestCase):
 def test_tencent_text_chunks_never_exceed_140_characters(self):
  phrases=generator.split_phrases(("并查集路径压缩算法。"*100))
  self.assertTrue(all(len(x)<=140 for x in phrases))
 def test_short_text_preserved(self):
  self.assertEqual(generator.split_phrases("并查集。"),["并查集。"])
if __name__=="__main__":unittest.main()
