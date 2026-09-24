---
title: 'DeepResearch 阶段 A 可运行 Mock 研究演示'
type: 'feature'
created: '2026-09-24'
status: 'done'
route: 'dispatch'
review_loop_iteration: 3
baseline_commit: 'a1d0e88aedd6780909afafc5d74ee20eff8ca1ed'
context:
  - 'outputs/phase-a-technical-proposal.md'
  - 'outputs/phase-a-technical-research.md'
  - 'design-system/deepresearch/MASTER.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** DeepResearch 目前只有获批的技术方案，没有可启动、可观察、可复现的研究工作台；因此还不能演示多 Agent 状态流、证据追溯或 Mock 与真实能力的边界。

**Approach:** 在独立仓库实现一个无第三方凭据的阶段 A 演示，从创建研究任务、预览计划、启动受限 Mock 图到查看事件、证据和带引用报告。后端以 FastAPI、LangGraph、SQLAlchemy/PostgreSQL 和固定 Provider fixtures 提供稳定 REST/SSE 契约，Vue 3 工作台消费同一契约。

## Boundaries & Constraints

**Always:** 结果、报告、事件和 Provider 状态清楚标记 Mock/fixture；引用只能解析到同一 run 的 Evidence；工作流、Scout 并发、补搜次数、事件数与运行时间有硬上限；REST/OpenAPI 是前后端契约来源；本地服务只绑定 localhost，PostgreSQL 端口只映射到 127.0.0.1。

**Never:** 不接真实 LLM、Web Search、网页抓取或真实语料；不暴露或要求浏览器 API key；不复制归档仓库代码；不引入无限 Agent 循环、Redis、后台多 worker 或未获批的 SQLite 替代；不宣称 fixture 报告具有真实研究准确性。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Successful mock run | Valid topic, at least one source, success fixture | planned → completed; run history, ordered events, evidence, citations, report are queryable | Any citation that is missing or belongs to another run fails validation |
| No evidence / partial scout failure | no_results or both sources enabled with one failing | A clearly labelled completed report explains the evidence gap; task and event states identify the failed source | If every enabled Scout fails, run becomes failed and no report is exposed |
| Cancel / duplicate start | Cancel planned or running run; repeat start while queued/running | Cancellation has one terminal event and no success report; repeated start registers one runtime task | Terminal operations return stable current state |
| Stream recovery | Reconnect with valid Last-Event-ID or invalid/future cursor | Persisted events replay in order without duplicate UI rows | Invalid cursor emits an id-less stream control error and closes only that subscription |
| Invalid input | Empty/oversized topic, invalid date order, no sources, unsupported format or disabled scenario | API rejects request before creating a run | Typed 422 error with safe, actionable message |

</frozen-after-approval>

## Code Map

- outputs/phase-a-technical-proposal.md — approved architecture, exact API/event/error semantics, data bounds, test and delivery requirements.
- outputs/phase-a-technical-research.md — source-backed project and dependency research; recheck official releases and licenses before installation.
- design-system/deepresearch/MASTER.md — persisted UI/UX Pro Max recommendations; use as design source of truth.
- backend/, frontend/ and deployment files contain the implemented Phase A demo; local `.agents/` and `_bmad/` workflow installations are Git-ignored, while project-owned BMad artifacts remain in `_bmad-output/`.

## Tasks & Acceptance

**Execution:**
- [x] _bmad-output/planning-artifacts/ — author the phase-A brief, PRD, DESIGN.md, EXPERIENCE.md, ARCHITECTURE-SPINE.md, epics/stories and readiness using the approved proposal and UI design rules.
- [x] backend/ — implement typed domain DTOs, SQLAlchemy/PostgreSQL persistence and migrations, repositories, FastAPI REST/OpenAPI routes, safe errors and resumable SSE.
- [x] backend/ — implement Provider protocols, deterministic fixtures, bounded LangGraph and cancellable runtime; persist run, SearchTask, Evidence, Citation, Report and ordered events.
- [x] frontend/ — implement accessible Vue 3/TypeScript task form, plan preview, live run workspace, evidence/report/history/provider views against generated API types.
- [x] docker-compose.yml, .env.example, scripts and README.md — provide localhost-only PostgreSQL and reproducible mock demo; never require secrets.
- [x] tests/ — add contract, domain, persistence, graph, API/SSE and frontend acceptance coverage, including edge cases in the matrix above.

