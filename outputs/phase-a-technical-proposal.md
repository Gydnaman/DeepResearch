---
title: "BMAD-DeepResearch 阶段 A 技术方案"
review_status: "三轮 BMAD Review 通过；按用户条件获批进入阶段 A 实施"
date: "2026-09-24"
research: "phase-a-technical-research.md"
---

# BMAD-DeepResearch 阶段 A 技术方案

> 本文件是可评审的实现方案，不是已批准的实现指令。项目方案要求：阶段 A 的技术方案评审通过后，才开始代码、页面或依赖实施。

> **推荐决策：**沿用 Vue 3 + FastAPI + LangGraph + PostgreSQL，自建 Mock-first 模块化单体；通过固定 fixture、有限研究图和持久事件流完成无 API Key 演示。

## 目标

建立一个可本机演示的多 Agent 研究工作台骨架：从主题创建到计划预览、Mock 运行、进度、证据池和带引用报告；即使没有真实 Provider API Key，也能完整走一遍。阶段 A 证明的是状态流与产品契约，不表示系统能完成真实网络研究或其结论可信。

## 非目标

- 不接真实 LLM、Web Search、网页抓取或本地语料检索。
- 不安装 Milvus，不配置真实 API Key。
- 不做开放式浏览、无限循环、后台多 worker、自动外部操作或长期隐式记忆。
- 不复用未确认许可证的仓库代码，不 fork 已归档的 Open Deep Research。
- 不在 Mock 数据上声称研究准确率、事实覆盖率或 Provider 健康度真实。

## 方案选择

硬门槛筛选、候选仓库比较和公开证据详见 [阶段 A 开源技术调研](phase-a-technical-research.md)。

| 方案 | 取舍 | 判断 |
|---|---|---|
| A. 按现有方案自建模块化单体：LangGraph + FastAPI + PostgreSQL + Vue 3 | 保留用户已选栈；Mock 与后续 Provider 共用契约 | **推荐** |
| B. 以 Google Gemini Fullstack 示例改造 | 图工作流相似，但 React/Gemini 凭据与 Vue/Mock 目标不符 | 不采用 |
| C. 部署或重度裁剪 DeerFlow | 现成运行时能力多，但沙箱、记忆、长任务、技能和安全配置增加首版范围 | 不采用 |
| D. Fork Open Deep Research | 可参考 LangGraph 图和证据状态，但 GitHub 已归档 | 仅参考 |

## 待评审的假设

- **[ASSUMPTION] 本机开发用 Docker Compose 启 PostgreSQL。**这遵循原方案基线，但要求本机有 Docker；如果你更看重免安装演示，可在评审时切成 SQLite。
- **[ASSUMPTION] 阶段 A 只运行一个 API 进程。**数据库保存可查询历史和 SSE 事件，进程重启不会恢复进行中的 Mock graph。
- **[ASSUMPTION] 此阶段不做账号登录。**应用仅绑定 localhost；任何局域网/公网部署另行加入认证与安全评审。
- **[ASSUMPTION] shadcn-vue + Reka UI 只是候选。**精确组件在 UI/UX Pro Max 检索后再确定。

## 架构与边界

采用**模块化单体**：Vue 单页应用、FastAPI API、Research Runtime、领域/Provider 端口、PostgreSQL。阶段 A 在一个 API 进程里运行确定性 Mock 工作流；不增加 Redis、Celery 或独立 agent 服务。PostgreSQL 保存产品历史与可重放事件（ResearchRun、Evidence、Report、RunEvent）；LangGraph checkpoint 用于恢复图执行状态，阶段 A 暂不持久化 graph checkpoint。进程重启后可查看历史终态和事件，但不会恢复进行中的 Mock graph。未来如需多 worker 和恢复执行，再评审 PostgreSQL checkpointer 与后台任务编排。

前端只依赖版本化 REST/SSE 契约。API 服务调用 Application Service；Service 依赖 AgentRuntime、Provider protocols 和 repository；LangGraph 节点依赖类型化输入输出和 Protocol，不直接 import 供应商 SDK。SSE 层只从允许公开的 ResearchEvent 构造事件。

