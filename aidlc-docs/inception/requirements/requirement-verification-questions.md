# 需求澄清问题

## Q1: Bedrock Provider 支持范围

您希望 Bedrock Provider 支持哪些模型？

A) 仅 Claude 系列模型（通过 Bedrock 调用 Anthropic Claude）
B) Claude + Amazon Titan 系列
C) Claude + Titan + Llama 系列（Meta 在 Bedrock 上的模型）
D) 所有 Bedrock 支持的模型（Claude、Titan、Llama、Mistral、Cohere 等）
E) 其他（请在 [Answer]: 标签后描述）

[Answer]:

---

## Q2: AWS 认证方式

Bedrock 的 AWS 认证应支持哪些方式？

A) 仅环境变量（AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY）
B) 环境变量 + AWS Profile（~/.aws/credentials）
C) 环境变量 + AWS Profile + IAM Role（AssumeRole）
D) 完整 boto3 默认凭证链（环境变量、Profile、IAM Role、EC2 Instance Profile、ECS Task Role 等）
E) 其他（请在 [Answer]: 标签后描述）

[Answer]:

---

## Q3: Bedrock 区域配置

A) 仅支持单一区域（通过环境变量 AWS_REGION 配置）
B) 支持多区域，用户可在配置中指定
C) 支持多区域 + 自动 fallback（主区域不可用时切换备用区域）
E) 其他（请在 [Answer]: 标签后描述）

[Answer]:

---

## Q4: Multi-Agent 支持的具体需求

您说的 "Multi-agent 支持" 具体指什么？

A) 增强现有 Swarm 框架，让主 agent 能自动拆分任务并分配给子 agent 执行
B) 支持不同 agent 使用不同的 LLM Provider（如主 agent 用 Claude，子 agent 用 Bedrock）
C) 新增 agent 编排模式（如顺序执行、并行执行、条件分支）
D) A + B 的组合（任务拆分 + 混合 Provider）
E) 其他（请在 [Answer]: 标签后描述）

[Answer]:

---

## Q5: Multi-Agent 的 agent 间通信

A) 使用现有的 Mailbox 机制即可
B) 需要增强为结构化消息（带类型、优先级、状态）
C) 需要支持共享上下文/记忆（多个 agent 共享对话历史）
D) B + C 的组合
E) 其他（请在 [Answer]: 标签后描述）

[Answer]:

---

## Q6: 优先级

这两个功能的优先级？

A) Bedrock Provider 优先，Multi-agent 其次
B) Multi-agent 优先，Bedrock Provider 其次
C) 两者同等优先级，可以并行开发
D) 其他（请在 [Answer]: 标签后描述）

[Answer]:
