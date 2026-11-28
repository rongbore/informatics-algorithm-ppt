import importlib.util,json,pathlib,shutil,subprocess,tempfile,unittest,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]/"scripts"
def load(name):
 p=ROOT/name;s=importlib.util.spec_from_file_location(name[:-3],p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
azure=load("azure_speech_v30.py")
class AzureProfileTests(unittest.TestCase):
 def test_both_profiles_emit_valid_zh_cn_ssml(self):
  for profile,style in [("coach_excited","sports-commentary-excited"),("coach_balanced","sports-commentary")]:
   xml=azure.build_ssml("注意！路径压缩是关键。",profile);root=ET.fromstring(xml)
   self.assertEqual(root.tag,"{http://www.w3.org/2001/10/synthesis}speak")
   self.assertIn(style,xml);self.assertIn("zh-CN-YunjianNeural",xml)
 def test_ssml_escapes_markup(self):
  ET.fromstring(azure.build_ssml("a < b & c","coach_excited"))
 def test_unknown_profile_rejected(self):
  with self.assertRaises(ValueError):azure.build_ssml("test","other")
 def test_no_secret_fails_closed(self):
  import os
  old=os.environ.pop("AZURE_SPEECH_KEY",None)
  try:
   with self.assertRaisesRegex(RuntimeError,"AZURE_SPEECH_KEY"):azure.synthesize(azure.build_ssml("test","coach_excited"),"/tmp/no.mp3")
  finally:
   if old is not None:os.environ["AZURE_SPEECH_KEY"]=old
@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
class DsuAnimationIntegrationTests(unittest.TestCase):
 def test_all_four_animations_render_1080p_from_34_slide_source(self):
  from pptx import Presentation
  from pptx.util import Inches
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td);ppt=td/"synthetic_dsu.pptx";prs=Presentation()
   for i in range(34):
    sl=prs.slides.add_slide(prs.slide_layouts[6]);box=sl.shapes.add_textbox(Inches(1),Inches(1),Inches(8),Inches(1))
    box.text=["亲戚","修建围栏","食物链","银河英雄传说"][i%4]
   prs.save(ppt);out=td/"animations"
   subprocess.run(["python",str(ROOT/"build_dsu_v30_animations.py"),"--pptx",str(ppt),"--out",str(out)],check=True,capture_output=True)
   manifest=json.loads((out/"animation_manifest.json").read_text(encoding="utf-8"))
   self.assertEqual(len(manifest["animations"]),4)
   for row in manifest["animations"]:
    self.assertEqual(row["resolution"],"1920x1080");self.assertEqual(row["fps"],30)
    self.assertTrue((out/row["file"]).exists())
   self.assertEqual(manifest["animations"][1]["perimeters"],[40,10])
   self.assertEqual(manifest["animations"][2]["accepted"],3)
   self.assertEqual(manifest["animations"][2]["rejected"],3)
   self.assertEqual(manifest["animations"][3]["node_2_offset"],4)
if __name__=="__main__":unittest.main()

class SourceDeckNarrationContractTests(unittest.TestCase):
 def test_all_animation_event_ids_are_unique_and_match_renderer(self):
  prompt=json.loads((ROOT.parent/"prompts"/"dsu_animation_narration_v30.json").read_text(encoding="utf-8"))
  expected={"relatives":[f"dsu_relatives_{i:02d}" for i in range(7)],"fencing":[f"dsu_fence_{i:02d}" for i in range(7)],"food_chain":[f"dsu_food_{i:02d}" for i in range(7)],"galaxy":[f"dsu_galaxy_{i:02d}" for i in range(5)]}
  all_ids=[]
  for animation in prompt["animations"]:
   ids=[event["event_id"] for event in animation["events"]]
   self.assertEqual(ids,expected[animation["animation_id"]])
   all_ids.extend(ids)
  self.assertEqual(len(all_ids),len(set(all_ids)))
 def test_food_chain_examples_match_original_deck_claims(self):
  prompt=json.loads((ROOT.parent/"prompts"/"dsu_animation_narration_v30.json").read_text(encoding="utf-8"))
  food=next(x for x in prompt["animations"] if x["animation_id"]=="food_chain")
  text=" ".join(x["text"] for x in food["events"])
  for fact in ["{1,2,3,5}","{4}","A 吃 B","假话数为零","2、1、4","假话数为一"]:
   self.assertIn(fact,text)
  for invented in ["1 吃 2","2 吃 3","3 吃 1","三句中有三句为假"]:
   self.assertNotIn(invented,text)
 def test_phrase_timing_is_grouped_under_stable_event_ids(self):
  script=(ROOT/"generate_audio_azure_v30.py").read_text(encoding="utf-8")
  self.assertIn("'phrases':event_phrases",script)
  self.assertIn("'speech_events':speech,'phrases':phrase_rows",script)
