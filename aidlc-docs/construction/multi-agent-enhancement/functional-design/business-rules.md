# Unit 2: Multi-Agent 增强 — 业务规则

## BR-1: 任务拆分判断
- 如果请求涉及单一文件或简单操作，不拆分（返回空列表）
- 如果请求涉及多个独立文件/模块的修改，拆分
- 拆分粒度: 每个子任务应是一个独立可验证的工作单元
- 最大子任务数: 不超过 5 个（避免过度拆分）

## BR-2: 子任务依赖处理
- 无依赖的子任务可并行执行
- 有依赖的子任务按依赖顺序执行
- 循环依赖检测: 如发现循环依赖，合并为单个任务

## BR-3: 结构化消息规则
- 每条消息必须有唯一 message_id（UUID）
- sender_id 和 receiver_id 必须是有效的 agent ID
- task_assignment 消息必须包含 task 描述
- result 消息必须包含执行输出
- error 消息必须包含错误详情

## BR-4: 消息优先级处理
- high: 立即处理（错误通知、紧急状态更新）
- normal: 按顺序处理（任务分配、结果返回）
- low: 空闲时处理（状态更新）

## BR-5: 共享上下文规则
- 上下文大小限制: 默认最大 50 条消息或 context_window_tokens 的 30%
- 超出限制时自动裁剪（保留最近的消息）
- 子 agent 只能读取分配给它的上下文子集
- 结果合并时去重（避免重复消息）

## BR-6: 错误处理
- 子 agent 执行失败: 标记该子任务为 failed，通知主 agent
- 主 agent 收到 failed: 可选择重试或跳过该子任务
- 通信超时: 默认 300 秒，超时后标记为 failed
- 所有子任务完成（含失败）后才汇总结果

## BR-7: 兼容性
- 不修改现有 TeammateMessage 类型，StructuredMessage 作为新增类型
- 现有 Mailbox 的 send/receive 方法保持向后兼容
- 新增 send_structured/receive_structured 方法
