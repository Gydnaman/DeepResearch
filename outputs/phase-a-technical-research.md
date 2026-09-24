---
title: "BMAD-DeepResearch 阶段 A 开源技术调研"
accessed: 2026-09-24
status: "review-ready"
decision: "为 Mock-first 阶段 A 选择可替换、可追溯的全栈实现底座"
---

# BMAD-DeepResearch 阶段 A 开源技术调研

> 调研日期：2026-09-24。本文只使用本轮检索到的公开资料；项目方案用于界定问题和硬约束，不作为技术事实来源。依赖版本、兼容性和许可证需在阶段实现启动当天复核。

## 执行摘要

建议按原方案自建一个模块化单体，而不是 fork 现有研究 Agent：后端采用 Python、FastAPI、LangGraph 和 PostgreSQL；前端保留 Vue 3、TypeScript 与 Vite；阶段 A 只走固定 fixture 和 Mock Provider，使用 SSE 推送类型化进度事件，并把运行事件和证据元数据落入 PostgreSQL。研究图限制为一轮 Reflect，所有报告引用都必须解析到 Evidence ID。

现有项目验证了 LangGraph + FastAPI + 前端工作台的路线。补充检索发现一个 Vue 3 + FastAPI + LangGraph 项目，但仓库当前规模很小，未确认到许可证或发行版，也没有证明满足无密钥演示和可靠引用契约；另一个 Vue 3 + FastAPI + SSE 项目使用 LangChain 而非 LangGraph，并要求外部模型/搜索配置。因此尚未确认有满足本项目硬门槛且适合直接采用的成熟完整项目。最相近项目可借鉴状态图、事件流和引用语义，不宜直接作为阶段 A 底座。LangChain 的 Open Deep Research 已于 2026-08-21 归档；DeerFlow 已扩展成带沙箱、记忆和技能的通用 Agent harness；Google 示例把研究搜索绑定到 Gemini API key。[1][2][3][15][16]

阶段 A 的版本只作调研快照，不是锁定清单。编程开始前应按原方案再次核验官方稳定版本并生成 lockfile。

## 需求框架与评估标准

- **硬门槛：**Vue 3；无 API Key 可启动；Mock/fixture 覆盖计划、进度、证据、报告；有硬停止条件；所有引用绑定证据 ID；API key 不进浏览器。
- **比较偏好：**优先满足阶段目标与无密钥演示，其次看接口可替换性、许可/维护证据和运行复杂度；每项结论区分仓库事实与方案判断。
- **决策方法：**先用硬门槛筛掉无法直接采用的仓库，再依据公开证据作定性选择。本轮不报告未实现方案的精确适配分数，也不把项目质量或性能伪装成量化测量。

## GitHub 项目对比

### 检索范围与纳入规则

本次于 2026-09-24 做了定向 GitHub 网页检索，使用的关键词包括 `"deep research" "Vue" "LangGraph"`、`"research agent" "Vue 3" FastAPI LangGraph` 和 `"AI research assistant" Vue evidence citations LangGraph`。随后查看候选仓库的 README、可见目录/许可证文件、Release 与页面展示的提交/活跃度线索；技术能力以仓库自身资料为主，未运行候选项目，也未审计其代码。该检索是关键词抽样，不是 GitHub 全量爬取或质量认证。纳入对比要求与研究流程或全栈运行方式直接相关；是否采用还要通过 Vue、无密钥演示、Mock/fixture、引用可追溯等项目硬门槛。页面未显示某项资料只表示本轮未确认，不证明仓库一定不存在该资料。

本轮找到的 Vue 3 项目说明相关尝试确实存在；但没有确认到兼具硬门槛和足够许可/维护证据的 Vue 3 研究工作台。项目已经把 Vue 3 定为硬约束，故保留 Vue，并继续自建窄应用。

