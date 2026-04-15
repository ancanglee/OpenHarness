# 依赖关系

## 内部依赖（与本次需求相关的核心链路）

```
cli.py
  |
  v
config/settings.py  -->  api/registry.py (提供商检测)
  |                           |
  v                           v
api/provider.py         api/client.py (SupportsStreamingMessages)
  |                      /          \
  v                     v            v
api/openai_client.py  api/client.py  api/copilot_client.py
(OpenAICompatibleClient) (AnthropicApiClient) (CopilotClient)
  |
  v
engine/query_engine.py  <--  tools/base.py (ToolRegistry)
  |
  v
swarm/team_lifecycle.py  <--  coordinator/agent_definitions.py
```

## 外部依赖（核心）
| 依赖 | 版本 | 用途 | 许可证 |
|------|------|------|--------|
| anthropic | >=0.40.0 | Anthropic API SDK | MIT |
| openai | >=1.0.0 | OpenAI 兼容 API | Apache-2.0 |
| httpx | >=0.27.0 | HTTP 客户端 | BSD-3 |
| pydantic | >=2.0.0 | 数据验证 | MIT |
| typer | >=0.12.0 | CLI 框架 | MIT |
| textual | >=0.80.0 | TUI 框架 | MIT |
| mcp | >=1.0.0 | MCP 协议 | MIT |

## Bedrock 需要新增的依赖
| 依赖 | 用途 |
|------|------|
| boto3 | AWS SDK，Bedrock Runtime API 调用 |
| botocore | AWS 认证（SigV4 签名） |
