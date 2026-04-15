# 单元测试执行指南

## 运行所有新增测试
```bash
cd OpenHarness
python -m pytest tests/test_bedrock_client.py tests/test_structured_message.py tests/test_shared_context.py tests/test_task_splitter.py -v
```

## 按 Unit 运行

### Unit 1: Bedrock Provider
```bash
python -m pytest tests/test_bedrock_client.py -v
```
- 预期: 10 个测试通过
- 覆盖: 消息格式转换、工具转换、模型 ID 规范化

### Unit 2: Multi-Agent
```bash
python -m pytest tests/test_structured_message.py tests/test_shared_context.py tests/test_task_splitter.py -v
```
- 预期: 19 个测试通过
- 覆盖: 结构化消息、共享上下文、任务拆分解析

## 运行全部项目测试
```bash
python -m pytest tests/ -v
```

## 测试覆盖率
```bash
python -m pytest tests/test_bedrock_client.py tests/test_structured_message.py tests/test_shared_context.py tests/test_task_splitter.py --cov=src/openharness --cov-report=term-missing
```
