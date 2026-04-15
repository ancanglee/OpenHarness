# 集成测试指南

## 场景 1: Bedrock Provider 端到端调用

### 前置条件
- 有效的 AWS 凭证（有 bedrock:InvokeModel 权限）
- AWS_REGION 已配置

### 测试步骤
```bash
# 启动 OpenHarness 使用 Bedrock Provider
oh --model bedrock/anthropic.claude-3-sonnet-20240229-v1:0

# 在交互界面中输入简单请求验证:
# > hello, what model are you?
# 预期: 收到 Claude 的流式响应
```

### 验证点
- 流式文本输出正常
- Token 用量统计正确
- 退出时无错误

## 场景 2: Bedrock 工具调用

### 测试步骤
```bash
oh --model bedrock/anthropic.claude-3-sonnet-20240229-v1:0

# 请求需要工具调用的操作:
# > read the file pyproject.toml and tell me the version
# 预期: agent 调用 read_file 工具，返回版本信息
```

## 场景 3: Multi-Agent 任务拆分（需要手动验证）

### 测试步骤
```bash
# 使用支持 swarm 的模式启动
oh

# 请求涉及多文件修改的复杂任务:
# > create a new CLI command 'status' that shows provider info and a 'version' command that shows the version
# 预期: TaskSplitter 识别为可拆分任务
```

## 场景 4: Unit 1 + Unit 2 集成

### 测试步骤
- 配置 Bedrock 作为 Provider
- 触发多 agent 任务
- 验证子 agent 能通过 Bedrock 调用模型
- 验证结构化消息在 agent 间正确传递