~~~mermaid
flowchart LR
  UI[Vue 3 工作台] -->|REST 创建/读取/取消| API[FastAPI API]
  UI -->|GET SSE 订阅| Stream[SSE Event Stream]
  API --> App[Run Application Service]
  App --> Runtime[Mock AgentRuntime]
  Runtime --> Graph[LangGraph StateGraph]
  Graph --> Ports[LLM / Web / Knowledge Protocols]
  Ports --> Mocks[Mock Providers + Fixtures]
  App --> DB[(PostgreSQL)]
  Stream --> DB
  DB --> UI
~~~

### 研究图执行路径

~~~mermaid
flowchart TD
  START --> ROUTER[Intent Router]
  ROUTER --> PLAN[Planner]
  PLAN --> WEB[Web Scout mock]
  PLAN --> LOCAL[Local Scout mock]
  WEB --> JUDGE[Evidence Judge]
  LOCAL --> JUDGE
  JUDGE --> ANALYST[Analyst]
  ANALYST --> REFLECT{缺口且 Reflect 未用?}
  REFLECT -->|是，至多一轮| REFLECT_NODE[Reflect]
  REFLECT_NODE --> SOURCE{按缺口选一个已启用来源}
  SOURCE -->|Web 可用| WEB
  SOURCE -->|Local 可用| LOCAL
  SOURCE -->|无可用目标 fixture| WRITER
  REFLECT -->|否或预算耗尽| WRITER[Writer]
  WRITER --> VALIDATE[Citation Validator]
  VALIDATE --> FINISH[完成或失败]
~~~

Mock Scout 从固定 fixture 读取证据，不访问网络；裁判/分析/写作也由可预测的 Mock 实现提供输出。预算耗尽、错误和取消分支必须能结束，不允许图回路无限重复。

创建请求至少启用 Web 或 Local 一个来源，否则返回 `422 no_source_enabled`。关闭的来源在初始计划中标记为 skipped 并发出 `node.skipped`；Reflect 根据缺口只选择一个已启用的 Scout，若没有可用的目标 fixture，则保留缺口并进入 Writer，不再循环。
## 阶段 A 技术栈

### 后端

- Python、FastAPI、Pydantic：服务端 API 和契约校验。
- LangGraph StateGraph：显式有向状态流程、并行 Web/Local scout、Evidence Judge、Writer、Citation Validator；一轮 Reflect 为唯一补搜分支，max_reflect_rounds=1。
- SQLAlchemy + PostgreSQL：ResearchRun、Plan、SearchTask、Evidence、Citation、Report、RunEvent 等产品元数据。PostgreSQL 保留为用户方案的基线；本机通过 Docker Compose 启动。
- SSE：采用 FastAPI 原生 EventSourceResponse/ServerSentEvent；版本在编码开始当天再次核验。事件包含递增 ID，可按 Last-Event-ID 恢复。
- 不加 Redis 或 checkpoint 数据库：阶段 A 是单进程 Mock；数据库事件记录承担 history/replay，图 checkpoint 暂缓。

### 前端

- Vue 3 + TypeScript + Vite；create-vue 作为官方脚手架，Vue Router 管理页面路径，Pinia 保存跨页面 run 与 SSE 状态。
- UI 组件候选为 shadcn-vue + Reka UI，MIT 且易于本项目掌控样式；精确组件须通过指定的 UI/UX Pro Max 检索后确认。PrimeVue 后续许可在 2026 有变化，作为备选时需重新核对当期许可。
- 第一阶段不用 Vue Flow 或 ECharts。计划预览、时间线、证据统计使用语义化 HTML、CSS/SVG 和简单进度条；出现真实的可编辑节点图或定量报告图表后再加依赖。
- 主视觉、响应式细节、键盘可达性、状态和错误恢复遵循 UI/UX Pro Max 编码前与交付前两个 Gate。

### 版本策略

本轮检索到 LangGraph 1.2.12、FastAPI 0.141.1、PostgreSQL 18.6 及 Vue 3.5.43 等版本信息，但不在此锁定。开发机最低版本建议 Python 3.11+、Node.js 20.19+ 或 22.12+（Vite 当前指南运行要求）；LangGraph 包要求 Python 3.10+，SQLAlchemy 2.0 面向 Python 3.7+，但 SQLAlchemy、LangGraph 与应用其余依赖的完整兼容组合仍须在实现启动时通过解析验证。[17][18] 实现启动时重新读取官方稳定发布、兼容性、许可证和 Node/Python 运行要求，锁入后端 lockfile、前端 lockfile 和 Compose 镜像版本。正式项目内安装官方 BMad 稳定版及 BMM；安装要求 Node.js 20.12+，实际可用工具集通过 npx bmad-method install --list-tools 确认。[14]

