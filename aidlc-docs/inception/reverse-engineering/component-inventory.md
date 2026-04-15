# 组件清单

## 核心模块
| 模块 | 用途 |
|------|------|
| `api/` | LLM API 客户端层（Anthropic、OpenAI 兼容、Copilot） |
| `engine/` | 查询引擎、对话管理、流式事件 |
| `bridge/` | 桥接会话管理（子进程会话） |
| `config/` | 配置管理、Settings、路径 |
| `coordinator/` | 多 agent 协调、agent 定义 |
| `swarm/` | 多 agent 框架（团队、邮箱、生成） |

## 工具与权限
| 模块 | 用途 |
|------|------|
| `tools/` | 工具注册表和内置工具 |
| `mcp/` | MCP 协议集成 |
| `permissions/` | 权限检查器 |
| `sandbox/` | 沙箱隔离 |
| `hooks/` | 事件钩子系统 |

## UI 与交互
| 模块 | 用途 |
|------|------|
| `ui/` | Textual TUI 界面 |
| `commands/` | CLI 命令 |
| `keybindings/` | 快捷键绑定 |
| `themes/` | 主题系统 |
| `output_styles/` | 输出样式 |
| `voice/` | 语音交互 |
| `vim/` | Vim 模式 |

## 辅助模块
| 模块 | 用途 |
|------|------|
| `auth/` | 认证管理（OAuth、API Key） |
| `channels/` | 通知渠道（Slack、Telegram、Discord、飞书） |
| `memory/` | 记忆/上下文管理 |
| `personalization/` | 个性化设置 |
| `plugins/` | 插件系统 |
| `prompts/` | 提示词管理 |
| `services/` | 后台服务（LSP、Cron、会话存储） |
| `skills/` | 技能系统 |
| `state/` | 状态管理 |
| `tasks/` | 任务管理 |
| `utils/` | 通用工具函数 |

## 前端
| 模块 | 用途 |
|------|------|
| `frontend/` | TypeScript 终端前端 |

## 测试
| 模块 | 用途 |
|------|------|
| `tests/` | pytest 测试套件 |

## 统计
- **总模块数**: 30+
- **核心模块**: 6
- **工具/权限**: 4
- **UI/交互**: 7
- **辅助模块**: 13
