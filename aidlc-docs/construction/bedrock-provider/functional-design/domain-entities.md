# Unit 1: Bedrock Provider — 领域实体

## 核心实体

### BedrockClient
```python
class BedrockClient:
    """AWS Bedrock Runtime 客户端，实现 SupportsStreamingMessages 协议。"""
    _session: boto3.Session
    _client: Any  # bedrock-runtime client
    _region: str
```

## 复用实体（来自现有代码）

### ApiMessageRequest（不修改）
- model: str
- messages: list[ConversationMessage]
- system_prompt: str | None
- max_tokens: int
- tools: list[dict]

### ApiStreamEvent（不修改）
- ApiTextDeltaEvent(text: str)
- ApiMessageCompleteEvent(message, usage, stop_reason)
- ApiRetryEvent(message, attempt, max_attempts, delay_seconds)

### UsageSnapshot（不修改）
- input_tokens: int
- output_tokens: int

### ConversationMessage（不修改）
- role: str
- content: list[ContentBlock]

## 修改实体

### ProviderSpec（修改 registry.py 中的 Bedrock 条目）
- backend_type: "bedrock"（从 "openai_compat" 改为 "bedrock"）

### Settings（新增字段）
- aws_region: str | None
- aws_profile: str | None
- aws_role_arn: str | None
