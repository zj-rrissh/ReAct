# ReAct Agent

基于 ReAct (Reasoning + Acting) 模式的智能助理，支持工具调用、自我反思和多后端 LLM。

## 特性

- **ReAct 循环**：Thought → Action → Observation 标准推理链路
- **自我反思**：Actor 执行 + Reviewer 评审 + 失败自动修正
- **多 Agent 编排**：Planner 规划 → Executor 执行 → Critic 评审
- **DAG 调度引擎**：基于依赖图的拓扑排序调度，支持并行执行和动态重规划
- **统一消息通信**：`Message` 数据类，规范化 Agent 间通信（sender/receiver/payload）
- **长期记忆**：工具经验积累、反思教训记录、关键词检索、自动压缩
- **双后端**：DeepSeek API / Ollama 本地模型，一键切换
- **7 个内置工具**：计算器、网页搜索、维基百科、文件读写、天气
- **插件式工具架构**：`@register_tool` 装饰器零侵入注册新工具
- **三种运行模式**：标准 ReAct / 反思模式 / 多 Agent 编排

## 快速开始

### 1. 安装依赖

```bash
pip install python-dotenv openai
# 如使用 Ollama 本地模型还需：
pip install ollama
# 网页搜索工具依赖：
pip install duckduckgo-search
```

### 2. 配置 API Key

编辑 `.env` 文件，填入你的 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 运行

```bash
# DeepSeek API（默认）
python ReAct.py -t "找出深度学习的定义并给出一个简单例子"

# 启用反思模式
python ReAct.py -t "计算 (15+23)*2 的结果" -r

# 启用多 Agent 编排模式
python ReAct.py -t "搜索量子计算最新进展，写成报告并保存到文件" --orchestrate

# 编排模式 + 并行执行
python ReAct.py -t "创建3个文件并合并内容" --orchestrate --parallel

# 交互模式
python ReAct.py
```

## 使用方式

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-t, --task` | 要执行的任务 | 无（进入交互模式） |
| `-p, --provider` | LLM 后端：`deepseek` 或 `ollama` | `deepseek` |
| `-m, --model` | 模型名称 | deepseek: `deepseek-chat` / ollama: `llama3:8b` |
| `-r, --reflect` | 启用自我反思模式 | 关闭 |
| `--orchestrate` | 启用多 Agent 编排模式（Planner + Executor + Critic） | 关闭 |
| `--parallel` | 编排模式下允许并行执行无依赖的子任务 | 关闭 |
| `--max-retries` | 反思/编排最大重试次数 | 2 |
| `--max-replans` | 编排模式下最大重规划次数 | 2 |
| `--max-steps` | 单次任务最大步数 | 20 |
| `-w, --workspace` | 文件读写工具的工作区目录 | `./workspace` |

### 交互模式命令

| 命令 | 说明 |
|------|------|
| `/orch` | 切换多 Agent 编排模式开关 |
| `/orch on/off` | 直接设置编排模式 |
| `/reflect` | 切换反思模式开关 |
| `/reflect on/off` | 直接设置反思模式 |
| `/help` | 查看帮助 |
| `exit` / `quit` | 退出 |

### 使用 Ollama 本地模型

```bash
# 确保 Ollama 已安装并拉取了模型
ollama pull llama3:8b

