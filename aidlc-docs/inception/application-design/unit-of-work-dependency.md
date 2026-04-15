# 工作单元依赖关系

## 依赖矩阵

```
                    Unit 1 (Bedrock)    Unit 2 (Multi-Agent)
Unit 1 (Bedrock)         -                    无
Unit 2 (Multi-Agent)     无                    -
```

## 分析

两个工作单元之间**无直接依赖**，可以并行开发：

- Unit 1 (Bedrock Provider) 仅涉及 `api/` 和 `config/` 模块
- Unit 2 (Multi-Agent) 仅涉及 `swarm/` 和 `coordinator/` 模块
- 两者不修改相同文件
- 两者通过 QueryEngine 间接关联，但不互相依赖

## 开发顺序建议

由于无依赖关系，建议：
1. **并行开发**：两个 Unit 可同时进行
2. **集成测试**：两个 Unit 完成后进行集成验证（Multi-Agent 使用 Bedrock Provider 作为子 agent 的 LLM 后端）

## 共享接口
- 两个 Unit 都通过 `SupportsStreamingMessages` 协议与 QueryEngine 交互
- Unit 2 的 TaskSplitter 可使用任何 Provider（包括 Unit 1 的 Bedrock）创建子 agent
