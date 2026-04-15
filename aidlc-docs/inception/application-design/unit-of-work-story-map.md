# 工作单元需求映射

## Unit 1: Bedrock Provider

| 需求 ID | 需求描述 | 映射 |
|---------|---------|------|
| FR-1.1 | 支持所有 Bedrock 模型 | BedrockClient + Converse API |
| FR-1.2 | AWS 认证（环境变量/Profile/IAM Role） | BedrockClient.__init__ |
| FR-1.3 | 区域配置 | Settings + BedrockClient |
| FR-1.4 | API 集成（流式、工具调用） | BedrockClient.stream_message |
| FR-1.5 | 提供商注册 | Registry + Provider + Settings |
| FR-1.6 | 费用追踪 | BedrockClient -> UsageSnapshot |
| NFR-1 | 兼容性 | 不影响现有客户端 |
| NFR-2 | 性能（流式延迟） | ConverseStream API |
| NFR-3 | 可测试性（mock） | boto3 stubber |
| NFR-4 | 安全性（凭证） | boto3 凭证链 |

## Unit 2: Multi-Agent 增强

| 需求 ID | 需求描述 | 映射 |
|---------|---------|------|
| FR-2.1 | 任务自动拆分 | TaskSplitter |
| FR-2.2 | 结构化消息 | StructuredMessage |
| FR-2.2 | 共享上下文 | SharedContext |
| FR-2.3 | 编排集成 | TeamLifecycleManager + Mailbox |
| NFR-1 | 兼容性 | 不破坏现有 Swarm |
| NFR-2 | 性能（拆分开销） | TaskSplitter <2s |
| NFR-3 | 可测试性 | mock API client |
| NFR-5 | 可维护性 | 遵循代码风格 |


---

## 补充映射（Unit 2 扩展）

| 需求 ID | 需求描述 | 映射 |
|---------|---------|------|
| FR-2.4 | Orchestrator-Subagent 模式 | Orchestrator |
| FR-2.5 | Verification Subagent | VerificationAgent |
| FR-2.6 | 专业化 Agent 配置 | SpecializedAgent + AgentDefinition |
| FR-2.7 | 并行执行 | Orchestrator (asyncio.gather) |
| FR-2.8 | 上下文中心分解 | TaskSplitter 增强 |
