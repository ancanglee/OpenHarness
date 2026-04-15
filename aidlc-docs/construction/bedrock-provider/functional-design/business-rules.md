# Unit 1: Bedrock Provider — 业务规则

## BR-1: AWS 认证优先级
1. 如果提供 `role_arn`，使用 STS AssumeRole
2. 如果提供 `profile`，使用 named profile
3. 否则使用 boto3 默认凭证链（环境变量 > ~/.aws/credentials default > EC2/ECS role）

## BR-2: 区域解析
1. 构造函数参数 `region` 优先
2. 环境变量 `AWS_REGION` 次之
3. 环境变量 `AWS_DEFAULT_REGION` 再次
4. boto3 Session 默认区域
5. 如果都没有，抛出 `AuthenticationFailure("AWS region not configured")`

## BR-3: 模型 ID 规范化
- 如果模型名以 `bedrock/` 开头，去除前缀
- 如果模型名包含 `.`（如 `anthropic.claude-3-sonnet...`），直接使用
- 不做额外的模型名验证（由 Bedrock API 返回错误）

## BR-4: 重试策略
- 最大重试次数: 3
- 可重试状态码: 429 (ThrottlingException), 500, 502, 503
- 退避策略: 指数退避 + 随机抖动
- 不重试: 认证错误 (403)、参数错误 (400)、模型不存在 (404)

## BR-5: 错误映射
| Bedrock 错误 | OpenHarness 错误 |
|-------------|-----------------|
| AccessDeniedException | AuthenticationFailure |
| ThrottlingException | RateLimitFailure |
| ModelNotReadyException | RequestFailure (可重试) |
| ValidationException | RequestFailure |
| 其他 | RequestFailure |

## BR-6: Token 用量提取
- 从 Converse Stream 的 metadata 事件中提取
- `metadata.usage.inputTokens` -> `UsageSnapshot.input_tokens`
- `metadata.usage.outputTokens` -> `UsageSnapshot.output_tokens`

## BR-7: 提供商检测
- `backend_type` 设为 `"bedrock"`（非 "openai_compat"）
- 检测条件: base_url 包含 "bedrock" 或模型名包含 "bedrock"
- 环境变量: `AWS_ACCESS_KEY_ID`（但不作为唯一检测条件）
