#!/usr/bin/env python3
"""ReAct Agent 主入口 —— 基于 ReAct (Reasoning + Acting) 模式的智能助理。

支持 Ollama 本地模型和 DeepSeek API 两种后端，单次任务执行和交互式对话两种模式。
"""

import argparse
import json
import os

from dotenv import load_dotenv
load_dotenv()

from utils.llm_client import LLMClient
from agents.base import BaseAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.critic import CriticAgent
from agents.orchestrator import Orchestrator
from memory.manager import MemoryManager

from tools.base import set_workspace_dir

# 导入所有工具以触发 @register_tool 自动注册
import tools.calculator      # noqa: F401
import tools.search          # noqa: F401
import tools.weather         # noqa: F401
import tools.web_search      # noqa: F401
import tools.wikipedia       # noqa: F401
import tools.file_reader     # noqa: F401
import tools.file_writer     # noqa: F401


DEFAULT_CONFIG_PATH = "config.json"


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """加载 config.json 配置文件。

    Returns:
        dict: {"provider": str, "model": str, "providers": dict}

    Raises:
        FileNotFoundError: config.json 不存在
        ValueError: 配置格式错误或 provider 无效
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"未找到配置文件: {config_path}\n"
            f"请从 config.json.example 复制一份:\n"
            f"  cp config.json.example config.json\n"
            f"然后编辑 config.json 填入你的 API 密钥。"
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"config.json 格式错误，无法解析 JSON: {e}")

    if "provider" not in config:
        raise ValueError(f"缺少必需字段 'provider'（文件: {config_path}）")
    if "providers" not in config:
        raise ValueError(f"缺少必需字段 'providers'（文件: {config_path}）")

    provider = config["provider"]
    if provider not in config["providers"]:
        available = ", ".join(config["providers"].keys())
        raise ValueError(
            f"未知的 provider: {provider}，可用的 provider: {available}（文件: {config_path}）"
        )

    if "model" not in config:
        config["model"] = provider

    return config


def create_openai_compatible_client(
    provider_name: str,
    model_name: str,
    base_url: str,
    api_key: str = "",
    api_key_env: str = "",
) -> LLMClient:
    """创建 OpenAI 兼容 API 的 LLM 客户端。

    Args:
        provider_name: 提供商名称（用于错误提示）
        model_name: 模型名称
        base_url: API 地址
        api_key: config.json 中的 api_key（可为空）
        api_key_env: 环境变量名

    Returns:
        LLMClient 实例

    Raises:
        ValueError: 无法获取 api_key
    """
    # 优先级: 环境变量 > config.json
    resolved_key = ""
    if api_key_env:
        resolved_key = os.getenv(api_key_env, "")
    if not resolved_key and api_key:
        resolved_key = api_key

    if not resolved_key:
        raise ValueError(
            f"[{provider_name}] 未找到 API 密钥。\n"
            f"  方式 1: 在 .env 中设置 {api_key_env}=sk-xxx\n"
            f"  方式 2: 在 config.json 的 providers.{provider_name}.api_key 中填写密钥"
        )

    from openai import OpenAI

    client = OpenAI(api_key=resolved_key, base_url=base_url)

    def adapter(model, prompt):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    return LLMClient(model_name=model_name, adapter=adapter)


def create_ollama_client(model_name: str = "llama3:8b") -> LLMClient:
    """创建基于 Ollama 的 LLM 客户端。"""
    import ollama

    def adapter(model, prompt):
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]

    return LLMClient(model_name=model_name, adapter=adapter)


def create_client(config_path: str = DEFAULT_CONFIG_PATH, provider: str = None, model_name: str = None) -> LLMClient:
    """根据配置创建 LLM 客户端。

    Args:
        config_path: config.json 路径
        provider: 覆盖配置中的 provider（命令行参数）
        model_name: 覆盖配置中的 model（命令行参数）

    Returns:
        LLMClient 实例
    """
    config = load_config(config_path)

    # 命令行参数覆盖 config
    provider = provider or config["provider"]
    model_name = model_name or config.get("model", provider)

    if provider not in config["providers"]:
        available = ", ".join(config["providers"].keys())
        raise ValueError(f"未知的 provider: {provider}，可用: {available}")

    provider_config = config["providers"][provider]
    provider_type = provider_config.get("type", "")

    if provider_type == "openai_compatible":
        return create_openai_compatible_client(
            provider_name=provider,
            model_name=model_name,
            base_url=provider_config.get("base_url", ""),
            api_key=provider_config.get("api_key", ""),
            api_key_env=provider_config.get("api_key_env", ""),
        )
    elif provider_type == "ollama":
        ollama_model = model_name or provider_config.get("model", "llama3:8b")
        return create_ollama_client(ollama_model)
    else:
        raise ValueError(
            f"未知的 provider type: {provider_type}，"
            f"provider '{provider}' 需在 config.json 中设置 type 字段（openai_compatible 或 ollama）"
        )


def create_orchestrator(model_name: str, llm_client: LLMClient):
    """创建多 Agent 编排组件（Planner + Executor + Critic + Orchestrator）。"""
    memory_mgr = MemoryManager()
    planner = PlannerAgent(model_name=model_name, llm_client=llm_client, memory_manager=memory_mgr)
    executor = ExecutorAgent(model_name=model_name, llm_client=llm_client, memory_manager=memory_mgr)
    critic = CriticAgent(model_name=model_name, llm_client=llm_client, memory_manager=memory_mgr)
    orch = Orchestrator(planner, executor, critic, memory_mgr)
    return orch, memory_mgr


def main():
    parser = argparse.ArgumentParser(
        description="ReAct Agent - 基于 Reasoning + Acting 模式的智能助理"
    )
    parser.add_argument(
        "-t", "--task",
        type=str,
        default=None,
        help="要执行的任务（不指定则进入交互模式）"
    )
    parser.add_argument(
        "-p", "--provider",
        type=str,
        default="deepseek",
        choices=["ollama", "deepseek"],
        help="LLM 后端: ollama（本地）或 deepseek（API）"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=None,
        help="模型名称（deepseek 默认: deepseek-chat，ollama 默认: llama3:8b）"
    )
    parser.add_argument(
        "-r", "--reflect",
        action="store_true",
        help="启用自我反思模式（Actor + Reviewer 协作）"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="反思模式下的最大重试次数（默认: 2）"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="单次任务的最大执行步数（默认: 20）"
    )
    parser.add_argument(
        "--orchestrate",
        action="store_true",
        help="启用多 Agent 编排模式（Planner + Executor + Critic 协作）"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="编排模式下允许并行执行无依赖的子任务"
    )
    parser.add_argument(
        "--max-replans",
        type=int,
        default=2,
        help="编排模式下的最大重规划次数（默认: 2）"
    )
    parser.add_argument(
        "-w", "--workspace",
        type=str,
        default="./workspace",
        help="工作区目录（文件读写工具的根目录，默认: ./workspace）"
    )
    args = parser.parse_args()

    # 配置工作区目录
    set_workspace_dir(args.workspace)

    # 根据 provider 自动选择默认模型
    if args.model is None:
        args.model = "deepseek-chat" if args.provider == "deepseek" else "llama3:8b"

    print(f"[ReAct] 后端: {args.provider}, 模型: {args.model}")
    client = create_client(provider=args.provider, model_name=args.model)

    if args.orchestrate:
        orchestrator, memory_mgr = create_orchestrator(args.model, client)
        agent = BaseAgent(model_name=args.model, llm_client=client, memory_manager=memory_mgr, name="main_agent")
    else:
        agent = BaseAgent(model_name=args.model, llm_client=client, name="main_agent")
        orchestrator = None

    if args.task:
        run_single_task(agent, args, orchestrator)
    else:
        run_interactive(agent, args, client, orchestrator)

    agent.memory.compress(max_items=50)


def run_single_task(agent: BaseAgent, args, orchestrator=None):
    """执行单次任务。"""
    if orchestrator:
        print("[ReAct] 多 Agent 编排模式已启用 (Phase 5: DAG 调度)")
        result = orchestrator.run_with_graph(
            args.task,
            max_retries=args.max_retries,
            parallel=args.parallel,
            max_replans=args.max_replans,
        )
    elif args.reflect:
        print(f"[ReAct] 自我反思模式已启用，最大重试: {args.max_retries}")
        result = agent.run_with_reflection(args.task, max_retries=args.max_retries, max_steps=args.max_steps)
    else:
        result = agent.run(args.task, max_steps=args.max_steps)

    print(f"\n{'='*60}")
    print("最终结果:")
    print(result)


def run_interactive(agent: BaseAgent, args, llm_client: LLMClient, orchestrator=None):
    """交互式对话模式。支持 /orch 动态切换编排模式。"""
    state = {
        "reflect_on": args.reflect,
        "orchestrate_on": orchestrator is not None,
        "orchestrator": orchestrator,
        "llm_client": llm_client,
        "model_name": args.model,
        "agent": agent,
        "max_retries": args.max_retries,
        "max_steps": args.max_steps,
        "parallel": args.parallel,
        "max_replans": args.max_replans,
    }

    def mode_label():
        if state["orchestrate_on"]:
            return "编排"
        elif state["reflect_on"]:
            return "反思"
        return "标准"

    print("[ReAct] 进入交互模式，输入 /help 查看可用命令。")
    print(f"[ReAct] 模式: {mode_label()}")

    while True:
        prompt = f"\n[{mode_label()}] > "
        try:
            task = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[ReAct] 再见。")
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit"):
            print("[ReAct] 再见。")
            break

        # 内置命令
        if task.startswith("/"):
            handle_command(task, state)
            continue

        if state["orchestrate_on"]:
            result = state["orchestrator"].run_with_graph(
                task,
                max_retries=state["max_retries"],
                parallel=state.get("parallel", False),
                max_replans=state.get("max_replans", 2),
            )
        elif state["reflect_on"]:
            print("[ReAct] 反思模式执行中...")
            result = state["agent"].run_with_reflection(task, max_retries=state["max_retries"], max_steps=state["max_steps"])
        else:
            result = state["agent"].run(task, max_steps=state["max_steps"])

        print(f"\n结果: {result}")


def handle_command(cmd: str, state: dict):
    """处理内置命令，直接修改 state dict。"""
    parts = cmd.lower().split()
    cmd_name = parts[0]

    if cmd_name in ("/reflect", "/r"):
        if state["orchestrate_on"]:
            print("[ReAct] 编排模式已开启，请先关闭编排模式（/orch off）再切换反思模式。")
            return
        if len(parts) > 1 and parts[1] in ("on", "1", "true", "yes"):
            state["reflect_on"] = True
        elif len(parts) > 1 and parts[1] in ("off", "0", "false", "no"):
            state["reflect_on"] = False
        else:
            state["reflect_on"] = not state["reflect_on"]
        print(f"[ReAct] 反思模式已: {'🟢 开启' if state['reflect_on'] else '⚫ 关闭'}")

    elif cmd_name in ("/orch", "/orchestrate"):
        if len(parts) > 1 and parts[1] in ("on", "1", "true", "yes"):
            if not state["orchestrate_on"]:
                state["orchestrator"], _ = create_orchestrator(state["model_name"], state["llm_client"])
                state["orchestrate_on"] = True
        elif len(parts) > 1 and parts[1] in ("off", "0", "false", "no"):
            if state["orchestrate_on"]:
                state["orchestrator"] = None
                state["orchestrate_on"] = False
        else:
            # 无参数时切换
            if state["orchestrate_on"]:
                state["orchestrator"] = None
                state["orchestrate_on"] = False
            else:
                state["orchestrator"], _ = create_orchestrator(state["model_name"], state["llm_client"])
                state["orchestrate_on"] = True
        if state["orchestrate_on"]:
            state["reflect_on"] = False
        print(f"[ReAct] 编排模式已: {'🟢 开启' if state['orchestrate_on'] else '⚫ 关闭'}")

    elif cmd_name in ("/parallel", "/pl"):
        if len(parts) > 1 and parts[1] in ("on", "1", "true", "yes"):
            state["parallel"] = True
        elif len(parts) > 1 and parts[1] in ("off", "0", "false", "no"):
            state["parallel"] = False
        else:
            state["parallel"] = not state["parallel"]
        print(f"[ReAct] 并行执行已: {'🟢 开启' if state['parallel'] else '⚫ 关闭'}")

    elif cmd_name in ("/replans", "/rp"):
        if len(parts) > 1 and parts[1].isdigit():
            state["max_replans"] = int(parts[1])
            print(f"[ReAct] 最大重规划次数已设为: {state['max_replans']}")
        else:
            print(f"[ReAct] 当前最大重规划次数: {state['max_replans']}")

    elif cmd_name in ("/help", "/h", "/?"):
        print("""
可用命令:
  /orch, /orchestrate       切换多 Agent 编排模式
  /orch on/off              直接设置编排模式
  /reflect, /r              切换反思模式（开/关）
  /reflect on/off           直接设置反思模式
  /parallel, /pl            切换并行执行（开/关/on/off）
  /replans, /rp [N]         查看/设置最大重规划次数
  /help, /h                 显示此帮助
  exit, quit                退出程序
        """.strip())

    else:
        print(f"未知命令: {cmd_name}，输入 /help 查看可用命令。")


if __name__ == "__main__":
    main()
    
