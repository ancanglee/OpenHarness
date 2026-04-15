# 组件方法签名

## BedrockClient

```python
class BedrockClient:
    def __init__(
        self,
        *,
        region: str | None = None,
        profile: str | None = None,
        role_arn: str | None = None,
    ) -> None: ...

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]: ...

    # 内部方法
    def _create_boto3_session(self) -> boto3.Session: ...
    def _build_converse_params(self, request: ApiMessageRequest) -> dict[str, Any]: ...
    def _convert_tools_to_bedrock(self, tools: list[dict]) -> list[dict]: ...
    def _parse_stream_event(self, event: dict) -> ApiStreamEvent | None: ...
```

## StructuredMessage

```python
@dataclass
class StructuredMessage:
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType  # task_assignment | result | status_update | error
    priority: Priority  # high | normal | low
    status: TaskStatus  # pending | in_progress | completed | failed
    payload: dict[str, Any]
    context_refs: list[str]  # 引用的共享上下文 ID
    timestamp: float

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StructuredMessage": ...
```

## SharedContext

```python
class SharedContext:
    def __init__(self, context_id: str) -> None: ...

    def add_messages(self, messages: list[ConversationMessage]) -> None: ...
    def get_messages(self, *, max_tokens: int | None = None) -> list[ConversationMessage]: ...
    def merge_result(self, agent_id: str, result: str) -> None: ...
    def create_subset(self, relevant_messages: list[int]) -> "SharedContext": ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SharedContext": ...
```

## TaskSplitter

```python
class TaskSplitter:
    def __init__(self, *, api_client: SupportsStreamingMessages, model: str) -> None: ...

    async def analyze_and_split(
        self, user_request: str, context: SharedContext | None = None
    ) -> list[SubTask]: ...

    async def merge_results(
        self, subtasks: list[SubTask], results: list[SubTaskResult]
    ) -> str: ...

@dataclass
class SubTask:
    task_id: str
    description: str
    dependencies: list[str]  # 依赖的其他 subtask ID
    context_refs: list[str]
    estimated_complexity: str  # simple | moderate | complex

@dataclass
class SubTaskResult:
    task_id: str
    status: TaskStatus
    output: str
    error: str | None = None
```