**Acceptance Criteria:**
- Given a clean local setup with PostgreSQL available and no provider credentials, when the user follows README, then the frontend and API start and a mock run can complete end-to-end.
- Given valid input, when a run is created and started, then the plan, status, bounded ordered events, SearchTasks and fixture Evidence are queryable over the documented API.
- Given a completed run, when the report is loaded, then each citation resolves to an Evidence record from that run and every report section’s markers match its citation IDs.
- Given cancellation, duplicate start, process restart or a failing scenario, when the runtime reaches the corresponding boundary, then exactly one valid terminal state/event is persisted and partial reports are not exposed.
- Given an SSE reconnect or invalid cursor, when the client subscribes, then events resume idempotently or a safe recovery control message is returned without corrupting persistent sequence numbers.
- Given desktop, tablet and 375px viewports, when users navigate by keyboard or pointer, then core flows work without horizontal overflow; loading, empty, failed, disabled, cancelled and mock states are visibly and accessibly explained.

## Implementation Notes

## Spec Change Log

## Review Triage Log
### BMad Build Review · 2026-09-24

每条原始发现独立核验并记录；重复根因只在后续修补分组，不合并或丢弃审查记录。
本节的 `patch` 是发现时的处置建议；当前关闭状态以 Round 3 的最终闭环表为准。

- **B1 — medium / patch** — service.py 把日期范围持久化后没有传入 Graph 或筛选 Provider 结果；Graph 输入与 _build_report 均未使用它，现有 API 测试也没有日期边界断言。
- **B2 — medium / patch** — 固定能源储能语料会被用于任意主题；Provider 将用户主题拼进不相关的事实句，且以真实机构名作为 Fixture 标签，报告可能显得主题匹配。将占位语料改为明确非事实的合成材料。
- **B3 — false** — partial_scout_failure 的失败用例把 max_scout_calls 设为 1；Graph 按硬预算只尝试一个 Scout，现有 API 测试明确断言另一任务为 skipped。放宽预算会违反获批的调用上限，因此这不是已证明的实现缺陷。
- **B4 — medium / patch** — Reflect SearchTask 在 Graph 完成后才创建；随后又在通用任务循环和显式 Reflect 分支中各完成、各发事件一次。将创建/started 事件挂到 Reflect 节点开始时，并只完成一次。
- **B5 — medium / patch** — 通用任务循环以 source_type 分配全部证据，初始 Scout 与 Reflect 会共享同源证据。给每条 Graph 证据保留调用阶段，并只关联它实际归属的 Scout。
- **B6 — medium / patch** — SSE stream 在轮询数据库时只 sleep，不发送注释心跳；planned run 或长耗时运行会保持无数据连接。增加定时 SSE comment keep-alive。
- **B7 — medium / patch** — 前端 EventSource 未监听 node.started、node.skipped、evidence.added、budget.updated，这些服务端持久事件不会出现在时间线。补齐事件订阅并覆盖消费逻辑。
- **B8 — medium / patch** — stream.error 处理只展示消息并关闭 EventSource，没有按 recovery=restart_from_zero 建立新连接；无效游标恢复契约未落到 UI。关闭后从服务端给出的恢复点重新订阅。
- **B9 — medium / patch** — 计划将 Web/Local 列为两个步骤，而 Graph 的 Scout 是一个节点；默认双源成功运行的完成节点数低于步骤总数，进度条无法到 100%。
- **B10 — medium / patch** — 历史项调用 openRun 和“新建研究”重置状态都不更新路由；/runs/:id 深链接虽能加载，但从历史选择后刷新无法保留选择。
- **V1 — medium / patch** — 现有 HomeView 测试只校验前端拦截的无效输入，没有有效提交的请求体断言；后端 API 测试直接构造请求，无法守住 UI 字段映射。添加成功提交测试验证来源、格式、预算与时间范围。
- **V2 — medium / patch** — 后端测试确认服务端会发 node.skipped，但仓库中没有前端事件 store 测试；consumeEvent 未处理该事件的行为因此未被前端测试守住。
- **E1 — low / patch** — SSE 游标先以正则接受任意位数数字再调用 int()；Python 的十进制位数限制会让超长游标抛 ValueError，破坏该连接并返回 500。先用去前导零的字符串长度/字典序与当前序号比较。
- **E2 — medium / patch** — 启动恢复把 stranded run 标记 failed，却不更新它的 planned/running SearchTask；现有恢复测试只断言 Run 状态和事件，没有检查任务历史。事务内同步把这些任务置 failed 并写入错误码。
- **E3 — medium / patch** — 日期范围无法排除 Fixture 日期；检查 RunCreate 入库后重建请求仍保留范围，但 Graph/provider 搜索路径没有读取该字段。
- **E4 — medium / patch** — 与 B7 同一根因：已持久化的自定义事件缺少 EventSource listener，生产者会发出而 UI 不会消费。
- **E5 — medium / patch** — openRun 并发请求在每次 await 后直接改 store；快速切换时较早发出的慢请求可覆盖最后选择的 run。使用递增请求序号，只允许最新请求写入状态或建流。
- **E6 — medium / patch** — 与 B9 同一根因：进度把 Graph 节点完成数除以 Plan 步骤数，两个来源映射到单一 scouts 节点时比例不一致。
- **E7 — medium / patch** — 实现任务要求由 OpenAPI 生成前端类型，但 frontend/src/api/types.ts 是手写接口且没有生成/一致性检查脚本。补充可重复的 OpenAPI 类型生成和验证。
- **E8 — medium / patch** — 375px 断点隐藏 .sidebar-history，同时仍显示指向该区域的“研究历史”导航；移动端没有其他历史列表入口，违反核心流程可达性。
- **E9 — medium / patch** — 422 handler 丢弃验证错误位置和说明，只返回“字段无效或超出范围”的通用消息；例如维度数量超限时用户不知道需要修正哪个字段。返回不含输入值的字段与约束说明。

