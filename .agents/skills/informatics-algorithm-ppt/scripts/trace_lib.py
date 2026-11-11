import json

def make_trace(values, window):
    if not values or not 1 <= window <= len(values):
        raise ValueError('window must be in 1..len(values), values nonempty')
    q=[]; out=[]; events=[]
    def record(action,i,message):
        events.append(dict(step=len(events),action=action,cursor=i,
            windowStart=max(0,i-window+1),queueIndices=q.copy(),output=out.copy(),
            message=message,codeLine=None))
    for i,x in enumerate(values):
        left=max(0,i-window+1)
        while q and q[0]<left:
            old=q.pop(0); record('pop_front',i,f'下标 {old} 已离开窗口，移除队首')
        while q and values[q[-1]]<=x:
            old=q.pop(); record('pop_back',i,f'{values[old]} 不大于新元素 {x}，移除队尾下标 {old}')
        q.append(i); record('push',i,f'加入下标 {i}，值为 {x}')
        if i>=window-1:
            out.append(values[q[0]]); record('emit',i,f'窗口最大值为 {values[q[0]]}')
    return dict(schemaVersion='1.0',algorithm='sliding-window-maximum',
        input=dict(values=values,window=window),expectedOutput=out,events=events)

def brute(values,window):
    return [max(values[i:i+window]) for i in range(len(values)-window+1)]