# 切换为 Ollama 后端
python ReAct.py -p ollama -m "llama3:8b" -t "今天天气怎么样？"
```

## 项目结构

```
ReAct/
├── ReAct.py                  # 主入口
├── ReAct01.py                # 早期独立原型（不依赖框架）
├── .env                      # API Key 配置（不提交）
├── .gitignore
├── agents/
│   ├── base.py               # Agent 基类：ReAct 循环 + 反思循环
│   ├── message.py            # Message 数据类：统一 Agent 间通信
│   ├── plan_graph.py         # PlanGraph + TaskNode：依赖图调度数据结构
│   ├── reviewer.py           # Reviewer 评审 Agent（反思模式用）
│   ├── planner.py            # Planner 规划 Agent（编排模式用）
│   ├── executor.py           # Executor 执行 Agent（编排模式用）
│   ├── critic.py             # Critic 评审 Agent（编排模式用）
│   └── orchestrator.py       # Orchestrator：DAG 调度引擎 + 并行 + 回溯
├── tools/
│   ├── base.py               # Tool 抽象基类
│   ├── registry.py           # @register_tool 装饰器注册表
│   ├── calculator.py         # 计算器
│   ├── web_search.py         # 网页搜索（DuckDuckGo）
│   ├── wikipedia.py          # 维基百科查询
│   ├── file_reader.py        # 文件读取（限工作区目录）
│   ├── file_writer.py        # 文件写入（限工作区目录）
│   ├── search.py             # 搜索（模拟）
│   └── weather.py            # 天气（模拟）
├── utils/
│   └── llm_client.py         # LLM 客户端适配器
├── memory/                   # 记忆模块
│   ├── store.py              # MemoryStore 抽象基类 + JSON 持久化
│   ├── manager.py            # MemoryManager 写入/检索/压缩
│   ├── memories.json         # 长期记忆数据文件
│   ├── short_term.py         # 短期记忆（占位）
│   ├── mid_term.py           # 中期记忆（占位）
│   └── long_term.py          # 长期记忆（占位）
├── workspace/                # 文件操作安全沙箱
├── docs/                     # 阶段完成报告
└── README.md
```

## 执行流程

### 标准 ReAct 模式

```
用户任务 ──▶ 构建 System Prompt（含工具描述）
                    │
                    ▼
          ┌─────────────────────┐
          │   ReAct 循环 (≤20步) │
          │                     │
          │  LLM 输出            │
          │    │                │
          │    ├─ Action → 执行工具 → Observation → 继续
          │    │                │
          │    └─ Final Answer → 返回结果
          └─────────────────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │  Reviewer 评审（可选）│
          │                     │
          │  ✅ PASS → 返回结果   │
          │  ❌ FAIL → 注入反馈 → 重试
          └─────────────────────┘
```

### 多 Agent 编排模式（DAG 调度）

```
用户任务 ──▶ Planner 分解任务 → PlanGraph 构建依赖图
                    │
                    ▼
          ┌──────────────────────────────────────────┐
          │  Orchestrator DAG 调度循环                │
          │                                          │
          │  while not all_done:                     │
          │    ready = get_ready_tasks()             │
          │    (仅返回依赖全部满足的节点)              │
          │                                          │
          │    if parallel:                          │
          │      ThreadPoolExecutor 并行执行 ready    │
          │    else:                                 │
          │      串行执行 ready                       │
          │                                          │
          │    每个节点:                              │
          │      Executor 执行 → Critic 评审          │
          │      ✅ PASS → mark_done, 解锁后继节点    │
          │      ❌ FAIL → 重试 → 回溯 → replan       │
          │                                          │
          │    死锁检测: 无就绪 + 未完成 → 处理       │
          └──────────────────────────────────────────┘
                    │
                    ▼
              汇总结果输出
```

编排模式的核心改进：不再按 Planner 返回的列表顺序串行执行，而是基于 `PlanGraph.get_ready_tasks()` 按依赖拓扑顺序调度——每轮只执行依赖已全部满足的节点，天然支持无依赖节点的并行执行。失败时自动尝试替代路径回溯，仍失败则触发 Planner 重规划。

所有 Agent 间通信均通过 `Message` 数据类完成（type/sender/receiver/payload）。

## 添加新工具

```python
from tools.base import Tool
from tools.registry import register_tool

@register_tool(name="my_tool")
class MyTool(Tool):
    name = "my_tool"
    description = "工具描述，模型会根据此描述决定何时调用"

    def execute(self, input: str) -> str:
        # 实现工具逻辑
        return f"结果: {input}"
```

将文件放入 `tools/` 目录，在 `ReAct.py` 中加一行 `import tools.my_tool` 即可。

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| 阶段 0 | 基础设施（Tool 基类、注册表、Agent 基类） | ✅ 完成 |
| 阶段 1 | 更多工具（web_search、wikipedia、file_read/write） | ✅ 完成 |
| 阶段 2 | 自我反思（Reviewer、反思循环、双后端） | ✅ 完成 |
| 阶段 3 | 长期记忆（JSON 持久化、检索、压缩） | ✅ 完成 |
| 阶段 4 | 多模型协作（Message 通信、Planner/Executor/Critic/Orchestrator） | ✅ 完成 |
| 阶段 5 | 规划能力（DAG 调度、动态重规划、回溯、并行执行） | ✅ 完成 |
