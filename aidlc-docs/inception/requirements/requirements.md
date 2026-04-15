# 需求文档

## 意图分析
- **用户请求**: 基于 OpenHarness 现有功能增加 Bedrock Provider 支持和 Multi-agent 支持
- **请求类型**: 新功能（New Feature）
- **范围估计**: 多组件（Multiple Components）— 涉及 api/、swarm/、coordinator/、config/ 等模块
- **复杂度估计**: 中等偏高（Moderate-Complex）

---

## 功能需求

### FR-1: AWS Bedrock Provider 支持

#### FR-1.1: 模型支持
- 支持所有 Bedrock 上可用的模型，包括但不限于：
  - Anthropic Claude 系列（Claude 3/3.5/4 Haiku/Sonnet/Opus）
  - Amazon Titan 系列
  - Meta Llama 系列
  - Mistral 系列
  - Cohere 系列
- 通过 Bedrock 的统一 API 调用，无需为每个模型单独适配

#### FR-1.2: AWS 认证
- 支持三种认证方式：
  1. 环境变量（AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN）
  2. AWS Profile（~/.aws/credentials 中的 named profile）
  3. IAM Role（AssumeRole，适用于 EC2/ECS 等环境）
- 使用 boto3 的凭证解析链，按优先级自动选择可用凭证
- 支持通过配置文件或环境变量指定 AWS Profile 名称

#### FR-1.3: 区域配置
- 支持单一区域配置
- 通过环境变量 `AWS_REGION` 或 `AWS_DEFAULT_REGION` 配置
- 也可在 OpenHarness 配置文件中指定 `aws_region`

#### FR-1.4: API 集成
- 新建 `bedrock_client.py`，实现 `SupportsStreamingMessages` 协议
- 使用 boto3 的 `bedrock-runtime` 客户端调用 `InvokeModelWithResponseStream` API
- 支持流式响应（Streaming）
- 支持工具调用（Tool Use / Function Calling）
- 正确处理 Bedrock 特有的请求/响应格式（Converse API）

#### FR-1.5: 提供商注册
- 更新 `registry.py` 中的 Bedrock ProviderSpec，设置正确的 `backend_type`
- 更新 `provider.py` 中的检测逻辑
- 更新 `settings.py` 支持 Bedrock 相关配置项

#### FR-1.6: 费用追踪
- 集成 Bedrock 的 token 用量信息到现有 CostTracker

### FR-2: Multi-Agent 支持

#### FR-2.1: 任务自动拆分
- 主 agent 能根据用户请求自动分析并拆分为多个子任务
- 每个子任务分配给独立的子 agent 执行
- 主 agent 负责汇总子 agent 的执行结果

#### FR-2.2: Agent 间通信增强
- 在现有 Mailbox 基础上增加结构化消息支持：
  - 消息类型（task_assignment / result / status_update / error）
  - 优先级（high / normal / low）
  - 状态（pending / in_progress / completed / failed）
- 支持共享上下文/记忆：
  - 多个 agent 可共享对话历史片段
  - 主 agent 可向子 agent 传递相关上下文
  - 子 agent 的执行结果可合并回主 agent 的上下文

#### FR-2.3: 编排集成
- 基于现有 Swarm 框架（TeamLifecycleManager、TeammateExecutor）
- 利用现有的子进程和进程内 agent 后端
- 主 agent 通过 Coordinator 模式管理子 agent 生命周期

---

## 非功能需求

### NFR-1: 兼容性
- Bedrock 客户端不影响现有 Anthropic/OpenAI 客户端的功能
- Multi-agent 增强不破坏现有 Swarm 框架的基本功能
- 保持 Python >=3.10 兼容性

### NFR-2: 性能
- Bedrock 流式响应延迟应与直接调用 Anthropic API 相当
- 多 agent 任务拆分的开销应在可接受范围内（<2秒）

### NFR-3: 可测试性
- 新增代码需有对应的单元测试
- Bedrock 客户端需支持 mock 测试（不依赖真实 AWS 凭证）

### NFR-4: 安全性
- AWS 凭证不得硬编码或日志输出
- 遵循 AWS 最小权限原则（仅需 bedrock:InvokeModel 权限）

### NFR-5: 可维护性
- 遵循现有代码风格（ruff、mypy strict）
- 新增模块需有模块级 docstring

---

## 新增依赖
| 依赖 | 用途 | 必要性 |
|------|------|--------|
| boto3 | AWS SDK，Bedrock Runtime API | 必须 |

---

## 优先级
- Bedrock Provider 和 Multi-agent 支持同等优先级，可并行开发
- 建议拆分为两个独立的工作单元


---

## 补充需求（基于 Anthropic Multi-Agent 最佳实践）

### FR-2.4: Orchestrator-Subagent 模式
- 主 agent（Orchestrator）负责分解任务、生成子 agent、等待结果、综合汇总
- 完整的 orchestrator 循环：spawn → 等待 → 验证 → 重试（最多 N 次）
- 子 agent 失败时 orchestrator 可决定重试或跳过

### FR-2.5: Verification Subagent（验证子 agent）
- 独立的验证 agent，专门验证其他 agent 的工作产出
- 验证 agent 不需要完整的实现上下文（黑盒验证）
- 支持明确的验证标准（success criteria）
- 防止"早期胜利"问题（必须运行完整验证才能标记通过）

### FR-2.6: 专业化 Agent 配置
- 不同 agent 可配置不同的 system_prompt（行为专业化）
- 不同 agent 可配置不同的 tool set（工具专业化）
- 不同 agent 可使用不同的 model（模型专业化）
- 基于现有 AgentDefinition 体系扩展

### FR-2.7: 并行执行
- 独立子任务通过 asyncio.gather 并行执行
- 有依赖关系的子任务按拓扑排序顺序执行
- 并行执行时每个子 agent 有独立上下文（上下文隔离）

### FR-2.8: 上下文中心分解（Context-Centric Decomposition）
- TaskSplitter 按上下文边界拆分任务，而非按问题类型
- 紧密耦合的工作保持在同一 agent 中
- 只在上下文可真正隔离时才拆分
