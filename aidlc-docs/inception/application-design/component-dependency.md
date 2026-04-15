# 组件依赖关系

## 依赖矩阵

```
                    BedrockClient  StructuredMsg  SharedContext  TaskSplitter
BedrockClient          -              -              -              -
StructuredMsg          -              -              -              -
SharedContext          -              -              -              -
TaskSplitter           -              -              x              -
Registry(修改)         -              -              -              -
Settings(修改)         -              -              -              -
Provider(修改)         x              -              -              -
Mailbox(增强)          -              x              -              -
TeamLifecycle(增强)    -              x              x              x
QueryEngine(集成)      x              -              x              x
```

x = 依赖关系

## 依赖图

```
+------------------+
|   QueryEngine    |
+------------------+
   |    |    |
   |    |    +---> TaskSplitter ---> SharedContext
   |    |
   |    +--------> SharedContext
   |
   +-------------> BedrockClient
                        |
                        v
                   boto3 (AWS SDK)

+------------------+
| TeamLifecycle    |
| Manager (增强)   |
+------------------+
   |    |    |
   |    |    +---> TaskSplitter
   |    |
   |    +--------> SharedContext
   |
   +-------------> StructuredMessage

+------------------+
| Mailbox (增强)   |
+------------------+
   |
   +-------------> StructuredMessage

+------------------+
| Provider (修改)  |
+------------------+
   |
   +-------------> BedrockClient (检测和创建)

+------------------+
| Registry (修改)  |
+------------------+
   (独立，仅数据变更)

+------------------+
| Settings (修改)  |
+------------------+
   (独立，仅配置项变更)
```

## 通信模式

### Bedrock Provider 通信
- **同步**: Settings -> Registry -> Provider Detection
- **异步流式**: BedrockClient -> boto3 -> AWS Bedrock API -> StreamEvents

### Multi-Agent 通信
- **任务分配**: TaskSplitter -> StructuredMessage(task_assignment) -> Mailbox -> SubAgent
- **状态更新**: SubAgent -> StructuredMessage(status_update) -> Mailbox -> 主 Agent
- **结果返回**: SubAgent -> StructuredMessage(result) -> Mailbox -> TaskSplitter.merge_results()
- **上下文共享**: SharedContext 通过引用传递，避免大量数据复制