## 数据流与事件/API 契约

### 运行路径

1. POST /api/v1/research-runs 校验研究输入，建立状态为 planned 的 mock ResearchRun 和 fixture-backed Plan，返回 run_id，不执行研究。
2. 用户在计划预览页确认后调用 POST /api/v1/research-runs/{run_id}/start。数据库以条件更新保证只有 planned 能进入 queued 并注册一个 runtime task；重复请求返回当前 run，不创建第二个 task。若 task 注册在进程内失败，service 以条件更新把 queued 转为 failed 并写 `run.failed/runtime_failed`；若进程在状态提交后、task 注册前崩溃，API 下次启动时按 `process_restarted` 收敛遗留状态。已是终态时返回 409 `run_terminal`。
3. Run Service 建立进程内异步任务，逐阶段调用 Mock AgentRuntime；Mock Web/Knowledge providers 从固定 fixture 返回 Evidence。每个阶段把状态更新写入 run 表和 RunEvent 表。
4. 前端通过 GET /api/v1/research-runs/{run_id}/events 订阅 SSE。断线时浏览器携带 Last-Event-ID；服务只用一个游标循环，持续按 `run_id` 和 `sequence > cursor` 查询、发送并推进游标。查询不到新事件时，服务等待或轮询，再用同一游标继续查询；直到终态事件已发出且没有后续记录，以避免从历史回放转入实时订阅时漏发事件。
5. 完成时先由 ReportRenderer 构造 Report 与 Citations；Citation Validator 确认每个 citation 引用的 Evidence 属于同一个 run，且每个 section 的 `citation_ids` 与正文 `[[cite:<citation_id>]]` marker 集合完全一致、均解析到同一 Report 的 Citation。随后在终态事务中再次检查 cancel_requested。仅当取消标志为 false 时才写 Report 并以条件更新提交 completed。
6. 取消请求在 queued/running 时原子设置 cancel_requested；Mock runtime 在每个节点边界检查取消信号。终态提交使用同一 run 行的条件更新：若取消先提交，写 cancelled 且不保存成功报告；若 completed 先提交，取消请求返回已完成状态。工作台据此停止显示加载状态并提供查看终态的路径。

在计划预览页（planned、尚未启动）点击取消会直接以条件更新进入 `cancelled` 并写入唯一终态事件，不创建 runtime task。已终态取消保持幂等并返回当前状态。

### REST 路由

- GET /api/v1/research-runs?limit={1..50}&cursor={opaque}
- POST /api/v1/research-runs
- GET /api/v1/research-runs/{run_id}
- GET /api/v1/research-runs/{run_id}/plan
- POST /api/v1/research-runs/{run_id}/start
- POST /api/v1/research-runs/{run_id}/cancel
- GET /api/v1/research-runs/{run_id}/events
- GET /api/v1/research-runs/{run_id}/evidence
- GET /api/v1/research-runs/{run_id}/search-tasks
- GET /api/v1/research-runs/{run_id}/report
- GET /api/v1/providers/status

成功的 run/plan/evidence/report 响应都包含 `mode: "mock"` 与 `fixture: true`；错误 envelope 不伪装成 fixture。Phase A 的 Provider status 是本地配置状态，不表示外部连接测试成功。

#### 请求、响应与错误语义

| 路由 | 请求与成功响应 | 状态码与重复调用语义 |
|---|---|---|
| POST `/research-runs` | `ResearchRunCreate {topic, time_range?, dimensions[], output_format, sources{web,local}, scenario?}` → `{run:ResearchRunSummary,plan:Plan}` | 201；输入不合法或未启用来源返回 422 |
| GET `/research-runs` | `limit` 默认 20、最大 50；不透明 `cursor` → `{items,next_cursor}` | 200；游标无效返回 422 |
| GET `/research-runs/{id}` | `ResearchRunSummary` | 200；不存在返回 404 |
| GET `/research-runs/{id}/plan` | `Plan` | 200；不存在 run 返回 404 |
| POST `/{id}/start` | 空对象 → 当前 `ResearchRunSummary` | planned 首次调用返回 202；queued/running 重试返回 200 当前状态；终态返回 409 |
| POST `/{id}/cancel` | 空对象 → 当前 `ResearchRunSummary` | planned 直接取消返回 200；queued/running 返回 202；重复取消或已终态返回 200 当前状态；不存在返回 404 |
| GET `/{id}/events` | SSE `ResearchEvent`，以 `Last-Event-ID` 恢复；游标错误发 id-less `StreamControlMessage` | run 不存在返回 404；终态事件重放完后关闭流 |
| GET `/{id}/evidence` | 当前 run 的 Evidence 列表 | 200；不存在返回 404 |
| GET `/{id}/search-tasks` | 当前 run 的 `SearchTask[]` | 200；不存在返回 404 |
| GET `/{id}/report` | 当前 run 的 Report | 200；非终态且报告尚未生成返回 409 `report_not_ready`（可重试）；失败/取消且无报告返回 409 `run_terminal`（不可重试）；不存在返回 404 |
| GET `/providers/status` | `ProviderStatus[]` | 200 |

