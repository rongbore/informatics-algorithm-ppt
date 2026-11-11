#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false); cin.tie(nullptr);
    int n,k; if(!(cin>>n>>k)) return 0;
    vector<int>a(n); for(int &x:a)cin>>x;
    deque<int>q;
    for(int i=0;i<n;i++){
        while(!q.empty() && q.front()<=i-k) q.pop_front(); // 移除过期下标
        while(!q.empty() && a[q.back()]<=a[i]) q.pop_back(); // 维护严格递减
        q.push_back(i);
        if(i>=k-1) cout<<a[q.front()]<<(i==n-1?'\n':' ');
    }
}
