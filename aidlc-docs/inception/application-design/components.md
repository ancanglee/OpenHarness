# 组件设计

## 新增组件

### 1. BedrockClient（新建）
- **位置**: `src/openharness/api/bedrock_client.py`
- **用途**: AWS Bedrock Runtime API 客户端
- **职责**:
  - 实现 `SupportsStreamingMessages` 协议
  - 通过 boto3 调用 Bedrock Converse API（ConverseStream）
  - 处理 AWS SigV4 认证（环境变量/Profile/IAM Role）
  - 流式响应解析，转换为 `ApiStreamEvent`
  - 工具调用（Tool Use）支持
  - 重试逻辑（限流、暂时性错误）
- **接口**: `SupportsStreamingMessages`（与现有客户端一致）

### 2. StructuredMessage（新建）
- **位置**: `src/openharness/swarm/structured_message.py`
- **用途**: 增强型 agent 间通信消息
- **职责**:
  - 定义结构化消息类型（task_assignment / result / status_update / error）
  - 消息优先级（high / normal / low）
  - 任务状态追踪（pending / in_progress / completed / failed）
  - 序列化/反序列化

### 3. SharedContext（新建）
- **位置**: `src/openharness/swarm/shared_context.py`
- **用途**: 多 agent 共享上下文管理
- **职责**:
  - 管理可共享的对话历史片段
  - 主 agent 向子 agent 传递上下文
  - 子 agent 结果合并回主 agent 上下文
  - 上下文大小控制和裁剪

### 4. TaskSplitter（新建）
- **位置**: `src/openharness/coordinator/task_splitter.py`
- **用途**: 任务自动拆分引擎
- **职责**:
  - 分析用户请求，识别可并行的子任务
  - 生成子任务描述和约束
  - 分配子任务给子 agent
  - 汇总子 agent 执行结果

## 修改组件

### 5. ProviderSpec / Registry（修改）
- **位置**: `src/openharness/api/registry.py`
- **修改**: 更新 Bedrock 的 `backend_type` 为 `"bedrock"`，新增 `backend_type` 值
- **影响**: 提供商检测逻辑

### 6. Settings / ProviderProfile（修改）
- **位置**: `src/openharness/config/settings.py`
- **修改**: 新增 Bedrock 相关配置项（aws_region, aws_profile）
- **影响**: 配置加载和解析

### 7. Provider Detection（修改）
- **位置**: `src/openharness/api/provider.py`
- **修改**: 新增 Bedrock 的认证类型和检测逻辑
- **影响**: 提供商自动检测

### 8. Mailbox（增强）
- **位置**: `src/openharness/swarm/mailbox.py`
- **修改**: 支持发送/接收 StructuredMessage
- **影响**: agent 间通信

### 9. TeamLifecycleManager（增强）
- **位置**: `src/openharness/swarm/team_lifecycle.py`
- **修改**: 集成 TaskSplitter，支持自动任务分配
- **影响**: 团队管理流程