错误响应统一为 `{error:{code,message,retryable}}`。`message` 是可公开的摘要，不含堆栈或 secret；状态码只按上表和通用 422 输入校验返回。Vite 开发服务器将 `/api` 代理到 FastAPI，浏览器的 REST 与 SSE 使用同源 `/api` 路径；阶段 A 不启用宽泛 CORS。

`ResearchRunCreate` 输入约束：`topic` 去首尾空格后为 1–500 字符；`dimensions` 最多 12 项、每项为 1–100 字符；`output_format` 只能是 `narrative`、`executive_summary` 或 `bullet_points`；时间范围须同时提供 ISO 日期 `start/end` 且 `start <= end`；`sources` 至少有一个为 true。可选 `budgets` 字段只能收紧上限：`max_reflect_rounds` 为 0–1、`max_scout_calls` 为 1–3、`max_concurrent_scouts` 为 1–2、`max_runtime_seconds` 为 1–120、`max_tokens` 为 1–100,000；超限返回 422。Mock 路径实际 token 用量标为“不适用”，不伪造消费；额度字段为后续 Provider 和预算 UI 保留。Pydantic schema 与 OpenAPI 对这些约束保持一致。`scenario` 只用于本机开发/验收；只有服务端配置 `MOCK_SCENARIOS_ENABLED=true` 才接受该字段，默认和其它环境都拒绝显式 scenario；常规 UI 不展示它。

历史列表按 `(created_at DESC, run_id DESC)` 稳定排序。cursor 编码上一页最后一项的二元组及首次请求时捕获的 `snapshot_created_seq`；`created_seq` 由单例计数器行在创建事务内加锁、递增和提交，下一次分配必须等前一创建事务提交，确保序号提交顺序一致。下一页只读取严格早于上一页二元组且 `created_seq <= snapshot_created_seq` 的行。翻页期间新建 run 不会插入当前分页快照，用户刷新首屏即可看到新增任务；`run_id` 是相同时间戳下的稳定 tie-breaker。

#### 核心 JSON schema 字段

OpenAPI JSON schema 是唯一前后端契约来源；以下字段名/枚举为本阶段最小稳定模型，允许增加可选字段，不允许改变既有字段语义。

| 类型 | 必需字段 |
|---|---|
| `ResearchRunCreate` | `topic:string`、`time_range?:{start,end}`、`dimensions:string[]`、`output_format:string`、`sources:{web:boolean,local:boolean}`、`budgets?:{max_reflect_rounds,max_scout_calls,max_concurrent_scouts,max_runtime_seconds,max_tokens?}`、`scenario?:Scenario`（仅开发/验收使用；仅服务端显式开启时接受，不在常规 UI 暴露） |
| `Plan` | `run_id:uuid`、`questions:string[]`、`steps:PlanStep[]`、`created_at:timestamp`、`mode:"mock"`、`fixture:true`；`PlanStep={id,node,source?,status}` |
| `SearchTask` | `task_id,run_id,source:web|local,query_label,status,started_at?,completed_at?,evidence_ids[],error?`；`status=planned,skipped,queued,running,completed,failed,cancelled` |
| `Evidence` | `evidence_id,run_id,source_type,source_label,excerpt,relevance,is_duplicate,fixture`；可选 `published_at,conflict_group_id` |
| `Citation` | `citation_id,run_id,evidence_id,section_id,marker` |
| `Report` | `run_id,sections:ReportSection[]`、`fixture:true`；`ReportSection={section_id,title,body,citation_ids:string[]}`；body 中每个 `[[cite:<citation_id>]]` marker 必须解析，且不同 marker ID 集合须等于该 section 的 `citation_ids` |
| `ProviderStatus` | `provider_id,kind,mode:"mock",configured,connectivity_tested:false` |
| `ResearchEvent` | `id:int,run_id,event,phase,node?,task_id?,status,run_status,summary,fixture,created_at,error?`；`status=planned,queued,running,completed,failed,cancelled,skipped`；`error={code,message,retryable}` |
| `StreamControlMessage` | 非持久化 SSE 控制消息 `{event:"stream.error",run_id,code,message,recovery}`；`recovery=resume_from_last_processed|restart_from_zero`；不含 SSE `id`，不参与 ResearchEvent 游标 |
| `ResearchRunSummary` | `run_id,status,mode:"mock",fixture:true,created_at,updated_at,warning?,failure_code?` |

