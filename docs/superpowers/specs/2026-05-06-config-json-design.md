# config.json 配置文件控制 API 切换

## 目标

用 `config.json` 配置文件集中管理 LLM 提供商切换，新增 OpenAI 兼容 API 提供方只需修改配置，无需改动代码。

## config.json 结构

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

## api_key 读取优先级

```
环境变量 (api_key_env)  >  config.json 中的 api_key 字段  >  启动报错
```

- `.env` 中设置了对应环境变量 → 优先使用
- 环境变量为空 → 使用 config.json 中的 `api_key` 值
- 两者都为空 → 启动时报错，提示用户设置

## 配置优先级

```
命令行 --provider/--model  >  config.json  >  代码默认值
```

## provider 类型

| type | 说明 | 需要配置 |
|------|------|---------|
| `openai_compatible` | OpenAI 兼容 HTTP API | base_url, api_key/api_key_env |
| `ollama` | 本地 Ollama 服务 | model |

## 改动范围

### 新增文件
- `config.json` — 默认配置文件
- `config.json.example` — 配置模板，可提交到 git

### 修改文件
- `ReAct.py`:
  - 新增 `load_config()` 函数，读取 config.json
  - 修改 `create_client()`，支持从 config 读取 provider 配置
  - 重构为通用 `create_openai_compatible_client()`，覆盖所有 `openai_compatible` 类型
  - 移除硬编码的 `provider` choices，动态从 config 读取
  - CLI `--provider` 的 choices 动态生成
- `.env.example` — 添加常见 provider 的 env 变量模板

### 不需修改
- 所有 Agent 代码
- `utils/llm_client.py`
- 工具代码

## 错误处理

- config.json 不存在 → 提示创建，给出模板
- config.json 格式错误 → 提示 JSON 解析错误
- 指定的 provider 不在 providers 列表中 → 列出可用 provider
- api_key 和 api_key_env 都未设置 → 提示具体变量名
- api_key_env 已设置但环境变量为空 → 提示需要在 .env 中配置该变量
