# My Agent

一个基于 Python 的命令行 AI Agent 框架，支持交互式对话、多智能体编排（Planner-Scheduler-Executor）、工具调用、TTS 语音播报等能力。

## 特性

- **交互式对话**：基于 Rich 的终端聊天界面，支持斜杠命令、会话管理
- **多智能体编排**：Orchestra 模式将复杂请求拆解为任务 DAG，由多个 Sub-Agent 协作完成
- **工具系统**：内置文件读写、目录列举、代码搜索/定位/分页读取/补丁等开发工具，支持沙箱与安全白名单、Hook 机制
- **Prompt 管理**：基于文件系统的 Prompt Registry，支持多套提示词模板切换（`prompts/` 目录）
- **记忆与压缩**：对话记忆管理、Token 计数与上下文压缩
- **TTS 语音**：支持 Edge-TTS、GPT-SoVITS 引擎的语音播报
- **多 LLM 后端**：支持 IdeaLab（OpenAI 兼容）与 Ollama 本地模型，内置限流与重试
- **会话持久化**：JSON 存储聊天记录与编排日志

## 项目结构

```
src/my_agent/
├── main.py                  # CLI 入口（Typer）
├── cli/commands/            # chat / orchestra / config 子命令
├── common/                  # 消息模型、异常、工具名常量
├── config/                  # 配置管理（pydantic-settings）
├── core/
│   ├── orchestra/           # 多智能体编排（Planner/Scheduler/Executor/Blackboard）
│   ├── services/            # ChatService、PromptRegistry
│   └── tools/               # 工具注册、执行器、沙箱、安全、工具定义与 Hook
├── infrastructure/
│   ├── llm/                 # LLM 客户端（IdeaLab / Ollama）、限流、重试
│   ├── memory/              # 记忆、Token 计数、上下文压缩
│   ├── repositories/        # 聊天存储、编排日志存储
│   └── tts/                 # TTS 引擎与播放管理
└── utils/                   # 日志、路径解析、脱敏
```

## 安装

要求 Python >= 3.10。

```bash
pip install -e .
# 开发依赖
pip install -e ".[dev]"
```

复制 `.env.example`（或参考 `.env` 模板）配置 LLM API Key、模型等参数。

## 使用

```bash
# 交互式对话
my-agent chat start

# 多智能体编排执行复杂任务
my-agent orchestra run "帮我分析退款逻辑"

# 查看/修改配置
my-agent config show
my-agent config set TTS_ENABLED true
```

## 主要配置项

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `API_KEY` / `BASE_URL` / `DEFAULT_MODEL` | IdeaLab LLM 配置 | - |
| `OLLAMA_BASE_URL` / `OLLAMA_DEFAULT_MODEL` | Ollama 本地模型配置 | `qwen2.5:7b` |
| `PROMPT_DIR` / `DEFAULT_PROMPT` | 提示词目录与默认模板 | `./prompts` / `python_helper` |
| `ENABLE_TOOLS` / `TOOL_FILE_WHITELIST` | 工具系统开关与文件访问白名单 | `true` / `["./"]` |
| `TTS_ENABLED` / `TTS_VOICE` | TTS 开关与音色 | `false` |
| `CHAT_MAX_TURNS` | 最大对话轮数 | `20` |

## License

MIT