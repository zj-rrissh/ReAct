# 阶段 5 完成报告

**日期**: 2026-05-06
**阶段**: 阶段 5 - 规划能力
**状态**: 核心功能已完成

---

## 1. 阶段目标

根据设计文档，阶段 5 的核心目标是让 Agent 能处理需要多步骤规划的复杂任务：

- **任务分解**：将复杂问题拆分为可执行的子任务，识别依赖关系，确定执行顺序
- **进度跟踪**：记录已完成的步骤，标记当前执行位置，处理部分失败的情况
- **动态调整**：根据执行结果调整后续计划，失败时尝试替代方案，发现新信息时更新计划
- **DAG 调度**：基于依赖图的拓扑排序调度，支持并行执行无依赖子任务
- **回溯机制**：记录决策点，失败时尝试其他路径，记录已尝试路径避免重复

---

## 2. 实际完成情况

### 2.1 PlanGraph 增强

| 组件 | 状态 | 文件位置 | 功能描述 |
|------|------|----------|----------|
| TaskNode.feedback | ✅ 已实现 | `plan_graph.py:10` | 失败反馈字段 |
| mark_running/done/failed | ✅ 已实现 | `plan_graph.py:30-40` | 状态管理方法 |
| get_node/get_nodes_by_status | ✅ 已实现 | `plan_graph.py:44-56` | 节点查询方法 |
| get_failed/done/pending_nodes | ✅ 已实现 | `plan_graph.py:58-66` | 按状态筛选便捷方法 |
| progress_summary() | ✅ 已实现 | `plan_graph.py:80-91` | 人类可读的进度摘要（x/y 完成，状态标识） |
| validate() | ✅ 已实现 | `plan_graph.py:95-118` | DFS 循环依赖检测 + 孤立引用校验 |
| merge_replan() | ✅ 已实现 | `plan_graph.py:122-137` | 合并重规划结果（保留已完成节点，替换/新增/删除未完成节点） |
| has_alternatives() | ✅ 已实现 | `plan_graph.py:141-142` | 检查是否有替代路径可用 |
| try_alternative() | ✅ 已实现 | `plan_graph.py:144-153` | 弹出替代描述，重置节点为 pending |

### 2.2 Orchestrator DAG 调度引擎

| 组件 | 状态 | 文件位置 | 功能描述 |
|------|------|----------|----------|
| run_with_graph() | ✅ 已实现 | `orchestrator.py:22-82` | 核心 DAG 调度入口：规划 → 调度循环 → 汇总 |
| run_sequential() | ✅ 保留 | `orchestrator.py:17-18` | 兼容旧接口，委托给 run_with_graph(parallel=False) |
| _execute_node() | ✅ 已实现 | `orchestrator.py:88-116` | 单节点执行-评审-重试循环 |
| _trigger_replan() | ✅ 已实现 | `orchestrator.py:119-127` | 调用 Planner.replan()，合并结果，回退到回溯 |
| _backtrack() | ✅ 已实现 | `orchestrator.py:129-133` | 尝试替代描述回溯失败节点 |
| _run_parallel() | ✅ 已实现 | `orchestrator.py:135-140` | ThreadPoolExecutor 并行执行就绪任务 |
| 死锁检测 | ✅ 已实现 | `orchestrator.py:40-54` | 无就绪任务 + 未全部完成时检测并处理 |
| 进度打印 | ✅ 已实现 | `orchestrator.py:58,74` | 每轮调度后打印进度摘要 |

### 2.3 代码清理

| 组件 | 状态 | 文件位置 | 功能描述 |
|------|------|----------|----------|
| planner.py imports | ✅ 已清理 | `planner.py:1-5` | 移除 `from urllib import response`、`from click import prompt` |
| critic.py imports | ✅ 已清理 | `critic.py:1-3` | 移除 `from click import prompt` |
| plan() 校验 | ✅ 已增强 | `planner.py:56-59` | JSON 解析后校验每个 item 有 id 和 description |
| replan() code fences | ✅ 已修复 | `planner.py:80-82` | 处理 markdown 代码块包裹的 JSON |

### 2.4 CLI 集成

| 组件 | 状态 | 位置 | 功能描述 |
|------|------|------|----------|
| --parallel 参数 | ✅ 已实现 | `ReAct.py:135-139` | 命令行启用并行执行 |
| --max-replans 参数 | ✅ 已实现 | `ReAct.py:140-144` | 配置最大重规划次数（默认 2） |
| run_with_graph 接入 | ✅ 已实现 | `ReAct.py:183-188` | 单次任务和交互模式均已接入新引擎 |