**分组与路由**

- **G1：时间范围过滤（B1、E3）→ patch。** 同一缺失字段传递/筛选行为。
- **G2：事件时间线（B7、V2、E4）→ patch。** 同一事件监听遗漏；按每条发现保留独立记录，修补时共用事件枚举和消费测试。
- **G3：进度计算（B9、E6）→ patch。** 同一 Plan/Graph 粒度不一致。
- **其余 findings 各自 patch；B3 false。** 暂无 intent_gap 或 bad_spec；所有真问题均由现有规格和 API 事件契约明确约束。

### BMad Build Review · Round 2 · 2026-09-24

Round 2 复核确认上一轮修复均已落入实现；本轮发现以下剩余问题，并在 Round 2 修补、Round 3 回归复核。相同根因仍逐项记录，不把不同审查视角合并成单条发现。

- **B11 — patch** — 从 `/runs/A` 提交新研究 B 后，store 显示 B，但 URL 仍指向 A；刷新会重新加载旧 run，深链接状态不一致。
- **B12 — patch** — `openRun` 的 request 序号未保护由事件触发的详情刷新及 `startRun`/`cancelRun` 回写；切换 run 后迟到响应仍可覆盖当前 store。
- **B13 — patch** — 类型生成器已加入，但 OpenAPI 的 422 仍声明默认 `HTTPValidationError`，运行时实际返回 `ErrorEnvelope`；SSE 200 schema 也遗漏 `stream.error` 的 `StreamControlMessage`。
- **E10 — patch** — 若任务完成/失败后的 Run Event 与详情 fetch 乱序返回，较早的 `search_task.*` 刷新可能覆盖 terminal run 的任务、证据与报告状态。
- **E11 — patch** — create/start/cancel 请求等待期间切换 run，旧响应可以写回新选择；新建请求被“新建研究”取消时还可能残留 busy 状态。
- **E12 — patch** — start 提交 queued 后、runtime task 注册前取消，会终止 Run，却使预建 SearchTask 保持 planned。
- **E13 — patch** — 移动端“数据源状态”导航锚点仍指向被隐藏的 sidebar 区域；可见的 provider 状态条没有对应 id。
- **E14 — patch** — 将 `#providers` id 添加到 provider-strip 后，该 strip 仍处于 `v-if currentRun` 内；空白工作台没有锚点目标。把该可见状态条移到 run 条件区外，并检查无 run 页面。
- **V3 — patch** — 日期测试只证明越界范围会返回空结果；增加在范围内证据与报告引用的正向断言。
- **V4 — patch** — partial Scout failure 测试只检查状态；增加报告 warning 和“覆盖范围有限”说明的断言。