`ResearchRun.status` 使用 `planned,queued,running,completed,failed,cancelled`；SearchTask 使用其表中枚举。`Scenario` 使用 `success,no_results,partial_scout_failure,writer_error,citation_validation_error,cancel`。持久化 `event` 使用 `run.queued,run.started,plan.ready,search_task.started,search_task.completed,search_task.failed,node.started,node.completed,node.failed,node.skipped,evidence.added,budget.updated,run.completed,run.failed,run.cancelled`；所有事件均含当前 `run_status`，终态事件只允许一个。`stream.error` 是单独的非持久化控制消息，不改变 run 状态，也没有 ResearchEvent ID。

稳定错误码如下：`validation_error`（422，不可重试）、`no_source_enabled`（422，不可重试）、`run_not_found`（404，不可重试）、`run_terminal`（409，不可重试）、`report_not_ready`（409；run 非终态时可重试，终态无报告时改用 `run_terminal`）、`invalid_event_cursor`（SSE 控制消息，不可自动重试）、`source_unavailable`（单个 Scout 失败，run 可继续）、`budget_exhausted`（终态失败，不可自动重试）、`process_restarted`（终态失败，不可自动重试）、`runtime_failed`（终态失败，本阶段不自动重试）、`citation_invalid_reference`（终态失败，不可自动重试）、`internal_error`（500，不可重试）。任何重试均创建新 run；阶段 A 不对运行中的 scenario 自动重放。

### ResearchEvent 示例

~~~json
{
  "id": 12,
  "run_id": "uuid",
  "event": "node.completed",
  "phase": "evidence_review",
  "node": "evidence_judge",
  "status": "completed",
  "run_status": "running",
  "summary": "已完成证据去重与冲突标记",
  "fixture": true,
  "created_at": "ISO-8601 timestamp"
}
~~~

- id 为同一个 run 内单调递增的事件序号，并作为 SSE id。
- 初次连接若没有 `Last-Event-ID`，默认从序号 0 开始；支持可选 `after` 查询参数作为初始游标。header 或 query 游标必须是非负十进制整数且不大于该 run 已分配的 `event_sequence`；格式错误、负数或未来游标时，服务发送可供 EventSource 监听的 `stream.error` 控制消息（`code=invalid_event_cursor`）后关闭连接。控制消息没有 ID 且不落库，因此不会改变持久化事件序号。`Last-Event-ID` 存在时优先于 `after` 查询参数。
- 前端事件处理同步更新本地投影，并按 `(run_id,id)` upsert，避免显式从 0 重放时重复显示。普通网络 `error` 不主动关闭 EventSource，允许浏览器用自己的 `Last-Event-ID` 自动续连；收到 `stream.error` 时才关闭并按恢复提示创建新连接，`after` 使用前端记录的最后已处理 ID，或在用户选择“从头重放”时使用 0。
- 服务端在终态事件已发送且数据库中无后续可重放记录时关闭 SSE；前端收到 `run.completed`、`run.failed` 或 `run.cancelled` 立即关闭 EventSource，避免浏览器自动重连。
- 数据库在 `research_runs` 行上原子递增 `event_sequence` 后写入 RunEvent；递增与事件插入在同一事务中完成，并设置 `UNIQUE(run_id, sequence)`，使并发 Scout 的事件分配有序且可重放。非终态事件写入先锁 run 行并确认状态仍为 planned/queued/running，再以条件递增 `event_sequence < max_events - 1` 保留终态槽；终态更新与终态事件在同一事务完成，终态之后拒绝所有普通事件。
- `event` 是有限枚举，详见上表；`stream.error` 属于无 ID 的 SSE 控制消息，不写入 RunEvent。
- 不发送模型私有推理、API Key、原始环境变量或未净化的异常堆栈。
- 错误事件公开稳定 error code、可读摘要、是否可重试及恢复操作；完整诊断只进后端日志。

