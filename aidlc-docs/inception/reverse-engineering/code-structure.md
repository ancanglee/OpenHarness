# 代码结构

## 构建系统
- **类型**: Hatch (pyproject.toml)
- **包名**: openharness-ai
- **版本**: 0.1.6
- **入口点**: `openharness.cli:app`（命令: `oh`, `openharness`, `openh`）

## Provider 架构（与 Bedrock 需求直接相关）

### 提供商抽象层
```
api/
+-- client.py          # SupportsStreamingMessages 协议（核心接口）
|                      # AnthropicApiClient（Anthropic 原生 SDK）
+-- openai_client.py   # OpenAICompatibleClient（OpenAI 兼容 API）
+-- copilot_client.py  # CopilotClient（GitHub Copilot）
+-- registry.py        # ProviderSpec 数据类 + PROVIDERS 注册表
+-- provider.py        # detect_provider() 提供商检测逻辑
+-- usage.py           # UsageSnapshot 用量统计
+-- errors.py          # API 错误类型
```

### 关键接口: `SupportsStreamingMessages`
```python
class SupportsStreamingMessages(Protocol):
    async def stream_message(self, request: ApiMessageRequest) -> AsyncIterator[ApiStreamEvent]:
        ...
```
所有提供商客户端都实现此协议。

### 提供商注册表 (`registry.py`)
- `ProviderSpec` 数据类定义提供商元数据
- `backend_type` 字段: "anthropic" | "openai_compat" | "copilot"
- Bedrock 已有占位注册（`backend_type="openai_compat"`），但无专用客户端
- 检测优先级: API Key 前缀 > Base URL 关键词 > 模型名关键词

### 当前 Bedrock 状态
- 注册表中已有 `bedrock` ProviderSpec（占位）
- `backend_type` 设为 `"openai_compat"`（不正确，Bedrock 有自己的 API 格式）
- 无专用 `bedrock_client.py`
- 无 AWS 认证集成（SigV4 签名）

## Swarm/Multi-Agent 架构（与 Multi-agent 需求直接相关）

### 现有 Swarm 模块
```
swarm/
+-- types.py              # TeammateIdentity, TeammateSpawnConfig, TeammateExecutor
+-- team_lifecycle.py     # TeamLifecycleManager, TeamFile, TeamMember
+-- spawn_utils.py        # agent 生成工具
+-- mailbox.py            # agent 间消息传递
+-- registry.py           # agent 注册表
+-- in_process.py         # 进程内 agent 执行
+-- subprocess_backend.py # 子进程 agent 后端
+-- worktree.py           # Git worktree 管理
+-- lockfile.py           # 锁文件管理
+-- permission_sync.py    # 权限同步

coordinator/
+-- agent_definitions.py  # AgentDefinition 类 + 内置 agent 定义
+-- coordinator_mode.py   # TeamRegistry, 协调模式
```

### 当前 Multi-Agent 状态
- 已有基础的 Swarm 框架（团队、成员、邮箱）
- 已有 Coordinator 模式（agent 定义、团队注册）
- 已有 TeammateExecutor 协议（spawn、send_message、shutdown）
- 已有子进程和进程内两种 agent 后端
- 已有 Git worktree 隔离机制

## 设计模式
| 模式 | 位置 | 用途 |
|------|------|------|
| Protocol (接口) | `api/client.py` | `SupportsStreamingMessages` 提供商抽象 |
| Registry | `api/registry.py` | 提供商注册和检测 |
| Strategy | `api/` 各客户端 | 不同提供商的 API 调用策略 |
| Observer | `engine/stream_events.py` | 流式事件处理 |
| Singleton | `bridge/manager.py` | BridgeSessionManager |
| Factory | `config/settings.py` | 根据配置创建客户端 |
