# Unit 2: Multi-Agent 增强 — 业务逻辑模型

## 核心流程

### 1. 任务拆分流程
```
用户请求 -> TaskSplitter.analyze_and_split(request, context)
  |
  +-> 使用 LLM 分析请求复杂度
  +-> 判断是否需要拆分（单任务直接返回空列表）
  +-> 如需拆分:
        +-> 识别可并行的子任务
        +-> 为每个子任务生成描述和约束
        +-> 标注子任务间依赖关系
        +-> 返回 list[SubTask]
```

### 2. 子任务执行流程
```
主 agent 收到 list[SubTask]
  |
  +-> TeamLifecycleManager.create_team(name)
  +-> 为每个 SubTask:
  |     +-> 创建 SharedContext（传递相关上下文）
  |     +-> 构建 StructuredMessage(type=task_assignment)
  |     +-> 通过 Mailbox 发送给子 agent
  |
  +-> 等待子 agent 完成:
  |     +-> 监听 Mailbox 中的 status_update 和 result 消息
  |     +-> 处理依赖关系（有依赖的任务等前置完成）
  |
  +-> TaskSplitter.merge_results(subtasks, results)
  +-> 汇总结果返回用户
```

### 3. 结构化消息流程
```
发送方 -> StructuredMessage.create(type, payload, priority)
  |
  +-> 序列化为 dict
  +-> Mailbox.send(receiver_id, message)
  +-> 接收方 Mailbox.receive() -> StructuredMessage
  +-> 根据 message_type 处理:
        task_assignment -> 开始执行任务
        status_update -> 更新任务状态
        result -> 收集执行结果
        error -> 错误处理
```

### 4. 共享上下文流程
```
主 agent 创建 SharedContext
  |
  +-> add_messages(相关对话历史片段)
  +-> create_subset(选择与子任务相关的消息)
  +-> 通过 StructuredMessage.context_refs 引用
  |
子 agent 使用:
  +-> SharedContext.get_messages() 获取上下文
  +-> 执行任务
  +-> SharedContext.merge_result(agent_id, result)
  |
主 agent 汇总:
  +-> 从各子 agent 的 SharedContext 收集结果
```
