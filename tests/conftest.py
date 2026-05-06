"""共享 fixtures —— 所有测试文件通过此模块获取 mock 对象和测试数据。"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保项目根目录在 sys.path 中（CI 环境友好）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.llm_client import LLMClient
from memory.manager import MemoryManager
from memory.store import JSONMemoryStore
from agents.message import Message


# ── 工作区与临时目录 ──

@pytest.fixture
def temp_dir():
    """临时目录，测试后自动清理。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def workspace_dir(temp_dir, monkeypatch):
    """设置临时工作区目录，影响 tools.base 的全局配置。"""
    import tools.base
    original = tools.base._workspace_dir
    tools.base.set_workspace_dir(str(temp_dir))
    yield temp_dir
    tools.base.set_workspace_dir(original)


@pytest.fixture
def sample_text_file(workspace_dir):
    """在工作区创建 sample.txt 并写入内容。"""
    path = workspace_dir / "sample.txt"
    path.write_text("Hello ReAct Test", encoding="utf-8")
    return "sample.txt"


# ── LLM Client Mocks ──

@pytest.fixture
def mock_adapter():
    """返回固定字符串的 LLM adapter。"""
    return MagicMock(return_value="Mock LLM response")


@pytest.fixture
def mock_llm_client(mock_adapter):
    """使用 mock adapter 构造的 LLMClient。"""
    return LLMClient(model_name="test-model", adapter=mock_adapter)


@pytest.fixture
def mock_llm_client_with_adapter():
    """返回 (LLMClient, adapter_mock) 元组，方便按测试调整返回值。"""
    adapter = MagicMock(return_value="Mock LLM response")
    client = LLMClient(model_name="test-model", adapter=adapter)
    return client, adapter


# ── Memory Mocks ──

@pytest.fixture
def temp_memory_file(tmp_path):
    """临时记忆文件路径。"""
    return str(tmp_path / "test_memories.json")


@pytest.fixture
def json_memory_store(temp_memory_file):
    """使用临时文件的 JSONMemoryStore。"""
    store = JSONMemoryStore(filepath=temp_memory_file)
    return store


@pytest.fixture
def sample_memory_entries():
    """4 条示例记忆数据。"""
    import time
    now = time.time()
    return [
        {
            "type": "tool_result",
            "content": "工具calculator成功执行, 输入：2+3，输出：5",
            "task": "计算 2+3",
            "tags": ["计算", "calculator"],
            "importance": 0.3,
            "timestamp": now - 86400 * 5,
            "access_count": 2,
            "last_accessed": now - 86400 * 3,
        },
        {
            "type": "reflection",
            "content": "反思记录: 搜索结果不够精确，需要更具体的关键词",
            "task": "搜索量子计算",
            "tags": ["搜索", "量子", "计算"],
            "importance": 0.7,
            "timestamp": now - 86400 * 2,
            "access_count": 5,
            "last_accessed": now - 3600,
        },
        {
            "type": "tool_result",
            "content": "工具web_search成功执行, 输入：天气，输出：晴天",
            "task": "查询天气",
            "tags": ["天气", "web_search"],
            "importance": 0.3,
            "timestamp": now - 86400 * 10,
            "access_count": 1,
            "last_accessed": now - 86400 * 9,
        },
        {
            "type": "user_preference",
            "content": "用户偏好使用中文回答",
            "task": "",
            "tags": ["中文", "偏好"],
            "importance": 0.9,
            "timestamp": now - 3600,
            "access_count": 10,
            "last_accessed": now - 60,
        },
    ]


@pytest.fixture
def populated_store(json_memory_store, sample_memory_entries):
    """预填充了 4 条记忆的 JSONMemoryStore。"""
    for entry in sample_memory_entries:
        json_memory_store.add(entry)
    return json_memory_store


@pytest.fixture
def memory_manager(json_memory_store):
    """使用临时 JSON 存储的 MemoryManager。"""
    return MemoryManager(store=json_memory_store)


@pytest.fixture
def mock_memory_manager():
    """MagicMock 的 MemoryManager —— 默认 retrieve_relevant 返回空列表。"""
    mgr = MagicMock(spec=MemoryManager)
    mgr.retrieve_relevant.return_value = []
    return mgr


# ── 工具注册表清理 ──

@pytest.fixture(autouse=True)
def clean_tool_registry():
    """每个测试前后清理全局 _tool_registry，防止测试间工具注册污染。"""
    import tools.registry as registry
    original = dict(registry._tool_registry)
    registry._tool_registry.clear()
    yield
    registry._tool_registry.clear()
    registry._tool_registry.update(original)


# ── Agent Fixtures ──

class _ConcreteAgent:
    """用于测试 BaseAgent 的具体子类，无需 mock ABC。"""
    from agents.base import BaseAgent as _Base

    class TestAgent(_Base):
        pass