**Round 2 grouping:** B12、E10、E11 → 当前 run 的异步写入保护；B13 → REST/SSE 错误契约文档；E13/E14 → 移动端锚点及空白页可达性；E12 → queued cancel 状态同步；V3/V4 → 增加正向报告行为断言。所有项均依据获批的深链、OpenAPI 来源、任务生命周期、响应式可用性与报告说明要求判定为 patch；暂无 intent_gap / bad_spec。
以上 `patch` 记录同样描述发现时的处置；修复后状态与证据见 Round 3 最终闭环表。

### BMad Build Review · Round 3 · 2026-09-24

Round 3 发现并修复以下问题；修补后新增的回归用例通过。

- **B14 — low / fixed** — “加载更多历史”在同一 cursor 请求未完成时可重复请求并重复插入相同 run；较慢分页还可在较新的刷新之后覆盖列表；两个完整刷新重叠时较早请求的 finally 也不能提前开放分页。按 cursor 去重、仅允许最新请求清理刷新锁、以请求序号拒绝过期响应，追加页按 run_id 去重。回归：`frontend/src/stores/__tests__/research.spec.ts` 中 “deduplicates concurrent history page requests for the same cursor”、“does not let an older history page overwrite a newer refresh” 和 “keeps pagination blocked until the latest overlapping history refresh finishes”。
- **E15 — blocking / fixed** — `/start` 的 queued 响应若晚于 SSE 终态事件和详情刷新，会把已结束的 run 回写为 queued 并重连。仅当当前状态未前进时应用响应，并且只对 queued/running 状态连接。回归：`frontend/src/stores/__tests__/research.spec.ts` 中 “does not let a late start response replace a terminal event or reconnect”。
- **V5 — P2 / fixed** — Round 2 的规格 triage 没有关闭状态与证据链接，测试覆盖清单未勾选。已勾选实现清单，并在本节为各轮结果记录关闭状态及测试文件证据。
- **V6 — P2 / fixed** — E13/E14 的闭环表未链接实际断言空白页 Provider 锚点的用例。已将证据指向 `frontend/src/views/__tests__/HomeView.spec.ts` 的 “keeps the data source navigation target in the visible provider strip”。
- **V7 — P2 / fixed** — Verification 文档误写不存在的 `typecheck` 和 `test` npm scripts。已改为 `build`（执行 type-check 与生产构建）及 `test:unit`，与 `frontend/package.json` 一致。
- **V8 — P2 / fixed** — E5（异步 run 选择保护）的闭环表误将其重复归到后端测试行。已将证据归属统一放在 `frontend/src/stores/__tests__/research.spec.ts`。

**最终闭环：** B1–B2、B4–B14、E1–E15、V1–V8 均已修复并由对应回归用例或文档证据覆盖；B3 经核验为 false（维持 `max_scout_calls=1` 硬上限）。Round 1/2/3 实现与验证问题均为 fixed 或 false；没有未关闭的 actionable findings。