---

## 3. 架构设计

### 3.1 DAG 调度流程

```
用户任务
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│                    Orchestrator                            │
│  run_with_graph(task, max_retries, parallel, max_replans) │
│                                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │ 1. 规划阶段                                       │     │
│  │    Message → Planner.plan(task)                  │     │
│  │    构建 PlanGraph → validate() 校验               │     │
│  │    → 循环检测 / 孤立引用 → 拒绝或执行              │     │
│  └──────────────────┬───────────────────────────────┘     │
│                     │                                      │
│                     ▼                                      │
│  ┌──────────────────────────────────────────────────┐     │
│  │ 2. 调度循环 (while not all_done)                  │     │
│  │                                                    │     │
│  │    ready = graph.get_ready_tasks()                │     │
│  │    (仅返回依赖全部满足的 pending 节点)             │     │
│  │                                                    │     │
│  │    ┌─ 死锁检测 ──────────────────────────────┐    │     │
│  │    │ ready 为空 + not all_done               │    │     │
│  │    │  ├─ 有失败节点 → 回溯尝试               │    │     │
│  │    │  ├─ 回溯失败 → replan 重规划             │    │     │
│  │    │  └─ 超过 max_replans → 终止              │    │     │
│  │    └──────────────────────────────────────────┘    │     │
│  │                                                    │     │
│  │    ┌─ 执行就绪任务 ─────────────────────────┐     │     │
│  │    │ if parallel: ThreadPoolExecutor         │     │     │
│  │    │ else: 串行 for loop                     │     │     │
│  │    │                                         │     │     │
│  │    │ 每个节点:                                │     │     │
│  │    │   Executor.execute → Critic.evaluate    │     │     │
│  │    │   PASS → mark_done                      │     │     │
│  │    │   FAIL → 重试(feedback注入) → mark_failed│     │     │
│  │    └──────────────────────────────────────────┘    │     │
│  │                                                    │     │
│  │    ┌─ 失败处理 ──────────────────────────────┐    │     │
│  │    │ 1. 回溯: try_alternative() 切换替代路径  │     │     │
│  │    │ 2. 重规划: planner.replan() → merge     │     │     │
│  │    └──────────────────────────────────────────┘    │     │
│  │                                                    │     │
│  │    打印 progress_summary()                         │     │
│  └──────────────────────────────────────────────────┘     │
│                     │                                      │
│                     ▼                                      │
│  ┌──────────────────────────────────────────────────┐     │
│  │ 3. 汇总阶段                                       │     │
│  │    [完成] + [失败] 分开展示                        │     │
│  └──────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

### 3.2 DAG 调度示例

```
Planner 生成 5 个子任务:

      [1: 创建 a.txt]        [2: 创建 b.txt]
           │                      │
           ├──────────────────────┤
           ▼                      ▼
      [3: 读取 a.txt]        [4: 读取 b.txt]
           │                      │
           └──────────┬───────────┘
                      ▼
              [5: 创建 c.txt (合并)]

调度序列:
  Round 1: get_ready_tasks() → [1, 2]   (无依赖)
  Round 2: get_ready_tasks() → [3, 4]   (依赖 1,2 已完成)
  Round 3: get_ready_tasks() → [5]      (依赖 3,4 已完成)
  Round 4: all_done() → True → 汇总
```

### 3.3 回溯与重规划决策流程

```
节点执行失败 (attempts 耗尽)
    │
    ├─ has_alternatives(id)?
    │   YES → try_alternative() → 重置为 pending → 下一轮调度
    │
    └─ NO → 所有失败节点都无替代?
            │
            ├─ replan_count < max_replans?
            │   YES → planner.replan() → merge_replan() → 继续调度
            │
            └─ NO → 终止，返回部分结果
