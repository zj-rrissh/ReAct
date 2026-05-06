# config.json 配置文件控制 API 切换 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 config.json 集中管理 LLM 提供商配置，新增 OpenAI 兼容 API 只需修改配置文件，无需改动 Python 代码。

**Architecture:** 新增 `load_config()` 读取 config.json → 重构 `create_deepseek_client()` 为通用 `create_openai_compatible_client()` → `create_client()` 从 config 动态获取 provider 配置 → CLI choices 动态生成。api_key 优先级：环境变量 > config.json > 报错。

**Tech Stack:** Python stdlib `json`, `openai` SDK, `python-dotenv`

---

### Task 1: 创建配置文件

**Files:**
- Create: `config.json`
- Create: `config.json.example`
- Modify: `.gitignore`

- [ ] **Step 1: 创建 config.json.example（可提交到 git 的模板）**

```json
{
  "provider": "deepseek",
  "model": "deepseek-chat",
  "providers": {
    "deepseek": {
      "type": "openai_compatible",
      "base_url": "https://api.deepseek.com",
      "api_key": "",
      "api_key_env": "DEEPSEEK_API_KEY"
    },
    "ollama": {
      "type": "ollama",
      "model": "llama3:8b"
    },
    "openai": {
      "type": "openai_compatible",
      "base_url": "https://api.openai.com/v1",
      "api_key": "",
      "api_key_env": "OPENAI_API_KEY"
    }
  }
}
```

- [ ] **Step 2: 创建 config.json（实际使用的配置，从 example 复制）**

Run: `cp config.json.example config.json`

- [ ] **Step 3: 将 config.json 加入 .gitignore**

Read `.gitignore`，在 `.env` 行后添加 `config.json`：

```gitignore
.env
config.json
```

- [ ] **Step 4: 更新 .env.example，添加更多 provider 的 env 变量模板**

```bash
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# OpenAI API 配置
OPENAI_API_KEY=sk-your-api-key

# 其他 OpenAI 兼容 API（如 千问、智谱、Kimi 等）
# QWEN_API_KEY=sk-your-api-key
# GLM_API_KEY=sk-your-api-key
# MOONSHOT_API_KEY=sk-your-api-key
```

- [ ] **Step 5: 提交配置文件**

```bash
git add config.json.example .env.example .gitignore
git commit -m "feat: 添加 config.json 配置文件支持，新增 config.json.example 和 .env.example 模板"
```

---

### Task 2: 实现 load_config() 函数

**Files:**
- Modify: `ReAct.py`（在 import 区域后、现有工厂函数前插入）
- Test: `tests/test_config.py`（新建）

- [ ] **Step 1: 编写 load_config 的测试**

创建 `tests/test_config.py`：

```python
"""config.json 加载逻辑测试。"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from ReAct import load_config


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        """正常加载合法 config.json。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "openai",
            "model": "gpt-4o",
            "providers": {
                "openai": {
                    "type": "openai_compatible",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "",
                    "api_key_env": "OPENAI_API_KEY"
                }
            }
        }))
        config = load_config(str(config_path))
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o"
        assert "openai" in config["providers"]

    def test_load_config_default_path(self, tmp_path, monkeypatch):
        """无参数时从当前目录加载 config.json。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "deepseek",
            "model": "deepseek-chat",
            "providers": {}
        }))
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config["provider"] == "deepseek"

    def test_missing_config_raises_file_not_found(self, tmp_path):
        """config.json 不存在时抛出 FileNotFoundError，包含示例内容。"""
        missing_path = str(tmp_path / "config.json")
        with pytest.raises(FileNotFoundError, match="config.json"):
            load_config(missing_path)

    def test_invalid_json_raises_value_error(self, tmp_path):
        """config.json 格式错误时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text("{ invalid json }")
        with pytest.raises(ValueError, match="JSON"):
            load_config(str(config_path))

    def test_missing_provider_field_raises_value_error(self, tmp_path):
        """config.json 缺少 provider 字段时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "model": "gpt-4o",
            "providers": {}
        }))
        with pytest.raises(ValueError, match="provider"):
            load_config(str(config_path))

    def test_missing_providers_field_raises_value_error(self, tmp_path):
        """config.json 缺少 providers 字段时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "deepseek",
            "model": "deepseek-chat"
        }))
        with pytest.raises(ValueError, match="providers"):
            load_config(str(config_path))

    def test_provider_not_in_providers_raises_value_error(self, tmp_path):
        """provider 不在 providers 列表中时抛出 ValueError。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "unknown",
            "model": "some-model",
            "providers": {
                "deepseek": {"type": "openai_compatible", "base_url": "https://api.deepseek.com", "api_key": "", "api_key_env": "DEEPSEEK_API_KEY"}
            }
        }))
        with pytest.raises(ValueError, match="unknown"):
            load_config(str(config_path))
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_config.py -v
```
预期: 全部 FAIL（ImportError: cannot import name 'load_config'）

