from pathlib import Path
import json
from trace_lib import make_trace
root=Path(__file__).resolve().parents[1]
out=root/'examples/sliding-window/trace.json'
out.write_text(json.dumps(make_trace([1,3,-1,-3,5,3,6,7],3),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out)