```

---

## 4. 与设计文档的符合度

| 设计文档要求 | 符合度 | 说明 |
|-------------|--------|------|
| 任务分解 | 100% | PlannerAgent.plan() 完整实现，输出结构化 JSON 计划 |
| 进度跟踪 | 100% | PlanGraph 实时跟踪节点状态，progress_summary() 展示完成/运行/待定/失败 |
| 动态调整（replan） | 100% | 失败触发 replan → merge_replan 合并，完整闭环 |
| DAG 依赖调度 | 100% | get_ready_tasks() 拓扑排序，每轮只执行依赖满足的节点 |
| 并行执行 | 100% | ThreadPoolExecutor 并行执行无依赖子任务 |
| 回溯机制 | 100% | try_alternative() 替代路径切换，attempts 跟踪 |
| 循环依赖检测 | 100% | DFS 染色法检测，执行前拦截 |
| 5 步以上复杂任务 | 100% | 实测 5 步 DAG 任务正确调度 |

---

## 5. 代码清单（阶段 5 新增/变更）

| 文件 | 变更类型 | 行数变化 | 说明 |
|------|----------|----------|------|
| agents/orchestrator.py | 重写 | 68 → 170 | run_with_graph() DAG 引擎 + 并行/回溯/replan |
| agents/plan_graph.py | 增强 | 50 → 154 | 状态管理/校验/合并/回溯，TaskNode 新增 feedback |
| agents/planner.py | 修复 | -2 +10 | 清理未使用 imports，增强解析鲁棒性 |
| agents/critic.py | 修复 | -1 | 清理未使用 import |
| ReAct.py | 更新 | +15 | --parallel、--max-replans 参数 + 引擎接入 |

---

## 6. 运行示例

### DAG 依赖调度

```bash
python ReAct.py --orchestrate \
  -t "创建3个文件：a.txt内容为hello，b.txt内容为world，c.txt内容为将a.txt和b.txt的内容合并"
```

输出：
```
[Orchestrator] 原始计划: [
  {"id": "1", "description": "使用file_write工具创建文件a.txt...", "depends_on": [], ...},
  {"id": "2", "description": "使用file_write工具创建文件b.txt...", "depends_on": [], ...},
  {"id": "3", "description": "使用file_read工具读取a.txt...", "depends_on": ["1"], ...},
  {"id": "4", "description": "使用file_read工具读取b.txt...", "depends_on": ["2"], ...},
  {"id": "5", "description": "使用file_write工具创建文件c.txt...", "depends_on": ["3","4"], ...}
]
[Orchestrator]
进度: 0/5 完成, 0 运行中, 5 待处理, 0 失败

# Round 1: 执行 task 1,2（无依赖，可并行）
[Orchestrator] 子任务 1 通过
[Orchestrator] 子任务 2 通过

进度: 2/5 完成, 0 运行中, 3 待处理, 0 失败
  [完成] 1: 使用file_write工具创建文件a.txt...
  [完成] 2: 使用file_write工具创建文件b.txt...

# Round 2: 执行 task 3,4（依赖 1,2 已满足）
[Orchestrator] 子任务 3 通过
[Orchestrator] 子任务 4 通过

进度: 4/5 完成, 0 运行中, 1 待处理, 0 失败

# Round 3: 执行 task 5（依赖 3,4 已满足）
[Orchestrator] 子任务 5 通过

进度: 5/5 完成, 0 运行中, 0 待处理, 0 失败

最终结果: 任务完成，所有 5 个子任务通过
```

### 并行执行

```bash
python ReAct.py --orchestrate --parallel \
  -t "搜索 Python 最新特性并搜索 Rust 最新特性，将两者保存到独立文件"
```

---

## 7. 与阶段 4 的改进对比

| 维度 | 阶段 4 | 阶段 5 |
|------|--------|--------|
| 调度方式 | 串行遍历 plan 列表 | DAG get_ready_tasks() 拓扑调度 |
| 失败处理 | 超过 max_retries 后跳过继续 | 回溯替代路径 → replan 重规划 → 终止 |
| 并行执行 | 不支持 | ThreadPoolExecutor 并行 |
| 计划校验 | 无 | DFS 循环检测 + 孤立引用检查 |
| 进度展示 | 无 | progress_summary() 实时状态 |
| 代码质量 | planner/critic 有未使用 imports | 全部清理干净 |
| PlanGraph 使用 | 定义但未使用 | 深度集成，作为调度核心 |

---

## 8. 总结

阶段 5 完成了从"列表迭代式串行编排"到"图驱动智能调度引擎"的跨越。核心变化是将阶段 4 中已定义但未使用的 PlanGraph 深度集成到 Orchestrator，实现了：

- **DAG 调度**：基于拓扑排序的就绪任务识别与调度
- **动态重规划**：失败后自动调用 Planner.replan() 闭环
- **回溯机制**：替代路径自动尝试，避免过早放弃
- **并行执行**：无依赖子任务的并发执行
- **死锁防护**：循环依赖前置检测 + 运行时死锁诊断
- **进度可视化**：每轮调度后实时展示任务状态

所有代码已清理完毕，无未使用 imports，通过实际 5 节点 DAG 任务验证。
