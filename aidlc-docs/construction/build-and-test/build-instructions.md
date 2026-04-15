# 构建指南

## 前置条件
- **Python**: >=3.10
- **构建工具**: Hatch (hatchling)
- **新增依赖**: boto3（Bedrock Provider 需要）

## 构建步骤

### 1. 安装依赖
```bash
cd OpenHarness
pip install -e ".[dev]"
pip install boto3
```

### 2. 验证安装
```bash
python -c "from openharness.api.bedrock_client import BedrockClient; print('Bedrock OK')"
python -c "from openharness.swarm.structured_message import StructuredMessage; print('StructuredMessage OK')"
python -c "from openharness.coordinator.task_splitter import TaskSplitter; print('TaskSplitter OK')"
```

### 3. 代码质量检查
```bash
# Linting
ruff check src/openharness/api/bedrock_client.py
ruff check src/openharness/swarm/structured_message.py
ruff check src/openharness/swarm/shared_context.py
ruff check src/openharness/coordinator/task_splitter.py

# 类型检查
mypy src/openharness/api/bedrock_client.py
mypy src/openharness/swarm/structured_message.py
mypy src/openharness/swarm/shared_context.py
mypy src/openharness/coordinator/task_splitter.py
```

## 环境变量（Bedrock 使用时需要）
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
# 可选
export AWS_PROFILE=your_profile
```
