#!/usr/bin/env python3
"""ReAct Agent 主入口 —— 基于 ReAct (Reasoning + Acting) 模式的智能助理。

支持 Ollama 本地模型和 DeepSeek API 两种后端，单次任务执行和交互式对话两种模式。
"""

import argparse
import os

from dotenv import load_dotenv
load_dotenv()

from utils.llm_client import LLMClient
from agents.base import BaseAgent

# 导入所有工具以触发 @register_tool 自动注册
import tools.calculator      # noqa: F401
import tools.search          # noqa: F401
import tools.weather         # noqa: F401
import tools.web_search      # noqa: F401
import tools.wikipedia       # noqa: F401
import tools.file_reader     # noqa: F401
import tools.file_writer     # noqa: F401


def create_deepseek_client(model_name: str = "deepseek-chat") -> LLMClient:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    if not api_key:
        raise ValueError(
            "未设置 DEEPSEEK_API_KEY，请在 .env 文件中配置或设置环境变量。\n"
            "  示例: DEEPSEEK_API_KEY=sk-xxxxxxxx"
        )

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

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


def create_client(provider: str, model_name: str) -> LLMClient:
    if provider == "deepseek":
        return create_deepseek_client(model_name)
    elif provider == "ollama":
        return create_ollama_client(model_name)
    else:
        raise ValueError(f"未知的 provider: {provider}，可选: ollama, deepseek")


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
    args = parser.parse_args()

    # 根据 provider 自动选择默认模型
    if args.model is None:
        args.model = "deepseek-chat" if args.provider == "deepseek" else "llama3:8b"

    print(f"[ReAct] 后端: {args.provider}, 模型: {args.model}")
    client = create_client(args.provider, args.model)
    agent = BaseAgent(model_name=args.model, llm_client=client)

    if args.task:
        run_single_task(agent, args)
    else:
        run_interactive(agent, args)


def run_single_task(agent: BaseAgent, args):
    """执行单次任务。"""
    if args.reflect:
        print(f"[ReAct] 自我反思模式已启用，最大重试: {args.max_retries}")
        result = agent.run_with_reflection(args.task, max_retries=args.max_retries, max_steps=args.max_steps)
    else:
        result = agent.run(args.task, max_steps=args.max_steps)

    print(f"\n{'='*60}")
    print("最终结果:")
    print(result)


def run_interactive(agent: BaseAgent, args):
    """交互式对话模式。"""
    reflect_on = args.reflect
    print("[ReAct] 进入交互模式，输入 /help 查看可用命令。")
    print(f"[ReAct] 反思模式: {'🟢 开启' if reflect_on else '⚫ 关闭'}")

    while True:
        prompt = "\n[反思] > " if reflect_on else "\n> "
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
            handled = handle_command(task, reflect_on)
            if handled is not None:
                reflect_on = handled
            continue

        if reflect_on:
            print("[ReAct] 反思模式执行中...")
            result = agent.run_with_reflection(task, max_retries=args.max_retries, max_steps=args.max_steps)
        else:
            result = agent.run(task, max_steps=args.max_steps)

        print(f"\n结果: {result}")


def handle_command(cmd: str, reflect_on: bool) -> bool | None:
    """处理内置命令，返回新的 reflect_on 值或 None（无需更新）。"""
    parts = cmd.lower().split()
    cmd_name = parts[0]

    if cmd_name in ("/reflect", "/r"):
        if len(parts) > 1 and parts[1] in ("on", "1", "true", "yes"):
            reflect_on = True
        elif len(parts) > 1 and parts[1] in ("off", "0", "false", "no"):
            reflect_on = False
        else:
            reflect_on = not reflect_on
        print(f"[ReAct] 反思模式已切换为: {'🟢 开启' if reflect_on else '⚫ 关闭'}")
        return reflect_on

    if cmd_name in ("/help", "/h", "/?"):
        print("""
可用命令:
  /reflect, /r       切换反思模式（开/关）
  /reflect on/off    直接设置反思模式
  /help, /h          显示此帮助
  exit, quit         退出程序
        """.strip())
        return None

    print(f"未知命令: {cmd_name}，输入 /help 查看可用命令。")
    return None


if __name__ == "__main__":
    main()
