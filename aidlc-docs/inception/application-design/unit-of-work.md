# 工作单元定义

## Unit 1: Bedrock Provider

### 基本信息
- **名称**: bedrock-provider
- **类型**: 功能模块（Module）
- **优先级**: 高
- **预估复杂度**: 中等

### 职责
- 实现 BedrockClient（SupportsStreamingMessages 协议）
- 集成 boto3 Bedrock Runtime Converse API
- AWS 认证支持（环境变量/Profile/IAM Role）
- 更新 ProviderSpec 注册表
- 更新 Settings 配置项
- 更新 Provider 检测逻辑
- 费用追踪集成

### 涉及文件
- `src/openharness/api/bedrock_client.py`（新建）
- `src/openharness/api/registry.py`（修改）
- `src/openharness/api/provider.py`（修改）
- `src/openharness/config/settings.py`（修改）
- `tests/test_bedrock_client.py`（新建）

### 新增依赖
- boto3

---

## Unit 2: Multi-Agent 增强

### 基本信息
- **名称**: multi-agent-enhancement
- **类型**: 功能模块（Module）
- **优先级**: 高
- **预估复杂度**: 中等偏高

### 职责
- 实现 StructuredMessage 结构化消息
- 实现 SharedContext 共享上下文管理
- 实现 TaskSplitter 任务自动拆分
- 增强 Mailbox 支持结构化消息
- 增强 TeamLifecycleManager 集成任务拆分

### 涉及文件
- `src/openharness/swarm/structured_message.py`（新建）
- `src/openharness/swarm/shared_context.py`（新建）
- `src/openharness/coordinator/task_splitter.py`（新建）
- `src/openharness/swarm/mailbox.py`（修改）
- `src/openharness/swarm/team_lifecycle.py`（修改）
- `tests/test_structured_message.py`（新建）
- `tests/test_shared_context.py`（新建）
- `tests/test_task_splitter.py`（新建）

### 新增依赖
- 无（使用现有依赖）
