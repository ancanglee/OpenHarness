# 业务概述

## 业务上下文

OpenHarness 是一个开源的 AI 编码助手 CLI 工具（Claude Code 的 Python 移植版），为开发者提供基于大语言模型的交互式编码辅助能力。

## 业务描述
- **核心业务**: 通过命令行界面，让开发者与 AI 模型进行对话式编程协作
- **目标用户**: 软件开发者、DevOps 工程师
- **核心价值**: 提供多 LLM 提供商支持的统一编码助手体验

## 业务事务
1. **对话式编码** — 用户通过 CLI 与 AI 模型交互，获取代码建议、调试帮助
2. **工具调用** — AI 模型可调用文件操作、Shell 命令等工具完成编码任务
3. **多提供商切换** — 支持 Anthropic、OpenAI、DeepSeek 等多个 LLM 提供商
4. **MCP 协议集成** — 通过 Model Context Protocol 扩展工具能力
5. **团队协作（Swarm）** — 多 agent 协同工作，分配子任务
6. **会话管理** — 会话持久化、恢复、历史记录
7. **权限控制** — 工具调用的权限检查和沙箱隔离

## 业务词典
| 术语 | 含义 |
|------|------|
| Provider | LLM 服务提供商（如 Anthropic、OpenAI） |
| Bridge | 提供商桥接层，管理子会话 |
| Swarm | 多 agent 协作框架 |
| Teammate | Swarm 中的协作 agent |
| MCP | Model Context Protocol，工具扩展协议 |
| QueryEngine | 核心查询引擎，管理对话和工具循环 |
| Hook | 事件钩子，在特定时机触发自定义逻辑 |