| 项目 | 检索到的技术与能力 | 状态/许可证 | 借鉴点 | 不直接采用的原因 |
|---|---|---|---|---|
| [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research) | LangGraph、结构化研究状态、多种模型/搜索配置、并行研究和引用产物；主要通过 LangGraph Studio / Open Agent Platform 使用 | MIT；GitHub 标记为 2026-08-21 归档，只读。[1] | 图状态、并行研究、引用和结构化输出 | 已归档；没有与本方案匹配的 Vue 工作台；仅作设计参考，不作为活跃依赖 |
| [Google Gemini Fullstack LangGraph Quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart) | React + Vite；FastAPI + LangGraph；生成搜索词、反思缺口、循环补搜并生成引文；部署说明使用 PostgreSQL + Redis | Apache-2.0；官方示例。[2] | 计划/搜索/反思/报告状态图，以及全栈拆分 | Gemini API key 是启动前置；前端是 React；生产部署引入 Redis 与 LangGraph Server 基础设施，超出 Mock 阶段需要 |
| [ByteDance DeerFlow](https://github.com/bytedance/deer-flow) | LangGraph/LangChain、FastAPI Gateway、Next.js、SQLite 或 PostgreSQL 部署方式、持久运行事件流；2.0 是从头重写的通用 SuperAgent harness | MIT；2.0.0 于 2026-06-25 发布，主仓库继续开发。[3] | 事件序号、流式运行状态、安全边界与模块化参考 | 沙箱、记忆、文件系统、技能和长任务会扩大首版复杂度；默认设计面向可信本地部署环境 |
| [LearningCircuit/local-deep-research](https://github.com/LearningCircuit/local-deep-research) | LangGraph 研究、来源/引用、Web UI、REST、WebSocket 实时进度 | MIT；版本 1.10.7 发布于 2026-08-28。[4] | 引用去重仍保留不同摘录、来源映射与进度 UI 的设计线索 | 产品能力较多且采用 WebSocket；阶段 A 应更窄并遵循 SSE 契约 |
| [AbhiGupta1310/Deep-Research-AI-Agent](https://github.com/AbhiGupta1310/Deep-Research-AI-Agent) | README 声称 LangGraph、FastAPI、React、Pydantic、SSE 与计划复核 | 本轮查看页未看到许可证声明或 Release，仓库体量较小。[5] | 可当作接近全栈研究演示的搜索线索 | README 主张未独立验证；未确认许可前不复用代码 |
| [oi1784105-spec/DeepResearch](https://github.com/oi1784105-spec/DeepResearch) | README 列出 Vue 3、TypeScript、Vite、FastAPI、SQLite、LangChain 与 LangGraph；提供研究工作台方向 | 检索时仓库页显示 3 commits、1 star；文件列表未见 LICENSE 或 Release，许可证与维护承诺未确认。[15] | 可对照 Vue/FastAPI/LangGraph 的页面与服务拆分 | README 未证明无密钥端到端流程、引用校验或可复用许可；仓库成熟度证据有限，不纳入可采用候选 |
| [Moe2233L/Agent-serach](https://github.com/Moe2233L/Agent-serach) | README 列出 Vue 3、FastAPI、SSE 和 LangChain；需要 OpenAI-compatible API key，并依赖 DDGS/代理进行搜索 | MIT；检索时仓库页显示 34 commits、2 stars，未见 Releases。[16] | Vue + FastAPI + SSE 的前端进度流可供参考 | 不是 LangGraph 架构，也不是无密钥 Mock-first；不满足阶段 A 的无凭据演示硬门槛 |

## 技术发现

### 图编排和进度

LangGraph 当前文档支持类型化 StateGraph、条件路由、并行节点，以及 updates/custom 模式传递节点状态和自定义进度。官方文档提醒完整 values 流会暴露整个状态，因此应用不能直接把 graph state 当作前端事件发出。[6]

FastAPI 已提供原生 SSE 响应类。官方实现包含 15 秒 keep-alive、禁止缓存及关闭反向代理缓冲等实践；浏览器原生 EventSource 以 URL 订阅，因此“创建任务、随后打开 GET 事件流、用 POST 取消”比把创建和流式响应放在一个 POST 更直接。使用事件 ID 和 Last-Event-ID 可以在断线后补发已持久化的事件。[7]

推荐由后端把 LangGraph 输出转换为窄的 ResearchEvent schema，不能传递私有推理文本、provider secret 或任意完整 Graph State。

### 运行记录与数据库

不同职责应分开：ResearchRun / Evidence / Report / RunEvent 面向产品历史和审计；LangGraph checkpoint 面向恢复图执行状态。阶段 A 的 Mock 流程没有跨进程恢复要求，因此先保留 PostgreSQL 产品数据和事件日志；图状态运行时驻留内存，不在首版增加独立 checkpoint/Redis/队列服务。进程重启后可以查看历史终态和事件，但不会恢复进行中的 Mock graph。未来需要多 worker、跨重启续跑时，再评估 PostgreSQL checkpointer 和任务调度。[8]

SQLite 是可行的本地演示选项，相关参考项目已有使用；但用户方案已把 PostgreSQL 定为任务和证据元数据基线，本方案沿用该决定。为降低本地设置阻力，技术方案建议通过 Docker Compose 启动 PostgreSQL，并让应用本身在无第三方 API Key 条件下工作。SQLite 可作为用户评审时的替代选项，不能在实现中静默替换基线。

### Vue 工作台与组件

Vue 官方建议使用 create-vue 生成 Vite 项目；官方 TypeScript 指南说明 Vue SFC 应使用 vue-tsc 等工具独立做类型检查。Pinia 是 Vue 官方推荐的状态管理方案，可把跨页面的运行进度与选中任务保持在单一 typed store。[9]

自定义分析工作台的组件候选：

- **shadcn-vue + Reka UI：**MIT、组件源码可按需进入项目并自行定制，适合由 UI/UX Pro Max 建立自己的 token 和视觉层级；代价是复杂 DataTable 需要自行组合。[10]
- **PrimeVue：**提供大量现成控件，但 2026 年活跃开发与授权路径迁移至 PrimeUI，PrimeVue 旧版本继续保持 MIT，后续版本需留意新许可边界。首选它之前必须再确认当时的 Community License 条件。[11]

阶段 A 的计划预览和运行时间线先用语义列表、状态徽标、CSS/SVG 时间线与预算进度条即可。只有出现可编辑、可缩放的节点图需求才加 Vue Flow；只有报告需要呈现真实量化图表时再加 ECharts。当前需求不需要额外流程图或图表包。[12] 当前 Vue 稳定版发布页为 3.5.43，UI primitives 发布页为 Reka UI 2.10.5、shadcn-vue 2.8.2；后两者在实现时复核。[9][10]

### 版本与运行窗口

本轮官方发布页列出 LangGraph 1.2.12（2026-09-21）、FastAPI 0.141.1（2026-07-29）、Vue 3.5.43（2026-09-17）和 Reka UI 2.10.5（2026-09-21）；FastAPI 原生 SSE 支持自 0.135.0 起；PostgreSQL 18.6 于 2026-08-13 发布，计划支持至 2030-11-14。[6][7][9][10][13] 版本只证明本轮兼容性研究的基线；实施当天重新核对并锁定依赖。

BMad 官方安装说明要求 Node.js 20.12+，稳定安装命令为 npx bmad-method install；截至本轮检索，官方发布页列出 v6.12.0。正式阶段 A 项目应单独安装 BMM，并通过 --list-tools 核对工具集成选项。[14]

### 安全边界、运行负担与成本因素

| 选择 | 凭据/安全边界 | 本地运行与外部成本因素 | 本轮未确认项 |
|---|---|---|---|
| 自建 Phase A | 本机 localhost；Mock 不需第三方凭据，不把 key 放入浏览器；PostgreSQL 仅本地服务 | Docker Compose + 单 API 进程；Mock 不产生模型/搜索调用费用 | 硬件、Docker 可用性和本机维护时间因用户环境而异 |
| Google Gemini Fullstack | Gemini API key 是研究调用前置；真实调用需在服务端保护凭据 | 全栈开发服务；调用 Gemini 会消耗其配额，可能产生费用 | 实际价格与配额取决于账号/模型，方案比较不含价格预测 |
| Open Deep Research | 归档的示例支持多种模型/搜索配置；启用真实 Provider 需要对应凭据 | 配置真实模型/搜索会产生外部 API 或运行服务成本；项目已归档 | 归档后的安全更新与未来维护无保证；不适合作为生产依赖 |
| DeerFlow 2.0 | 功能涵盖沙箱、文件系统、记忆和技能；默认面向可信本地部署环境，暴露服务前需仔细收紧边界 | 比本阶段需要更多运行设施与配置；真实 Provider 另计 | 此次没有建立可比的最低资源或运行费用数据 |
| Vue3/FastAPI/LangGraph DeepResearch | README 说明可配置 Provider，但 key 的具体存储/保护方式未审计 | README 主张支持 SQLite 与 LangGraph；真实研究取决于配置的 Provider | 未确认许可证，未执行仓库；安全实现和外部调用成本未知 |
| Agent-serach | README 要求 OpenAI-compatible key，并需要外部搜索/DDGS 与代理；凭据保存方式未审计 | 需要模型配额和外部网络，可能产生费用；非无密钥演示 | 实际费用、代理信任边界及运维安全未确认 |

表内外部费用仅描述成本来源，不作美元估算。具体 API 定价、沙箱资源与用户机器运维成本没有在本次范围内统一核价；本阶段优先采用零外部调用的 fixture 演示。

## 硬门槛筛选与方案决策

先按硬门槛判断是否能直接采用，再比较技术参考价值；任一硬门槛没有证据通过，就不把该仓库当作阶段 A 的代码底座。下表中的“符合/不符合”针对直接采用当前项目，不表示经过重写后无法达成。

| 实施路径/候选 | 硬门槛筛选 | 决定 |
|---|---|---|
| 自建薄应用：LangGraph + FastAPI + PostgreSQL + Vue 3 | **按方案设计符合** Vue、无密钥 fixture 演示、可追溯引用与硬停止条件；尚未通过实现验证 | 推荐；选最小可替换模块化单体 |
| Google Gemini Fullstack 示例 | 不符合：React 前端且要求 Gemini API key | 只参考图流程 |
| Open Deep Research | 未证明 Vue 工作台与无密钥演示；仓库已归档 | 只参考研究状态与引用语义，不复制归档代码 |
| DeerFlow 2.0 | 不符合现有 Vue 工作台；沙箱、记忆、技能和长任务超出首版 | 只参考事件持久化和安全边界 |
| Vue3/FastAPI/LangGraph DeepResearch | Vue 栈符合；无密钥完整演示、引用校验和许可/维护证据不足 | 仅作对照，不直接采用 |
| Agent-serach | Vue/FastAPI/SSE 栈符合；要求外部模型 key，不符合无密钥门槛，且采用 LangChain | 仅参考 SSE 工作台交互 |
| 其它相关仓库 | Local Deep Research 和 Deep Research AI Agent 有研究/进度参考价值；前者未确认 Vue，后者是 React 且许可线索未确认 | 仅参考，不直接采用 |

推荐的依据是原方案已确定 Vue 3、Phase A 必须离线/无凭据演示以及引用绑定 Evidence ID；本轮检索没有发现可以通过全部门槛且具备充分复用证据的现成项目。自建决策是对计划方案的预测，不是已构建系统的验证结果。对可替换性、许可/维护和复杂度的比较是定性判断；实施前仍须锁版本、核对许可并验证兼容性，不报告精确适配分数或通用项目排名。

## 交叉结论与建议

开源项目的共同经验支持“显式状态 + 有界图 + 前端可观察进度 + 证据 ID”的方向，但 UI 框架与运行时部署选择因项目目标差异很大。Open Deep Research 的冻结状态说明，即使架构参考强，也要区分参考实现和当前依赖；DeerFlow 展示的事件/安全措施有价值，但其长任务设施和沙箱能力不是本演示需要；Google 示例的迭代反思有借鉴价值，但其凭据假设与当前 Mock-first 目标冲突。

阶段 A 建议保持现有技术基线，并以适配器和事件契约隔离未来 Provider：

1. FastAPI API 创建 run、展示计划、启动/取消任务、查询证据/报告/Provider 状态。
2. LangGraph 只负责阶段迁移；AgentRuntime 管理 Mock Provider、fixture、预算与取消；图节点不 import 供应商 SDK。
3. PostgreSQL 保存任务/计划/证据/报告/事件元数据；SSE 使用数据库事件序号支持断线重连。
4. Vue 端只消费 REST/SSE 稳定契约，使用明确的 Mock 标识；视觉依 UI/UX Pro Max 的编码前 Gate 生成。
5. Milvus、真实 Web Search、真实 LLM 和供应商 SDK 留到阶段 B，届时重新调研，不在阶段 A 安装。

## 未决问题

- 默认本地运行使用 Docker Compose 启动 PostgreSQL，会增加一个本地服务前置。若用户希望“只装语言运行时即可启动”，评审时可改为 SQLite；当前按原方案 PostgreSQL 作为阶段 A 基线。
- API event envelope、事件游标、取消与终态竞争的 Phase A 语义已在技术提案中定为契约；实现时须按该契约落地并生成 OpenAPI schema。
- UI 组件、色彩与布局必须在编码前读取指定的 UI/UX Pro Max skill，并从检索结果中确认，不在此提前选定视觉模板。

## 新鲜度地图（脚本计算）

按技术包的 freshness 窗口，将版本/兼容性设为 1 个月、生态信号设为 6 个月、AI 邻近领域 landscape 设为 3 个月、架构模式设为 24 个月；claims.json 与重检日期输出来自 recon_kit.py staleness（today=2026-09-24）。

脚本标记 5 条版本类 claim 已过重检日期：FastAPI SSE 能力说明（2026-04-01）、PrimeVue/PrimeUI 许可迁移（2026-08-27）、FastAPI 当前版本（2026-08-29）、shadcn-vue 当前版本（2026-09-08）、PostgreSQL 当前版本（2026-09-13）。最早重检日为 2026-04-01。它们不是过时结论的证明，而是实现启动前应回到官方页面再核实的工作项；其它版本类 claim 的最早重检日为 2026-10-04（BMad），生态信号最早为 2026-12-25（DeerFlow release）。[6][7][9][10][11][13][14]

架构模式预计可复用较久；若改成多进程运行、部署到非本机网络或加入凭据，应重新评审运行与安全边界。

## 来源附录

每条来源均于 2026-09-24 检索。公开页面未标发布日期时记为“未注明”；confidence 表示该来源对所列事实的支持强度，不是对项目整体质量的评价。

| [n] | 支持的主张 | Publisher | 发布日期 | 检索日期 | Confidence | 来源 |
|---|---|---|---|---|---|---|
| 1 | Open Deep Research 使用 LangGraph 与结构化研究状态；MIT；2026-08-21 已归档 | LangChain AI / GitHub | 归档日期 2026-08-21；README 更新 2025-08 | 2026-09-24 | 高 | [仓库](https://github.com/langchain-ai/open_deep_research)；[状态 schema](https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/state.py) |
| 2 | Gemini 全栈示例使用 React/Vite、FastAPI、LangGraph，要求 Gemini API key；生产部署说明包含 PostgreSQL 与 Redis | Google Gemini / GitHub | 未注明 | 2026-09-24 | 高 | [仓库 README](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart) |
| 3 | DeerFlow 2.0 使用 LangGraph/FastAPI、Next.js；MIT；SQLite/PostgreSQL 部署；2.0 是通用 Agent harness | ByteDance / GitHub | Release v2.0.0：2026-06-25 | 2026-09-24 | 高 | [README](https://github.com/bytedance/deer-flow)；[Releases](https://github.com/bytedance/deer-flow/releases)；[Deployment Guide](https://github.com/bytedance/deer-flow/blob/main/frontend/src/content/en/application/deployment-guide.mdx) |
| 4 | Local Deep Research 使用 LangGraph、来源/引用与 WebSocket 进度；MIT；v1.10.7 发布于 2026-08-28 | LearningCircuit / GitHub | 2026-08-28 | 2026-09-24 | 高 | [仓库](https://github.com/LearningCircuit/local-deep-research)；[Releases](https://github.com/LearningCircuit/local-deep-research/releases)；[License](https://github.com/LearningCircuit/local-deep-research/blob/main/LICENSE) |
| 5 | Deep Research AI Agent README 提及 FastAPI、LangGraph、React、Pydantic 与 SSE；查看页未发现许可证声明或发行版 | AbhiGupta1310 / GitHub | 未注明 | 2026-09-24 | 中 | [仓库](https://github.com/AbhiGupta1310/Deep-Research-AI-Agent) |
| 6 | LangGraph 的 StateGraph 类型化状态、条件/并行路由；updates/custom 流；避免向用户暴露完整 graph values；版本发布 | LangChain / LangGraph | release 页面显示 1.2.12 于 2026-09-21 发布 | 2026-09-24 | 高 | [Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)；[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)；[Releases](https://github.com/langchain-ai/langgraph/releases) |
| 7 | FastAPI 原生 SSE 支持、keep-alive/header 行为；浏览器 EventSource 按 URL 连接；release notes | FastAPI / MDN | FastAPI 0.141.1 于 2026-07-29 发布；SSE 支持自 0.135.0 起 | 2026-09-24 | 高 | [SSE Guide](https://fastapi.tiangolo.com/tutorial/server-sent-events/)；[SSE Reference](https://fastapi.tiangolo.com/reference/sse/)；[Release Notes](https://fastapi.tiangolo.com/release-notes/)；[MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource) |
| 8 | LangGraph 区分图 checkpoint 与应用运行历史；官方 checkpointer 支持持久化图状态 | LangChain / LangGraph | 未注明 | 2026-09-24 | 高 | [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)；[Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) |
| 9 | Vue 官方 TypeScript/Vite 建议；Pinia 是 Vue 默认状态管理方案 | Vue.js / Pinia | Vue 3.5.43 于 2026-09-17 发布 | 2026-09-24 | 高 | [Vue TypeScript](https://vuejs.org/guide/typescript/overview)；[Vue Releases](https://github.com/vuejs/core/releases)；[Pinia](https://pinia.vuejs.org/introduction) |
| 10 | shadcn-vue 与 Reka UI 提供可定制的 Vue 组件方案，MIT 许可 | unovue / GitHub | Reka UI 2.10.5 于 2026-09-21、shadcn-vue 2.8.2 于 2026-08-08 发布；版本实施时复核 | 2026-09-24 | 高 | [shadcn-vue](https://github.com/unovue/shadcn-vue)；[Reka UI](https://github.com/unovue/reka-ui) |
| 11 | PrimeVue 旧版本 MIT；活跃开发/新版本移向 PrimeUI，需核对 Community License | PrimeTek / PrimeUI | 许可迁移公告 2026-07 | 2026-09-24 | 高 | [PrimeVue repository](https://github.com/primefaces/primevue)；[PrimeUI Community License](https://primeui.dev/licenses/community)；[PrimeVue changelog](https://primevue.dev/changelog/) |
| 12 | Vue Flow 可用于交互式节点图；ECharts 是量化数据图表候选 | Vue Flow / Apache ECharts | 页面为滚动更新文档 | 2026-09-24 | 高 | [Vue Flow](https://github.com/bcakmakoglu/vue-flow)；[Apache ECharts](https://github.com/apache/echarts) |
| 13 | PostgreSQL 18.6 发布于 2026-08-13，支持至 2030-11-14 | PostgreSQL Global Development Group | 2026-08-13 | 2026-09-24 | 高 | [Release 18.6](https://www.postgresql.org/docs/release/18.6/)；[Versioning Policy](https://www.postgresql.org/support/versioning/) |
| 14 | BMad 稳定安装说明、Node.js 20.12+ 前置和官方发布状态 | BMad Method / GitHub | v6.12.0 于 2026-09-04 发布 | 2026-09-24 | 高 | [Install BMad](https://docs.bmad-method.org/start/install-bmad/)；[GitHub releases](https://github.com/bmad-code-org/BMAD-METHOD/releases) |
| 15 | Vue3/FastAPI/LangGraph DeepResearch 仓库 README 栈信息及页面可见的维护/许可证线索 | GitHub / 仓库作者 | 未注明 | 2026-09-24 | 中 | [仓库 README 与文件列表](https://github.com/oi1784105-spec/DeepResearch) |
| 16 | Agent-serach README 栈、MIT 许可证及外部 API/搜索配置要求 | GitHub / 仓库作者 | 未注明 | 2026-09-24 | 中 | [仓库](https://github.com/Moe2233L/Agent-serach)；[README](https://github.com/Moe2233L/Agent-serach#readme) |
| 17 | 当前 Vite 指南要求 Node.js 20.19+ 或 22.12+ | Vite | 滚动更新页面 | 2026-09-24 | 高 | [Getting Started](https://vite.dev/guide/) |
| 18 | LangGraph 当前包要求 Python 3.10+；SQLAlchemy 2.0 目标为 Python 3.7+ | LangChain / SQLAlchemy | 滚动更新包元数据与文档 | 2026-09-24 | 高 | [LangGraph pyproject.toml](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/pyproject.toml)；[SQLAlchemy 2.0 Overview](https://docs.sqlalchemy.org/en/20/intro.html) |


## 实施启动时的版本复核（2026-09-24）

实现前再次核对官方稳定发行与包索引：FastAPI 0.141.1（PyPI 标注 MIT、Python >=3.10），LangGraph 1.2.12（PyPI 标注 MIT、Python >=3.10），SQLAlchemy 2.0.54（选用 2.0 稳定线而非 2.1 prerelease），PostgreSQL 18.6；Vue 3.5.43、Vite 8.3.0、Pinia 4.0.3、Vue Router 5.3.1、Vitest 4.1.11（由 package-lock 固定）。当前机器 Node.js 24.13.0、Python 3.14.2、uv 0.12.10；Vite 指南最低为 Node.js 20.19+ 或 22.12+，但 npm 锁定的 jsdom/若干传递依赖要求 Node.js 24.15+ 或 22.22.2+。Node 24.13.0 上类型检查、Vitest 和 Vite 生产构建实测通过，但 npm 会报告 EBADENGINE，因此文档推荐 Node.js 24.15+，容器锁定 node:24.15.0-alpine。PostgreSQL 18 官方镜像将 PGDATA 和 volume root 改为 `/var/lib/postgresql/18/docker` 与 `/var/lib/postgresql`；Compose 命名卷据此挂载。[官方 PostgreSQL 镜像说明](https://hub.docker.com/_/postgres)；[Node 24.15.0 发布页](https://nodejs.org/en/download/archive/v24.15.0)。其余来源：[FastAPI PyPI](https://pypi.org/project/fastapi/)、[LangGraph PyPI](https://pypi.org/project/langgraph/)、[SQLAlchemy PyPI](https://pypi.org/project/SQLAlchemy/2.0.54/)、[PostgreSQL 18.6](https://www.postgresql.org/docs/release/18.6/)、[Vite Getting Started](https://vite.dev/guide/)、[Vue Quick Start](https://vuejs.org/guide/quick-start.html)。发布状态在安装日再次核验，锁文件记录实际解析结果。