## 领域/Mock 约定

- Run、Plan、SearchTask、Evidence、Citation、ReportSection、ResearchEvent 用固定 Pydantic 类型建模；API JSON schema 作为前后端契约来源。CitationStore 提供 save/list/resolve(evidence_id)；校验强制 `citation.run_id == evidence.run_id`，数据库以 Evidence 上的 `UNIQUE(run_id,evidence_id)` 和 Citation 上的复合外键阻止跨 run 引用。Report 组装时校验每一节 marker 的引用 ID 去重集合与 `citation_ids` 完全相等，并验证每个 Citation 属于同一个 `run_id`；额外 Citation 和悬空 marker 都拒绝写库。
- Provider protocol：LLMProvider.plan/generate/stream、WebSearchProvider.search、KnowledgeProvider.search；阶段 A 只提供 Mock implementations。
- SearchTask 在创建 Plan 时按每个来源建记录：关闭来源初始为 `skipped`，启用来源为 `planned`；Scout 开始时变为 `running` 并发 `search_task.started`，结束后变为 `completed` 或 `failed` 并带 `task_id`、`evidence_ids`/稳定错误码写事件。Reflect 补搜创建一条新的 SearchTask；GET search-tasks 返回该 run 的完整任务列表，工作台不从通用 node 摘要推测 SearchTask 状态。
- AgentRuntime.run 采用异步事件迭代器语义，使 API 能一边推进运行一边写库并发出 SSE；这是对原方案一次性返回 ResearchEvent[] 的细化。
- 保留基线端口 `ReportRenderer.render(sections,citations) -> Report`；`MockReportRenderer` 实现该协议。Writer 产出章节草稿和 evidence 引用集合，Application Service 调用 renderer 组装报告与 citation marker，随后 Citation Validator 比对 marker、每节 citation ID 与 Citation 实体，校验所有 evidence 同属该 run 后才落库，避免渲染细节耦合到 LangGraph 节点。
- 预置 scenario 至少覆盖：完整成功、无结果、部分 scout 失败、writer/validation 错误、用户取消。所有最终报告都应明确标注“Mock fixture 演示”。
- 硬限制由每个 run 创建时快照的 RunBudget 控制；默认上限为一轮 Reflect、3 次 Scout 调用（初始 Web/Local 加一次补搜）、2 个 Scout 并发、120 秒和 100 个持久化事件（含唯一终态事件）。请求预算可收紧上限。每个 Scout call 最多返回 5 条且单条 excerpt 最多 1,000 字符；每个 call 最多写一条 `evidence.added` 事件，其 `evidence_ids` 列出本批条目。非终态事件写入通过同一 run 行的条件递增原子校验 `event_sequence < max_events - 1`，终态事件使用保留名额，因此并发节点无法抢占终态槽。保守路径预算为：10 个节点各有至多 started/completed 两条事件（20）+3 个 SearchTask 各 2 个状态事件（6）+`plan.ready/run.queued/run.started`（3）+每个 Scout 一条 evidence 与 budget 事件（6）+最多 2 条 skipped 事件，共不超过 37 条非终态事件；另预留唯一终态事件。方案采用 100 条总上限，拓扑或事件清单改动时须重新推导。调度器用 semaphore 强制 Scout 并发上限；开始调度节点前检查调用数与剩余时间；节点执行受剩余时长超时控制。触顶时停止后续工作并以 `failed/budget_exhausted` 写入终态。`max_tokens` 作为可选额度保存，Mock 下 `tokens_used=null`，不伪造 token 用量。

### 阶段 A 场景终态矩阵

