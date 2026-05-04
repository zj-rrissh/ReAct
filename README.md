# ReAct Agent

基于 ReAct (Reasoning + Acting) 模式的智能助理，支持工具调用、自我反思和多后端 LLM。

## 特性

- **ReAct 循环**：Thought → Action → Observation 标准推理链路
- **自我反思**：Actor 执行 + Reviewer 评审 + 失败自动修正
- **多 Agent 编排**：Planner 规划 → Executor 执行 → Critic 评审，串行协作
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
| `--max-retries` | 反思/编排最大重试次数 | 2 |
| `-w, --workspace` | 文件读写工具的工作区目录 | `./workspace` |
| `--max-steps` | 单次任务最大步数 | 20 |

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
│   ├── reviewer.py           # Reviewer 评审 Agent（反思模式用）
│   ├── planner.py            # Planner 规划 Agent（编排模式用）
│   ├── executor.py           # Executor 执行 Agent（编排模式用）
│   ├── critic.py             # Critic 评审 Agent（编排模式用）
│   └── orchestrator.py       # Orchestrator 编排器：串行协调多 Agent
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
│   ├── short_term.py         # 短期记忆（占位，逻辑在 BaseAgent 中）
│   ├── mid_term.py           # 中期记忆（占位，会话摘要待实现）
│   └── long_term.py          # 长期记忆（占位，逻辑在 store.py 中）
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

### 多 Agent 编排模式

```
用户任务 ──▶ Planner 分解任务为子任务列表
                    │
                    ▼
          ┌─────────────────────────────────┐
          │  Orchestrator 串行协调           │
          │                                 │
          │  对每个子任务:                    │
          │    ├─ Executor 执行子任务         │
          │    ├─ Critic 评审执行结果          │
          │    ├─ ✅ PASS → 记录结果, 继续     │
          │    └─ ❌ FAIL → 注入反馈 → 重试    │
          │                                 │
          │  汇总所有子任务结果 → 最终输出      │
          └─────────────────────────────────┘
```

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
| 阶段 5 | 规划能力增强（任务分解优化、进度跟踪、动态调整、并行执行） | 📋 计划中 |
