# Unit 1: Bedrock Provider — 业务逻辑模型

## 核心流程

### 1. 客户端初始化
```
BedrockClient.__init__(region, profile, role_arn)
  |
  +-> 创建 boto3 Session（按优先级：role_arn > profile > 环境变量）
  +-> 创建 bedrock-runtime 客户端
  +-> 验证区域配置（AWS_REGION / AWS_DEFAULT_REGION / 参数传入）
```

### 2. 流式消息处理
```
stream_message(ApiMessageRequest)
  |
  +-> _build_converse_params(request)
  |     +-> 转换 system_prompt 为 Bedrock system 格式
  |     +-> 转换 messages 为 Bedrock Converse 格式
  |     +-> 转换 tools 为 Bedrock toolConfig 格式
  |     +-> 设置 modelId（处理 bedrock/ 前缀）
  |
  +-> bedrock_client.converse_stream(**params)
  |
  +-> 遍历 EventStream:
        +-> contentBlockDelta (text) -> yield ApiTextDeltaEvent
        +-> contentBlockDelta (toolUse) -> 累积工具调用
        +-> messageStop -> 构建 ConversationMessage
        +-> metadata (usage) -> 提取 token 用量
        +-> yield ApiMessageCompleteEvent
```

### 3. 消息格式转换

#### Anthropic -> Bedrock Converse 格式
```
Anthropic 格式:
  messages: [{role: "user", content: [{type: "text", text: "..."}]}]

Bedrock Converse 格式:
  messages: [{role: "user", content: [{text: "..."}]}]
```

#### 工具调用转换
```
Anthropic 格式:
  {name: "tool", description: "...", input_schema: {...}}

Bedrock toolConfig 格式:
  {tools: [{toolSpec: {name: "tool", description: "...", inputSchema: {json: {...}}}}]}
```

#### 工具结果转换
```
Anthropic ToolResultBlock:
  {tool_use_id: "id", content: "result"}

Bedrock toolResult:
  {toolUseId: "id", content: [{text: "result"}]}
```

## 模型 ID 处理
- 用户输入: `bedrock/anthropic.claude-3-sonnet-20240229-v1:0`
- 去除 `bedrock/` 前缀后传给 Bedrock API
- 也支持直接输入 Bedrock 模型 ID（无前缀）