- [ ] **Step 3: 在 ReAct.py 中实现 load_config() 函数**

在 `ReAct.py` 的 import 区域之后、`create_deepseek_client` 之前插入：

```python
import json

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
        raise ValueError("config.json 缺少必需字段 'provider'")
    if "providers" not in config:
        raise ValueError("config.json 缺少必需字段 'providers'")

    provider = config["provider"]
    if provider not in config["providers"]:
        available = ", ".join(config["providers"].keys())
        raise ValueError(
            f"未知的 provider: {provider}，config.json 中可用的 provider: {available}"
        )

    if "model" not in config:
        config["model"] = provider

    return config
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_config.py -v
```
预期: 7 passed

- [ ] **Step 5: 提交**

```bash
git add tests/test_config.py ReAct.py
git commit -m "feat: 添加 load_config() 函数，支持从 config.json 加载配置"
```

---

### Task 3: 重构为通用 create_openai_compatible_client()

**Files:**
- Modify: `ReAct.py`（重构 `create_deepseek_client` 为 `create_openai_compatible_client`）
- Modify: `tests/test_react.py`（删除旧的 TestCreateDeepseekClient 类，更新 import）
- Test: `tests/test_config.py`（追加测试）

- [ ] **Step 1: 编写通用工厂函数的测试**

在 `tests/test_config.py` 末尾追加：

```python
from ReAct import create_openai_compatible_client, create_ollama_client
from utils.llm_client import LLMClient


class TestCreateOpenAICompatibleClient:
    def test_creates_llm_client_with_env_api_key(self, monkeypatch):
        """环境变量有 api_key 时从 env 读取。"""
        monkeypatch.setenv("TEST_API_KEY", "sk-env-key")
        client = create_openai_compatible_client(
            provider_name="test-provider",
            model_name="gpt-4o",
            base_url="https://api.test.com",
            api_key="",
            api_key_env="TEST_API_KEY",
        )
        assert isinstance(client, LLMClient)

    def test_creates_llm_client_with_config_api_key(self, monkeypatch):
        """环境变量未设置时使用 config 中的 api_key。"""
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        client = create_openai_compatible_client(
            provider_name="test-provider",
            model_name="gpt-4o",
            base_url="https://api.test.com",
            api_key="sk-config-key",
            api_key_env="TEST_API_KEY",
        )
        assert isinstance(client, LLMClient)

    def test_raises_when_no_api_key(self, monkeypatch):
        """env 和 config 都没有 api_key 时报错。"""
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        with pytest.raises(ValueError, match="api_key"):
            create_openai_compatible_client(
                provider_name="test-provider",
                model_name="gpt-4o",
                base_url="https://api.test.com",
                api_key="",
                api_key_env="TEST_API_KEY",
            )

    def test_env_priority_over_config(self, monkeypatch):
        """环境变量优先级高于 config 中的 api_key。"""
        monkeypatch.setenv("PRIORITY_KEY", "sk-from-env")
        client = create_openai_compatible_client(
            provider_name="test-provider",
            model_name="gpt-4o",
            base_url="https://api.test.com",
            api_key="sk-from-config",
            api_key_env="PRIORITY_KEY",
        )
        assert isinstance(client, LLMClient)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_config.py::TestCreateOpenAICompatibleClient -v
```
预期: 全部 FAIL（ImportError）

- [ ] **Step 3: 实现通用 create_openai_compatible_client()**

将 `ReAct.py` 中的 `create_deepseek_client` 替换为：

```python
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
```