| 场景 | 最终状态/报告 | 关键事件与错误 | 重试语义 |
|---|---|---|---|
| `success` | `completed`；报告和所有引用持久化 | `run.completed`；无错误码 | 无自动重试；新 run 可再次运行 |
| `no_results` | `completed`；报告明确说明无证据，引用列表为空；`warning=no_evidence` | `run.completed`；无错误码 | 不自动重试 |
| `partial_scout_failure` | 验收 fixture 要求 Web/Local 都启用；至少一个 Scout 成功时为 `completed`，生成部分/无证据说明并设 `warning=partial_sources`（无 Evidence 时再加 `no_evidence`） | 失败任务发 `search_task.failed` 与 `node.failed`（`source_unavailable`），run 最后发 `run.completed` | 不自动重试；提示用户可创建新 run |
| `writer_error` | `failed`；不保存部分报告 | `node.failed`、`run.failed`（`runtime_failed`） | 不自动重试 |
| `citation_validation_error` | `failed`；不保存无效报告 | `node.failed`、`run.failed`（`citation_invalid_reference`） | 不自动重试 |
| `cancel` | `cancelled`；不保存成功报告 | `run.cancelled`；无失败错误码 | 终态幂等；如要再试则新建 run |

验收 scenario `partial_scout_failure` 若只启用一个来源则返回 422 `validation_error`。正常运行中若所有启用 Scout 都失败，run 为 `failed`、无报告，发 `run.failed/runtime_failed`；若至少一个 Scout 成功但均无证据，则 Writer 仍可完成一份明确无证据的报告。发生 Writer/验证失败时，即使内存中已有报告草稿，也不能经 report endpoint 暴露为完成报告。运行终态及最终事件在同一事务内落库。

## 页面结构

1. 研究任务创建：主题、时间范围、关注维度、输出结构、来源开关、可收紧的 Reflect/Scout/时长/Token 预算和 mock 提示。
2. 计划预览：mock 子问题/搜索策略、步骤数量、开始和取消按钮。
3. 运行工作台：节点阶段时间线、SearchTask 状态、失败摘要、Scout/时长预算使用、Mock Token“不适用”状态和取消反馈。
4. 证据池：Evidence ID、来源标签、日期、摘录、相关性与重复/冲突标记。
5. 报告：章节、文内引用号、来源列表、从 citation 返回对应 fixture evidence。
6. 历史和 Provider 状态：运行模式、时间、终态、配置状态；历史列表使用 GET `/api/v1/research-runs` 游标分页；不提供浏览器 API Key 输入框。

所有页面设计在实施 Story 开始前运行指定的 UI/UX Pro Max 的 design-system、UX 和 Vue 检索；Master 已存在时先阅读，不覆盖。

## 错误、取消与安全边界

- Run 状态：planned → queued → running → completed | failed | cancelled；planned 也可直接转 cancelled。写状态与事件使用同一事务或 outbox-style 写入，防止 UI 收到不存在的事件。
- API 进程启动时，在接收请求前将遗留的 queued/running run 标记为 `failed`（`failure_code=process_restarted`），并在同一事务写入 `run.failed` 事件；阶段 A 明确不恢复 graph。任务注册本身若返回异常，也以 queued 状态条件更新写 `runtime_failed`；状态提交后进程崩溃则由下次启动扫描收敛。
- 每个事件只包含可公开的摘要和明确阶段；fixture 数据含固定来源映射。
- cancel 对终态幂等返回当前终态；queued run 在启动前检查 cancel_requested 并直接转为 cancelled，running run 在下一节点边界停止，报告不会被标为成功。Mock node 的最长阻塞时间应受配置限制。
- 取消与完成通过终态条件更新竞争，只允许一个终态落库；保存报告也必须在确认未取消的事务中完成。非终态节点写入须确认 run 仍未终态，防止迟到的 Scout 事件排到 terminal event 之后。
- graph recursion、provider calls、并发数、总时长均有硬上限；Reflect 上限为一。
- API 只监听 localhost 开发绑定；Docker Compose PostgreSQL 端口必须映射到 `127.0.0.1`，或仅留在内部 Compose network，不可绑定 `0.0.0.0`。若后续暴露到局域网/公网，需先做独立认证、CSRF/CORS 和部署安全评审。
- secret 留在服务器端；阶段 A 不要求 secret。后续 provider 的 base_url/model/secret/timeout 来自服务器端配置并做日志脱敏。

## 验收与验证方法

实现完成后（本方案批准后）按以下条目人工/自动核验；本轮不执行实现测试：

