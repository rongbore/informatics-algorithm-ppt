import json,sys
from pathlib import Path
from trace_lib import brute

def validate(trace):
    assert trace['schemaVersion']=='1.0'
    assert trace['algorithm']=='sliding-window-maximum'
    values=trace['input']['values']; k=trace['input']['window']
    assert values and all(type(x) is int for x in values)
    assert type(k) is int and 1<=k<=len(values)
    events=trace['events']; assert events
    q=[]; out=[]; previous_cursor=-1
    for n,e in enumerate(events):
        assert e['step']==n
        assert e['action'] in ('push','pop_front','pop_back','emit')
        i=e['cursor']; left=max(0,i-k+1)
        assert previous_cursor<=i<len(values) and i>=0
        assert e['windowStart']==left
        assert isinstance(e['message'],str) and e['message'].strip()
        assert e['codeLine'] is None or type(e['codeLine']) is int and e['codeLine']>0
        if e['action']=='pop_front':
            assert q and q[0]<left; q.pop(0)
        elif e['action']=='pop_back':
            assert q and values[q[-1]]<=values[i]; q.pop()
        elif e['action']=='push':
            assert (not q or q[0]>=left) and (not q or values[q[-1]]>values[i]); q.append(i)
        else:
            assert i>=k-1 and q and q[0]>=left
            out.append(values[q[0]])
        assert e['queueIndices']==q
        assert e['output']==out
        assert len(q)==len(set(q)) and q==sorted(q)
        assert all(left<=j<=i for j in q)
        assert all(values[a]>values[b] for a,b in zip(q,q[1:]))
        previous_cursor=i
    assert previous_cursor==len(values)-1
    assert out==brute(values,k)==trace['expectedOutput']
    return True

if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'examples/sliding-window/trace.json'
    validate(json.loads(path.read_text(encoding='utf-8')))
    print('PASS:',path)