同时删除旧的 `create_deepseek_client` 函数。

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_config.py::TestCreateOpenAICompatibleClient -v
```
预期: 4 passed

- [ ] **Step 4.5: 删除旧的 TestCreateDeepseekClient 测试类和 import**

在 `tests/test_react.py` 中：
1. 删除整个 `TestCreateDeepseekClient` 类（第 42-61 行）
2. 在顶部 import 中删除 `create_deepseek_client`：

```python
from ReAct import (
    create_client,
    create_ollama_client,
    create_orchestrator,
    handle_command,
)
```

- [ ] **Step 5: 运行全部测试确保无回归**

```bash
python -m pytest tests/ -v
```
预期: 全部通过

- [ ] **Step 6: 提交**

```bash
git add ReAct.py tests/test_config.py
git commit -m "refactor: 重构 create_deepseek_client 为通用 create_openai_compatible_client"
```

---

### Task 4: 重构 create_client() 从 config 读取配置

**Files:**
- Modify: `ReAct.py`（重构 `create_client()`）
- Modify: `tests/test_react.py`（更新旧测试，添加新测试）

- [ ] **Step 1: 更新 create_client 测试**

在 `tests/test_react.py` 中替换 `TestCreateClient` 类：

```python
class TestCreateClient:
    def test_create_client_from_config_deepseek(self, tmp_path, monkeypatch):
        """从 config 读取 deepseek provider 创建客户端。"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "deepseek",
            "model": "deepseek-chat",
            "providers": {
                "deepseek": {
                    "type": "openai_compatible",
                    "base_url": "https://api.deepseek.com",
                    "api_key": "",
                    "api_key_env": "DEEPSEEK_API_KEY"
                }
            }
        }))
        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "test"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)
        with patch.dict("sys.modules", {"openai": fake_openai}):
            client = create_client(config_path=str(config_path))
            assert isinstance(client, LLMClient)

    def test_create_client_from_config_ollama(self, tmp_path):
        """从 config 读取 ollama provider 创建客户端。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "ollama",
            "model": "llama3:8b",
            "providers": {
                "ollama": {
                    "type": "ollama",
                    "model": "llama3:8b"
                }
            }
        }))
        fake_ollama = MagicMock()
        fake_ollama.chat.return_value = {"message": {"content": "reply"}}
        with patch.dict("sys.modules", {"ollama": fake_ollama}):
            client = create_client(config_path=str(config_path))
            assert isinstance(client, LLMClient)

    def test_create_client_unknown_provider_type_raises_value_error(self, tmp_path):
        """config 中 provider type 未知时报错。"""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "bad",
            "model": "bad-model",
            "providers": {
                "bad": {
                    "type": "unknown_type"
                }
            }
        }))
        with pytest.raises(ValueError, match="type"):
            create_client(config_path=str(config_path))
```

需要在 `tests/test_react.py` 顶部添加 `import json`。

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_react.py::TestCreateClient -v
```
预期: FAIL（函数签名和逻辑尚未更新）

- [ ] **Step 3: 重构 create_client()**

将 `ReAct.py` 中的 `create_client` 替换为：

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_react.py::TestCreateClient -v
```
预期: 3 passed

- [ ] **Step 5: 运行全部测试确保无回归**

```bash
python -m pytest tests/ -v
```
预期: 全部通过

- [ ] **Step 6: 提交**

```bash
git add ReAct.py tests/test_react.py
git commit -m "refactor: create_client() 改为从 config.json 读取配置，支持命令行覆盖"
```

---

### Task 5: 更新 main() CLI 逻辑

**Files:**
- Modify: `ReAct.py`（main 函数中的 provider choices 动态生成）

- [ ] **Step 1: 修改 main() 中 provider choices 为动态生成**

在 `ReAct.py` 的 `main()` 函数中，将：

```python
parser.add_argument(
    "-p", "--provider",
    type=str,
    default="deepseek",
    choices=["ollama", "deepseek"],
    help="LLM 后端: ollama（本地）或 deepseek（API）"
)
```

改为：

```python
# 尝试加载 config 以获取可用 provider 列表
try:
    _config = load_config()
    _available_providers = list(_config["providers"].keys())
    _default_provider = _config["provider"]
    _default_model = _config.get("model", _default_provider)
except Exception:
    _available_providers = ["deepseek", "ollama"]
    _default_provider = "deepseek"
    _default_model = "deepseek-chat"

parser.add_argument(
    "-p", "--provider",
    type=str,
    default=None,
    choices=_available_providers,
    help=f"LLM 后端（可用: {', '.join(_available_providers)}）"
)
```

- [ ] **Step 2: 更新 default model 选择逻辑**

将：

```python
if args.model is None:
    args.model = "deepseek-chat" if args.provider == "deepseek" else "llama3:8b"
```

改为：

```python
# 命令行参数覆盖 config
if args.provider is None:
    args.provider = _default_provider
if args.model is None:
    args.model = _default_model
