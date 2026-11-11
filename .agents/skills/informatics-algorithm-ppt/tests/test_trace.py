import sys,unittest,random,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from trace_lib import make_trace,brute
from validate_trace import validate
class TraceTests(unittest.TestCase):
    def test_demo(self):
        data=json.loads((root/'examples/sliding-window/trace.json').read_text(encoding='utf-8'))
        self.assertTrue(validate(data))
    def test_edge_cases(self):
        for arr,k in [([7],1),([2,2,2],2),([-4,-1,-9],3),([9,8,7,6],1),([1,2,3],3)]:
            self.assertTrue(validate(make_trace(arr,k)))
    def test_random(self):
        rng=random.Random(1234)
        for _ in range(100):
            n=rng.randint(1,20); a=[rng.randint(-10,10) for _ in range(n)]; k=rng.randint(1,n)
            self.assertTrue(validate(make_trace(a,k)))
    def test_reject_corruption(self):
        t=make_trace([1,3,2],2); t['events'][-1]['output']=[999]
        with self.assertRaises(AssertionError): validate(t)
    def test_invalid_input(self):
        with self.assertRaises(ValueError): make_trace([],1)
if __name__=='__main__': unittest.main()