@pytest.fixture
def base_agent(mock_llm_client, mock_memory_manager):
    """BaseAgent 的具体测试子类实例（使用空工具注册表）。"""
    return _ConcreteAgent.TestAgent(
        model_name="test-model",
        llm_client=mock_llm_client,
        tools_registry={},
        memory_manager=mock_memory_manager,
        name="test_agent",
    )


@pytest.fixture
def base_agent_with_tools(mock_llm_client, mock_memory_manager):
    """BaseAgent 实例，注册了 calculator 和 search 两个 mock 工具。"""
    from tools.base import Tool

    class MockCalculator(Tool):
        name = "mock_calc"
        description = "Mock calculator tool"

        def execute(self, input: str) -> str:
            return f"calc_result: {input}"

    class MockSearch(Tool):
        name = "mock_search"
        description = "Mock search tool"

        def execute(self, input: str) -> str:
            return f"search_result: {input}"

    tools_registry = {"mock_calc": MockCalculator, "mock_search": MockSearch}
    agent = _ConcreteAgent.TestAgent(
        model_name="test-model",
        llm_client=mock_llm_client,
        tools_registry=tools_registry,
        memory_manager=mock_memory_manager,
        name="test_agent",
    )
    return agent


@pytest.fixture
def reviewer_agent(mock_llm_client):
    """ReviewerAgent 实例。"""
    from agents.reviewer import ReviewerAgent
    return ReviewerAgent(model_name="test-model", llm_client=mock_llm_client, name="reviewer")


@pytest.fixture
def planner_agent(mock_llm_client):
    """PlannerAgent 实例（空工具注册表）。"""
    from agents.planner import PlannerAgent
    return PlannerAgent(model_name="test-model", llm_client=mock_llm_client, name="planner")


@pytest.fixture
def executor_agent(mock_llm_client):
    """ExecutorAgent 实例（空工具注册表）。"""
    from agents.executor import ExecutorAgent
    return ExecutorAgent(
        model_name="test-model",
        llm_client=mock_llm_client,
        tools_registry={},
        name="executor",
    )


@pytest.fixture
def critic_agent(mock_llm_client):
    """CriticAgent 实例。"""
    from agents.critic import CriticAgent
    return CriticAgent(model_name="test-model", llm_client=mock_llm_client, name="critic")


# ── 示例计划数据 ──

@pytest.fixture
def sample_plan():
    """3 节点示例计划：task1 -> task2 -> task3。"""
    return [
        {"id": "1", "description": "搜索相关数据", "depends_on": [], "assigned_to": "executor"},
        {"id": "2", "description": "分析搜索结果", "depends_on": ["1"], "assigned_to": "executor"},
        {"id": "3", "description": "生成最终报告", "depends_on": ["2"], "assigned_to": "executor"},
    ]


@pytest.fixture
def sample_plan_diamond():
    """菱形依赖计划：1 -> (2, 3) -> 4。"""
    return [
        {"id": "1", "description": "数据收集", "depends_on": [], "assigned_to": "executor"},
        {"id": "2", "description": "数据清洗", "depends_on": ["1"], "assigned_to": "executor"},
        {"id": "3", "description": "数据分析", "depends_on": ["1"], "assigned_to": "executor"},
        {"id": "4", "description": "结果汇总", "depends_on": ["2", "3"], "assigned_to": "executor"},
    ]


# ── PlanGraph Fixture ──

@pytest.fixture
def empty_graph():
    """空 PlanGraph。"""
    from agents.plan_graph import PlanGraph
    return PlanGraph()


@pytest.fixture
def graph_from_plan(sample_plan):
    """从 sample_plan 构建的 PlanGraph。"""
    from agents.plan_graph import PlanGraph
    g = PlanGraph()
    g.from_plan(sample_plan)
    return g


# ── Mock Orchestrator 组件 ──

@pytest.fixture
def mock_planner():
    """MagicMock PlannerAgent。"""
    from agents.planner import PlannerAgent
    return MagicMock(spec=PlannerAgent, name="planner")


@pytest.fixture
def mock_executor():
    """MagicMock ExecutorAgent。"""
    from agents.executor import ExecutorAgent
    return MagicMock(spec=ExecutorAgent, name="executor")


@pytest.fixture
def mock_critic():
    """MagicMock CriticAgent。"""
    from agents.critic import CriticAgent
    return MagicMock(spec=CriticAgent, name="critic")


# ── 外部 API Mock 上下文管理器 ──

@pytest.fixture
def mock_requests_get():
    """Mock requests.get，返回可控的 Mock 响应。"""
    with patch("tools.wikipedia.requests.get") as mock_get:
        yield mock_get


@pytest.fixture
def mock_ddgs():
    """Mock DDGS 类。"""
    with patch("tools.web_search.DDGS") as mock_ddgs_cls:
        yield mock_ddgs_cls


# ── 环境变量 helper ──

@pytest.fixture
def set_deepseek_env(monkeypatch):
    """临时设置 DEEPSEEK_API_KEY 和 DEEPSEEK_BASE_URL。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key-12345")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