```

- [ ] **Step 3: 更新 create_client 调用，传入新的参数**

将：

```python
print(f"[ReAct] 后端: {args.provider}, 模型: {args.model}")
client = create_client(args.provider, args.model)
```

改为：

```python
print(f"[ReAct] 后端: {args.provider}, 模型: {args.model}")
client = create_client(provider=args.provider, model_name=args.model)
```

- [ ] **Step 4: 手动验证程序启动**

```bash
python ReAct.py --help
```
预期: 显示帮助信息，provider choices 从 config.json 动态加载

- [ ] **Step 5: 运行全部测试**

```bash
python -m pytest tests/ -v
```
预期: 全部通过

- [ ] **Step 6: 提交**

```bash
git add ReAct.py
git commit -m "feat: CLI --provider choices 从 config.json 动态生成"
```

---

### Task 6: 集成测试与验证

**Files:**
- Create: `tests/test_integration_config.py`（新建）

- [ ] **Step 1: 编写端到端集成测试**

创建 `tests/test_integration_config.py`：

```python
"""config.json 端到端集成测试。"""
import json
import os

import pytest


class TestConfigIntegration:
    """完整的 config.json -> create_client -> LLMClient 流程测试。"""

    def test_full_flow_openai_compatible(self, tmp_path, monkeypatch):
        """完整流程: config.json 定义 openai_compatible -> 创建客户端 -> 调用 LLM。"""
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("MY_KEY", "sk-integration-test")

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "my_provider",
            "model": "my-model-v1",
            "providers": {
                "my_provider": {
                    "type": "openai_compatible",
                    "base_url": "https://my-api.example.com",
                    "api_key": "",
                    "api_key_env": "MY_KEY"
                }
            }
        }))

        from ReAct import create_client

        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "integration response"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)

        with patch.dict("sys.modules", {"openai": fake_openai}):
            from ReAct import create_client
            client = create_client(config_path=str(config_path))
            result = client.generate("hello")
            assert result == "integration response"

    def test_full_flow_config_api_key_fallback(self, tmp_path, monkeypatch):
        """config.json 中直接写 api_key，无环境变量时的完整流程。"""
        from unittest.mock import MagicMock, patch

        monkeypatch.delenv("MY_OTHER_KEY", raising=False)

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "test_p",
            "model": "test-m",
            "providers": {
                "test_p": {
                    "type": "openai_compatible",
                    "base_url": "https://test.example.com",
                    "api_key": "sk-direct-key",
                    "api_key_env": "MY_OTHER_KEY"
                }
            }
        }))

        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "direct key response"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)

        with patch.dict("sys.modules", {"openai": fake_openai}):
            from ReAct import create_client
            client = create_client(config_path=str(config_path))
            result = client.generate("hello")
            assert result == "direct key response"

    def test_cli_override_provider(self, tmp_path, monkeypatch):
        """命令行 --provider 覆盖 config.json 中的 provider。"""
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("OVERRIDE_KEY", "sk-override")

        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "provider": "default_p",
            "model": "default-m",
            "providers": {
                "default_p": {
                    "type": "openai_compatible",
                    "base_url": "https://default.example.com",
                    "api_key": "",
                    "api_key_env": "DEFAULT_KEY"
                },
                "override_p": {
                    "type": "openai_compatible",
                    "base_url": "https://override.example.com",
                    "api_key": "",
                    "api_key_env": "OVERRIDE_KEY"
                }
            }
        }))

        fake_openai = MagicMock()
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = "override"
        fake_client.chat.completions.create.return_value = fake_response
        fake_openai.OpenAI = MagicMock(return_value=fake_client)

        with patch.dict("sys.modules", {"openai": fake_openai}):
            from ReAct import create_client
            # 使用 provider= 参数覆盖
            client = create_client(config_path=str(config_path), provider="override_p")
            result = client.generate("hello")
            assert result == "override"
```

- [ ] **Step 2: 运行集成测试**

```bash
python -m pytest tests/test_integration_config.py -v
```
预期: 3 passed

- [ ] **Step 3: 运行全部测试最终验证**

```bash
python -m pytest tests/ -v
```
预期: 全部通过

- [ ] **Step 4: 提交**

```bash
git add tests/test_integration_config.py
git commit -m "test: 添加 config.json 端到端集成测试"
```

---

### 最终提交历史

```
feat: 添加 config.json 配置文件支持，新增 config.json.example 和 .env.example 模板
feat: 添加 load_config() 函数，支持从 config.json 加载配置
refactor: 重构 create_deepseek_client 为通用 create_openai_compatible_client
refactor: create_client() 改为从 config.json 读取配置，支持命令行覆盖
feat: CLI --provider choices 从 config.json 动态生成
test: 添加 config.json 端到端集成测试
```
