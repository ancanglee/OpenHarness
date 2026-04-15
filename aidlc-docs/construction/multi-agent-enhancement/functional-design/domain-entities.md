# Unit 2: Multi-Agent 增强 — 领域实体

## 新增实体

### MessageType (枚举)
```python
class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    RESULT = "result"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
```

### Priority (枚举)
```python
class Priority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
```

### TaskStatus (枚举)
```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
```

### StructuredMessage
```python
@dataclass
class StructuredMessage:
    message_id: str          # UUID
    sender_id: str           # agent ID
    receiver_id: str         # agent ID
    message_type: MessageType
    priority: Priority
    status: TaskStatus
    payload: dict[str, Any]  # 消息内容
    context_refs: list[str]  # SharedContext ID 引用
    timestamp: float
```

### SharedContext
```python
class SharedContext:
    context_id: str
    _messages: list[ConversationMessage]
    _results: dict[str, str]  # agent_id -> result
    _max_messages: int
```

### SubTask
```python
@dataclass
class SubTask:
    task_id: str
    description: str
    dependencies: list[str]  # 依赖的 task_id
    context_refs: list[str]  # SharedContext ID
    estimated_complexity: str  # simple | moderate | complex
```

### SubTaskResult
```python
@dataclass
class SubTaskResult:
    task_id: str
    status: TaskStatus
    output: str
    error: str | None = None
```

### TaskSplitter
```python
class TaskSplitter:
    _api_client: SupportsStreamingMessages
    _model: str
```

## 修改实体

### Mailbox（增强）
- 新增方法: `send_structured(message: StructuredMessage)`
- 新增方法: `receive_structured(agent_id: str) -> list[StructuredMessage]`
- 现有方法保持不变

### TeamLifecycleManager（增强）
- 新增方法: `create_team_with_tasks(name, subtasks, context)`
- 现有方法保持不变
