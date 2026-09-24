# API 与 SSE 事件契约

Base path 为 `/api/v1`。FastAPI `/docs` 和 `/openapi.json` 提供在线契约。错误统一为 `{ "error": { "code", "message", "retryable" } }`；错误消息为公开摘要，不包含堆栈或环境变量。

## 路由

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | API 健康状态及 Mock 标记 |
| GET | `/providers/status` | 固定 Mock Provider 配置状态，不表示外部连接成功 |
| POST | `/research-runs` | 校验输入、创建 planned run、Plan、初始 SearchTask 与 `plan.ready` 事件 |
| GET | `/research-runs?limit=20&cursor=` | 最多 50 条历史；cursor 编码快照水位和末条排序键 |
| GET | `/research-runs/{id}` | Run 状态 |
| GET | `/research-runs/{id}/plan` | 研究计划 |
| POST | `/research-runs/{id}/start` | planned → queued；重复启动不会创建第二个 runtime |
| POST | `/research-runs/{id}/cancel` | 取消 planned/queued/running；终态调用幂等 |
| GET | `/research-runs/{id}/events` | SSE 持久事件；支持 Last-Event-ID 或 `after` |
| GET | `/research-runs/{id}/search-tasks` | Web/Local 与 Reflect Scout 任务 |
| GET | `/research-runs/{id}/evidence` | 当前 run 的 Fixture Evidence |
| GET | `/research-runs/{id}/report` | 完成报告；未完成为 `report_not_ready`，无报告终态为 `run_terminal` |

创建请求示例：

```json
{
  "topic": "长时储能对高比例可再生能源电网的影响",
  "dimensions": ["成本", "可靠性"],
  "output_format": "narrative",
  "sources": { "web": true, "local": true },
  "budgets": {
    "max_reflect_rounds": 1,
    "max_scout_calls": 3,
    "max_concurrent_scouts": 2,
    "max_runtime_seconds": 120
  }
}
```

`scenario` 只在服务端显式启用 `MOCK_SCENARIOS_ENABLED=true` 时接受；常规工作台不会发送该字段。Mock 下 `tokens_used` 为 `null`，不会伪造模型消耗。

## SSE

每条已保存事件的 `id` 是该 run 内递增序号，`run_events` 通过 `(run_id, sequence)` 唯一约束防止重复。初始连接从 `after=0` 回放；浏览器 EventSource 断线重连时，`Last-Event-ID` 优先于 query `after`。游标必须是非负十进制整数，且不能大于已分配序号。

游标无效时，服务器只向该连接发出无 ID 的控制消息并关闭该连接，且不写入数据库：

```text
event: stream.error
data: {"run_id":"uuid","code":"invalid_event_cursor","message":"...","recovery":"restart_from_zero"}
```

其他事件由统一的 `ResearchEvent` schema 表达，例如：

```json
{
  "id": 12,
  "run_id": "uuid",
  "event": "node.completed",
  "phase": "evidence_judge",
  "node": "evidence_judge",
  "status": "completed",
  "run_status": "running",
  "summary": "Completed evidence judge.",
  "fixture": true
}
```

终态 `run.completed`、`run.failed`、`run.cancelled` 与状态更新在一个数据库事务中提交。总事件上限为 100，非终态事件保留一个槽位给唯一终态事件。终态已回放且无后续事件后连接关闭。事件不包含模型私有推理、密钥或未净化的异常堆栈。