- 从无 API Key 的新环境启动演示，能从新建任务到 Mock 报告。
- 所有结果明确显示 mock/fixture；报告来源只能引用当前 run 的 Evidence ID。
- 拒绝跨 run Evidence ID；来源开关对 Scout、计划和 SearchTask 有可观察影响。
- GET search-tasks 返回 Web/Local 初始任务和 Reflect 补搜任务；关闭来源为 skipped，运行中/失败/完成状态由任务记录和带 task_id 的事件一致表达。
- 正常、无结果、部分 scout 失败、validation 失败和取消都能进入合理终态；取消后无“成功”报告。
- 重复 start 只启动一个 runtime task；进程重启后 queued/running run 有明确的 failed 终态与事件；取消和完成竞争只提交一个终态。
- 至多一次 Reflect；预算、并发、事件数、Evidence 数量/摘录长度和运行时长配置不可绕过。
- SSE 初次连接从 0 回放；断线后可用 Last-Event-ID 补发；非法游标会给出可恢复的错误并关闭 EventSource，事件 ID 有序且不含私有推理或 secret；收到终态事件后前端关闭连接。
- 历史列表按 `(created_at,run_id)` 做 keyset 分页并使用 `created_seq` 快照水位；翻页时新建的 run 不会插入当前游标页，刷新列表可见。
- DTO 校验拒绝空主题、超长主题/维度、未知输出格式、无效日期顺序、无来源输入；scenario fixture 开关未启用时，API 拒绝客户端显式选择 scenario。
- 若 Reflect 所选来源没有可用 fixture，则不发起 Scout、不无限重试，直接经 Writer 产出带缺口说明的报告。
- 页面含空、加载、失败和禁用/取消状态，窄屏无横向溢出；键盘可达，并提供清晰的焦点指示、表单错误和错误恢复提示。
- Provider 替换不改变前端 API response schemas；Provider 健康状态清楚写明是 Mock 配置状态。
- README 演示脚本解释这是 Mock 流程，不是经过真实来源验证的研究。

## 风险与回退

| 风险 | 控制 | 回退路线 |
|---|---|---|
| Mock 报告被误解为真实研究 | 页面、事件与报告统一带 Mock 标签；引用只指向 fixtures | 禁止关闭标签，直到真实 Provider 通过 B 阶段评审 |
| 使用归档代码产生维护/许可问题 | 只读 Open Deep Research 文档和状态流，不复制代码 | 用 LangGraph 当前文档和自建 contracts 替代 |
| PostgreSQL 让首次运行变重 | Compose 提供本地 PG；Schema/Repo 边界隔离存储 | 若演示环境无法承担 PostgreSQL，先修订方案并重新评审，不能在实现中自行换 SQLite |
| SSE/Event/Graph state 结构串在一起 | 以 Pydantic ResearchEvent 做唯一公开事件契约 | 固定 adapter mapper，避免暴露 LangGraph event 原始载荷 |
| 前端套件维护或许可变动 | 使用按需复制的 MIT 组件，安装前复核 Reka/shadcn-vue | 用语义 HTML + 本地 Vue 组件 |
| 取消只取消 UI 订阅，任务仍执行 | API 取消任务并在节点边界检查信号 | 若进程级取消不可靠，保留 cancel 标记并由 runtime 明确返回终态 |

## 任务拆分

收到批准后按依赖顺序制定详细实现计划：

1. 新建独立项目目录；安装官方稳定 BMad Method 与 BMM；产出 brief/PRD/UX/架构与 Story/readiness 文件，保持其与用户方案一致。
2. 建立后端与 Vue 工作区、锁定阶段 A 的当前依赖版本、启动 Compose PostgreSQL 和迁移脚手架。
3. 实现领域 schema、repository、REST API 和 ResearchEvent 契约。
4. 实现 Mock fixtures、Provider adapters、有限 LangGraph graph、运行控制和可取消 AgentRuntime。
5. 执行 UI/UX Pro Max 编码前 Gate，完成页面骨架和所有 mock/error/empty states。
6. 接通 REST/SSE、历史、报告证据回跳与 Provider 状态。
7. 按验收列表走查，更新 README、API/event 文档和演示脚本，再走 UI/UX Pro Max 交付 Gate 与 code review。

## 评审批注

此技术方案采用用户已有的 Vue 3、FastAPI、SSE、LangGraph 和 PostgreSQL 基线。唯一明显细化是 Phase A 的 AgentRuntime 使用异步事件迭代器，支持实时进度而不是一次性返回事件数组。版本、视觉组件细节以及未来 Provider 不在此提前锁定。

**方案状态：三轮 BMAD Review 已通过。**Adversarial、edge-case、structure 与 prose 视角均完成复核，Round 3 修订项已回填并核对；按用户“无问题就通过”的指示，阶段 A 技术方案获批，进入代码、页面与依赖实施。
