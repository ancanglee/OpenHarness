# 服务设计

## 服务层概述

本次增强不引入新的独立服务，而是在现有架构内扩展：

### 1. Provider 服务扩展

**现有流程**:
```
Settings -> detect_provider() -> 选择 Client -> QueryEngine 使用
```

**增强后**:
```
Settings -> detect_provider() -> 选择 Client -> QueryEngine 使用
                                    |
                                    +-> AnthropicApiClient (backend_type="anthropic")
                                    +-> OpenAICompatibleClient (backend_type="openai_compat")
                                    +-> CopilotClient (backend_type="copilot")
                                    +-> BedrockClient (backend_type="bedrock")  [新增]
```

**客户端工厂逻辑**（需在现有代码中定位并扩展）:
- 当 `backend_type == "bedrock"` 时，创建 `BedrockClient` 实例
- 传入 region、profile 等 AWS 配置

### 2. Multi-Agent 编排服务扩展

**现有流程**:
```
用户请求 -> QueryEngine -> 单 agent 执行
```

**增强后**:
```
用户请求 -> QueryEngine -> TaskSplitter 分析
                              |
                    +---------+---------+
                    |                   |
              单任务（直接执行）    多任务（拆分）
                                        |
                                  TeamLifecycleManager
                                   /        |        \
                              SubAgent1  SubAgent2  SubAgent3
                                   \        |        /
                                  结果汇总 -> 主 agent 响应
```

**编排模式**:
- 主 agent 通过 TaskSplitter 判断是否需要拆分
- 如需拆分，通过 TeamLifecycleManager 创建团队
- 子 agent 通过 StructuredMessage 接收任务
- SharedContext 提供必要的上下文
- 主 agent 汇总结果后响应用户
