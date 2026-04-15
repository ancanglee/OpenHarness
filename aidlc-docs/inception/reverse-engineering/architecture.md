# 系统架构

## 系统概述
OpenHarness 是一个模块化的 Python CLI 应用，采用分层架构，核心由 API 客户端层、查询引擎层、工具层和 UI 层组成。

## 架构图

```
+------------------------------------------------------------------+
|                         CLI 入口 (cli.py)                         |
+------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+----------------+  +------------------+  +------------------+
|   UI 层        |  |  Coordinator     |  |  Config 层       |
|  (Textual TUI) |  |  (多agent协调)    |  |  (Settings)      |
+----------------+  +------------------+  +------------------+
         |                    |                    |
         v                    v                    v
+------------------------------------------------------------------+
|                    QueryEngine (查询引擎)                          |
|  - 管理对话历史                                                    |
|  - 协调工具调用循环                                                |
|  - 流式事件处理                                                    |
+------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+----------------+  +------------------+  +------------------+
|  API 客户端层   |  |  Tools 层        |  |  Permissions     |
|  - Anthropic   |  |  - 文件操作       |  |  - 权限检查       |
|  - OpenAI兼容  |  |  - Shell命令      |  |  - 沙箱隔离       |
|  - Copilot     |  |  - MCP工具        |  +------------------+
+----------------+  +------------------+
         |
         v
+------------------------------------------------------------------+
|                    Provider Registry (提供商注册表)                 |
|  Anthropic | OpenAI | DeepSeek | Gemini | Bedrock(占位) | ...    |
+------------------------------------------------------------------+
```

## 关键组件

### API 客户端层 (`api/`)
- `client.py` — Anthropic 原生 SDK 客户端 (`AnthropicApiClient`)
- `openai_client.py` — OpenAI 兼容客户端 (`OpenAICompatibleClient`)
- `copilot_client.py` — GitHub Copilot 客户端
- `registry.py` — 提供商注册表，所有提供商的元数据
- `provider.py` — 提供商检测和认证状态

### 查询引擎 (`engine/`)
- `query_engine.py` — 核心引擎，管理对话和工具循环
- `query.py` — 查询执行逻辑
- `messages.py` — 消息模型
- `stream_events.py` — 流式事件类型

### Swarm 多agent (`swarm/`)
- `team_lifecycle.py` — 团队生命周期管理
- `types.py` — Teammate、PaneBackend 等类型定义
- `spawn_utils.py` — agent 生成工具
- `mailbox.py` — agent 间消息传递
- `registry.py` — agent 注册表

### Coordinator (`coordinator/`)
- `agent_definitions.py` — agent 定义和内置 agent
- `coordinator_mode.py` — 协调模式，团队注册

## 数据流
1. 用户输入 -> CLI -> QueryEngine.submit_message()
2. QueryEngine -> API Client (根据 provider 选择) -> LLM API
3. LLM 响应 -> StreamEvents -> 工具调用判断
4. 如有工具调用 -> ToolRegistry -> 执行 -> 结果回传 LLM
5. 最终响应 -> UI 渲染

## 集成点
- **外部 API**: Anthropic API, OpenAI API, 各兼容 API
- **MCP 服务器**: 通过 MCP 协议连接外部工具
- **Git**: worktree 管理（Swarm 用）
- **通知渠道**: Slack, Telegram, Discord, 飞书
