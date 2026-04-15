# Multi-Agent 补充功能设计 — Anthropic 最佳实践模式

## 1. Orchestrator 编排循环

```
用户请求
  |
  v
Orchestrator.run(request)
  |
  +-> TaskSplitter.analyze_and_split(request)
  |     |
  |     +-> 返回 [] (不需拆分) -> 单 agent 直接执行
  |     +-> 返回 [subtasks] -> 进入编排循环
  |
  +-> 依赖分析: _resolve_execution_order(subtasks)
  |     +-> 无依赖的任务 -> 并行组
  |     +-> 有依赖的任务 -> 按拓扑排序分层
  |
  +-> 按层执行:
  |     Layer 0: asyncio.gather(task_a, task_b)  # 并行
  |     Layer 1: asyncio.gather(task_c)          # 等 Layer 0 完成
  |
  +-> 每个子任务完成后 -> VerificationAgent.verify()
  |     +-> 通过 -> 标记完成
  |     +-> 失败 -> 重试（最多 max_attempts 次）
  |
  +-> TaskSplitter.merge_results() -> 返回综合结果
```

## 2. Verification Subagent 模式

```
VerificationAgent.verify(task_description, output, criteria)
  |
  +-> 构建验证 prompt（不包含实现上下文）
  |     - 任务描述（做了什么）
  |     - 产出内容（结果是什么）
  |     - 验证标准（应该满足什么）
  |
  +-> 调用 LLM 验证
  |
  +-> 解析结果:
        +-> {"passed": true, "issues": []}
        +-> {"passed": false, "issues": ["具体问题..."]}
```

### 防止早期胜利
- 验证 prompt 明确要求: "你必须检查所有验证标准后才能标记通过"
- 要求逐条列出每个标准的验证结果
- 不允许只检查部分就声明通过

## 3. 并行执行与依赖解析

```python
# 拓扑排序分层
subtasks = [A(deps=[]), B(deps=[]), C(deps=[A]), D(deps=[A,B])]

# 解析为:
# Layer 0: [A, B]  (无依赖，并行)
# Layer 1: [C, D]  (依赖 Layer 0，等待后并行)

async def execute_layers(layers):
    for layer in layers:
        results = await asyncio.gather(*[run_subagent(t) for t in layer])
        # 验证每个结果
```

## 4. 上下文中心分解规则

TaskSplitter 的 system prompt 增加以下判断逻辑:
- 紧密耦合的工作（如功能实现+测试）保持在同一子任务
- 只在上下文可真正隔离时才拆分
- 避免按问题类型拆分（不要分成"写代码的agent"和"写测试的agent"）
- 每个子任务应该是自包含的工作单元

## 5. 专业化 Agent 选择

```
Orchestrator 根据子任务类型选择 agent:
  |
  +-> 子任务涉及代码 -> 使用 coding agent (有文件工具)
  +-> 子任务涉及研究 -> 使用 research agent (有搜索工具)
  +-> 子任务涉及验证 -> 使用 verification agent (有测试工具)
  +-> 默认 -> 使用通用 agent
```
