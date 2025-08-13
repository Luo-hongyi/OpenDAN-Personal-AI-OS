### Compute Node Scheduler 设计方案（三步流程）

本文档描述调度器在当前架构下的目标、三步流程与评分策略，结合已实现组件（节点池与过滤器），为后续实现“评分 + 加权随机选择”提供清晰边界与参数规范。

### 目标与范围

- 已实现：
  - NodePool（池管理与路由）：根据任务优先级将任务路由到 `high`/`low` 等池，并维护池内节点成员关系与查询。
  - NodeFilter（高性能过滤）：基于 `task_type`、`model_in` 的 O(1) 级别索引过滤，返回候选节点 ID 集合。
- 待实现：
  - Scorer & Selector（评分与加权随机选择）：对候选节点按负载、价格、能力匹配度打分，按得分进行加权随机选择最终节点。

### 三步流程

1) 选定池（Pool Routing）
- 输入：`ComputeTask.priority`（"high"/"low"）
- 输出：池标识（如 `high` 或 `low`）
- 规则建议：
  - 用户对话类低延迟任务 → `high` 池
  - 后台类高容忍度任务 → `low` 池
  - 默认兜底 → `low`，可由调用方显式覆盖

2) 过滤节点（Fast Filtering）
- 输入：池内节点集合、`CandidateQuery(task_type, model_in)` 或由任务自动构建的查询
- 过程：
  - 基于 `NodeFilter` 的倒排索引（task_type、model），对池内节点做交集过滤
  - 复杂度：集合运算，近似 O(1) 到 O(n_small)（n_small 为池内候选规模）
- 输出：满足功能约束的候选节点 ID 集合

3) 评分与加权随机选择（Score & Weighted Random in Top-K）
- 输入：候选节点 ID 集合，节点运行时指标与静态属性
- 过程：
  - 对每个候选节点计算综合得分 `Score ∈ [0,1]`
  - 按得分权重进行随机选择
- 输出：被选中的目标节点

### 评分模型

综合得分由三部分组成：负载（Load）、价格（Price）、能力匹配度（Ability Fit）。

- LoadScore（越空闲越高）：
  - 输入：`capacity_concurrent`、`in_flight_task_count`、`pending_task_total_runtime_ms`（可选）
  - 简化计算：
    - `util_concurrency = in_flight_task_count / max(1, capacity_concurrent)`，截断到 [0,1]
    - 可选排队压力：`queue_pressure = pending_task_total_runtime_ms / window_ms`（window_ms 经验值，如 30_000）
    - `pressure = util_concurrency + β * queue_pressure`，β ∈ [0,1]
    - `LoadScore = 1 / (1 + pressure)` 或近似 `LoadScore = 1 - clamp(pressure, 0, 1)`

- PriceScore（越便宜越高）：
  - 输入：`price_per_token`
  - 归一化：在候选集合内做 min-max 标准化
    - 设 `p_min = min(price)`, `p_max = max(price)`
    - `PriceScore = (p_max - price) / max(ε, p_max - p_min)`（ε 防止除零）

- AbilityScore（任务难度与节点能力的适配）：
  - 输入：`task.difficulty_level ∈ {1..5}`，`node.ability_level ∈ {1..5}`
  - 计算：
    - 若 `node.ability ≥ task.difficulty`：`AbilityScore = 1.0`
    - 否则设差值 `d = task.difficulty - node.ability`，`AbilityScore = 1 / (1 + d)`（差越大分越低）

- 综合得分：
  - `Score = w_load * LoadScore + w_price * PriceScore + w_ability * AbilityScore`
  - 权重建议（可按池调整）：
    - high 池：`w_load=0.5, w_ability=0.4, w_price=0.1`
    - low 池：`w_load=0.3, w_ability=0.2, w_price=0.5`

### 选择策略（Top-K + 加权随机）

- 排序取 Top-K：按 `Score` 降序，取前 K 个（K 默认为 8 或 16，可配置）
- 加权随机：在 Top-K 内按 `prob_i ∝ (Score_i)^γ` 进行随机抽样（γ 为温度/锐度，默认 1.0）
- 兜底策略：
  - 候选为空：回退到该池的全部节点或放宽过滤条件
  - Score 全为 0：在 Top-K 内做均匀随机

### 数据与接口要求

- 节点需暴露或可推导：
  - `ability_level`（1..5）
  - `price_per_token`
  - `capacity_concurrent`
  - `in_flight_task_count`
  - `pending_task_total_runtime_ms`（可选）
- 任务需明确：
  - `priority`（"high"/"low"）
  - `task_type`、`model_name`（可选）
  - `difficulty_level`（1..5；由标签 switch/outline/plan/reason/code 映射而来，可在 Kernel 层完成）

### 复杂度与性能

- 选池：O(1)
- 过滤：集合交集，近似 O(1)~O(n_pool)
- 评分：O(n_cand)
- Top-K：O(n_cand log K) 或采用线性选择近似 O(n_cand)
- 加权采样：O(K)

### 与 Kernel 的集成关系

在 `ComputeKernel` 的调度路径中：
1) `pool = node_pool.route_pool(task)`
2) `pool_nodes = node_pool.get_pool_nodes(pool)`（或先取 ID 集合）
3) `cand_ids = node_filter.filter_node_ids(task=task)` 与 `pool_nodes` 做交集
4) 对 `cand_ids` 进行评分与选择，得到最终节点
5) 下发执行，更新节点运行时指标（异步或定期刷新）

### 可配置与扩展点

- 权重、K、γ、β、window_ms 通过配置文件或环境变量调整
- 指标扩展：失败率、历史 P50/P95 延迟、冷却时间、区域偏好等
- 评分缓存：在高并发下可对静态项（价格、能力）做缓存，对动态项（负载）限频刷新

### 参考伪代码

```python
def schedule(task):
    pool = node_pool.route_pool(task)
    pool_ids = node_pool.list_ids_by_pool(pool)  # 或由 get_pool_nodes(pool) 推导
    cand_ids = node_filter.filter_node_ids(task=task)
    cand_ids &= pool_ids
    if not cand_ids:
        cand_ids = pool_ids  # 放宽为池内全量

    scored = []
    for nid in cand_ids:
        node = node_index[nid]
        load_score = compute_load_score(node)
        price_score = compute_price_score(node, cand_ids)
        ability_score = compute_ability_score(task, node)
        w = get_weights_by_pool(pool)
        score = w.load * load_score + w.price * price_score + w.ability * ability_score
        scored.append((nid, score))

    topk = take_top_k(scored, K)
    chosen = weighted_random(topk, gamma=1.0)
    return chosen
```

以上方案确保：
- 高优先级任务优先路由与调度
- 过滤高效（O(1)），评分线性可扩展
- 价格、负载、能力匹配度可按业务权重灵活调参


