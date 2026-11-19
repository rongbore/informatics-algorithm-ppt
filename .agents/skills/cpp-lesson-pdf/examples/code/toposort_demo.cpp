#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> g(n + 1); // g[u] 保存从 u 出发的所有有向边
    vector<int> indeg(n + 1, 0);  // indeg[v]：尚未完成的前置要求数

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v); // u 必须排在 v 的前面
        indeg[v]++;
    }

    queue<int> q;
    for (int i = 1; i <= n; i++) {
        if (indeg[i] == 0) q.push(i); // 没有前置任务的点可以先处理
    }

    vector<int> ans;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        ans.push_back(u);
        for (int v : g[u]) {
            // 已处理 u，解除它对每个后继 v 的限制
            if (--indeg[v] == 0) q.push(v);
        }
    }

    if ((int)ans.size() != n) {
        cout << -1 << '\n'; // 仍有顶点无法处理，说明存在有向环
    } else {
        for (int x : ans) cout << x << ' ';
        cout << '\n'; // 输出一个满足全部依赖的排列
    }
    return 0;
}