| 发现 | 关闭状态与验证证据 |
|---|---|
| B1、E3、V3 | fixed — 日期边界与范围内证据/引用断言；`backend/tests/test_api.py` |
| B2、B3 | B2 fixed — 合成 fixture 边界；`backend/tests/test_api.py`。B3 false — 预算硬上限及 skipped 任务行为由 `backend/tests/test_api.py` 覆盖 |
| B4–B5、E2、E12 | fixed — Graph 任务生命周期、归属、启动恢复与取消收尾；`backend/tests/test_api.py` |
| B6、E1–E2 | fixed — SSE 心跳、游标边界、恢复状态；`backend/tests/test_api.py` |
| B7–B8、V2、B12、E5、E10–E11、E15 | fixed — 事件消费、恢复连接、乱序详情/动作回写和终态竞争；`frontend/src/stores/__tests__/research.spec.ts` |
| B9、E6 | fixed — 进度按可见步骤完成；`frontend/src/views/__tests__/HomeView.spec.ts` |
| B10–B11 | fixed — 路由深链与创建后导航；`frontend/src/views/__tests__/HomeView.spec.ts`、`frontend/src/__tests__/App.spec.ts` |
| V1 | fixed — 有效表单请求 payload；`frontend/src/views/__tests__/HomeView.spec.ts` |
| B13 | fixed — REST 错误、SSE 控制消息和 409 范围的 OpenAPI 契约及类型生成；`backend/tests/test_openapi_generated_types.py`、`frontend/src/api/types.ts` |
| E7 | fixed — API 类型生成与漂移检查；`backend/tests/test_openapi_generated_types.py`、`frontend/package.json` |
| E8 | fixed — 移动端历史列表可达；`frontend/src/__tests__/App.spec.ts` |
| E9 | fixed — 字段化安全错误；`backend/tests/test_api.py` |
| E13–E14 | fixed — Provider 锚点位于 HomeView 的可见状态条；空白首页断言见 `frontend/src/views/__tests__/HomeView.spec.ts` |
| B14 | fixed — 同游标并发、过期分页、重叠刷新期间禁止分页和 run_id 去重；`frontend/src/stores/__tests__/research.spec.ts` |
| V4 | fixed — partial Scout failure 的 warning 与覆盖范围说明；`backend/tests/test_api.py` |
| V5 | fixed — 本节记录 triage 关闭状态与测试证据；本规格 |
| V6 | fixed — Provider 锚点的测试证据指向真实断言；`frontend/src/views/__tests__/HomeView.spec.ts` |
| V7 | fixed — 命令已与 `frontend/package.json` scripts 对齐；本规格及 `frontend/package.json` |
| V8 | fixed — E5 证据归属已更正为前端 store 回归用例；`frontend/src/stores/__tests__/research.spec.ts` |

### Verification boundary

本机自动验证可在 SQLite 临时数据库上运行。Docker Compose 配置检查通过，但 Docker Engine 未启动，因此 PostgreSQL 容器集成与部署态端到端验证未运行；也未完成真实浏览器 375/768/1024/1440px 视觉检查。前端验证最终使用 Node 24.19.0（满足 package engine 声明）。

## Design Notes

Use the persisted dense dashboard system with institutional navy and research accent, semantic neutral/status tokens, Fira Sans body text and subdued Fira Code only for technical metadata. Keep motion subtle and honor reduced-motion; use semantic HTML/SVG icons, visible keyboard focus, labelled form controls and explicit empty/loading/error recovery states. This visual direction is derived from the requested analyst evidence dashboard; do not add marketing content or fictional testimonials.

## Verification

**Commands:**
- uv run --cache-dir ./.uv-cache --directory backend pytest — expected: all unit, contract, repository and API tests pass.
- npm --prefix frontend run build — expected: type-check and production bundle build pass.
- npm --prefix frontend run test:unit — expected: UI interaction/state tests pass.
- npm --prefix frontend run check:api-types — expected: generated frontend API types match the OpenAPI schema.
- docker compose config --quiet — expected: valid Compose config with database bound only to localhost.
- Optional runtime check, requires Docker Engine: docker compose up -d db, then backend PostgreSQL integration tests — expected: migrations and PostgreSQL persistence pass.

**Manual checks:**
- Follow README from a fresh checkout; complete success, no-evidence, partial-failure and cancel demos.
- Verify citation-to-evidence navigation, event replay, mock labels, keyboard focus and responsive layout at 375px, 768px, 1024px and 1440px.
