---
title: 'DeepResearch 新手 README 与首用引导'
type: 'feature'
created: '2026-10-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '61d2bdf0ad2f62489c0533fb632be214b181b643'
context:
  - 'README.md'
  - 'design-system/deepresearch/MASTER.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-deepresearch-2026-09-24/DESIGN.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-deepresearch-2026-09-24/EXPERIENCE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** README 目前偏向开发者说明，第一次接触项目的人不容易看懂它能做什么、如何启动、页面各区域有什么用；打开工作台后也缺少从创建任务到检查报告的清晰入口。

**Approach:** 重写 README，让非技术用户能理解 Phase A 的用途、功能边界、页面流程和整体架构，同时保留准确的本地启动与开发说明。在现有工作台增加可跳过、可再次打开的入门说明，解释填写主题、确认计划、查看证据与引用的顺序。

## Boundaries & Constraints

**Always:** 明确此阶段仅使用固定 Mock Fixture，不调用真实 Web、模型或用户本地语料，也不需要 API Key；保持 localhost 端口和 Docker Compose 命令准确。入门说明首次可见、可关闭，关闭状态保存在浏览器本地；顶栏“使用说明”可随时重开。正文清楚易读，键盘可操作，375px 页面不横向溢出，遵循现有 DESIGN/EXPERIENCE。

**Never:** 不改 API、数据库、LangGraph、Provider 或 Mock 行为；不增加真实外部请求、账号或凭据；不做强制遮罩式导览，不把 Fixture 报告描述为真实来源已验证的研究结论。

</frozen-after-approval>

## Code Map

- `README.md` — 当前启动/演示/开发说明已有事实，但顺序面向熟悉 Docker 与代码的读者；以新手快速开始、工作台导览、架构图、限制和排障重新组织。
- `docker-compose.yml`、`.env.example` — 启动端口、服务健康检查、默认变量和 `postgres_data` 命名卷的数据保留事实来源。
- `frontend/src/App.vue` — 应用外壳、导航和顶栏；在此添加常驻“使用说明”按钮及原生对话框，不改路由和 store 生命周期。
- `frontend/src/views/HomeView.vue` — 现有表单、计划、运行状态、事件、证据池和报告；在表单前加入首次引导卡，不改变创建/启动/取消路径。
- `frontend/src/assets/main.css`、`frontend/src/assets/base.css` — 工作台样式、响应式断点、焦点和减少动态效果规则；为引导添加可读、窄屏适配的样式。
- `frontend/src/stores/research.ts`、`backend/src/deepresearch_api/` — 提供现有流程与接口；本次复用，不修改。
- `docs/api-and-events.md`、`design-system/deepresearch/pages/research-workspace.md` — API/SSE 语义及工作台设计约束的核对来源。

## Tasks & Acceptance

**Execution:**
- [x] `README.md` — 按新手阅读顺序解释项目用途、可做/不可做、启动停止、页面操作、数据保留与清空、常见问题、技术架构和目录职责。
- [x] `frontend/src/App.vue` — 添加可键盘操作、Esc 可关闭且能恢复焦点的“使用说明”对话框入口。
- [x] `frontend/src/views/HomeView.vue`、`frontend/src/assets/main.css` — 增加首次显示的三步引导卡、关闭后记忆状态、适配窄屏并提升说明文字字号；现有研究流程保持不变。

**Acceptance Criteria:**
- Given 用户只看 README，when 按文档启动，then 能知道浏览器地址、页面区域作用、一次演示任务的操作顺序以及 Mock 限制。
- Given 初次打开空白工作台，when 页面就绪，then 可看到三步引导并直接开始填写或关闭。
- Given 用户关闭引导，when 后续重新访问，then 不再自动显示；when 点击顶栏“使用说明”，then 可重新查看完整操作说明。
- Given 键盘用户或 375px 窄屏，when 使用引导和对话框，then 焦点可见、Esc 可关闭、布局无横向溢出。
- Given 用户创建、运行或取消任务，when 新增引导功能存在，then 原有 API、Mock 状态和报告引用流程不变。

## Implementation Notes


## Spec Change Log

## Review Triage Log
- B1 — README quick start 中重复运行 `Copy-Item` 会覆盖用户已有 `.env`；**medium / patch P1**。已核对 PowerShell `Copy-Item` 默认覆盖，属于真实配置丢失风险。
- B2 — README 删除了局域网/公网部署前的安全边界提醒；**medium / patch P2**。基线明确提醒需先设计认证、跨站请求保护和部署安全边界。
- B3 — 本机开发示例把 PostgreSQL 端口固定为 `54329`，但前文允许修改 `POSTGRES_PORT`；**medium / patch P3**。Compose 的宿主机映射随该变量变化，示例连接串不会自动变化。
- B4 — 改 `WEB_PORT` 后没有说明浏览器地址也要使用该端口；**low / patch P4**。Compose 映射证实端口会随变量变化；补充 URL 模板即可消除启动困惑。
- B5 — 启动步骤没有给出就绪判断；**medium / patch P5**。`docker compose up -d` 可在服务就绪前返回，排障段虽提到健康检查但快速开始没有等待/检查步骤。
- B6 — 本机开发列出 `uv` 但没有安装指引；**low / patch P6**。对未安装 `uv` 的开发者缺少下一步；加入官方安装文档链接即可。
- E1 — `.env` 覆盖风险与 B1 相同，**medium / patch P1**。相同命令会覆盖用户配置，沿用 B1 结论。
- E2 — 自定义 `POSTGRES_PORT` 与开发连接串不一致，与 B3 相同，**medium / patch P3**。Compose 读取该端口而硬编码连接串仍为 `54329`。
- E3 — 浏览器存储不可用时，关闭引导后离开 Home 再返回会重新显示；**low / patch P7**。读取失败路径总是将可见状态设为真，且关闭不保留当前 SPA 会话状态；加会话内状态即可处理。
- E4 — 对话框关闭与 RAF 聚焦存在竞态；**low / patch P8**。在回调中检查对话框仍打开，是直接且低成本的修正。
- E5 — 部署安全提醒删除与 B2 相同，**medium / patch P2**。基线中的安全提醒确已删除。
- E6 — localStorage 不可用时不能保证跨刷新记住关闭状态；**false**。该失败路径没有可用持久化介质，代码有意回退为当前打开时可关闭；用户仍可在浏览器本地存储可用时获得持久记忆，不能把存储被禁用时的跨刷新持久化当作代码可实现行为。
- V1 — 引导关闭持久化没有回归测试；**medium / patch P9**。验证层已查阅现有 HomeView 测试并确认没有覆盖存储/重挂载行为；需要对该关键验收行为增加定向用例。
- V2 — 使用说明对话框的 Escape 关闭没有回归测试；**medium / patch P10**。验证层已查阅现有 App 测试并确认未覆盖对话框；需要增加键盘交互用例。
- R2-B1 — README 将 Node 版本写成“22.22.2+ 或 24.15.0+”，可能使人误选 Node 23 或 Node 24.0–24.14；**medium / patch P11**。`frontend/package.json` 的 engine 实际是 `^22.22.2 || >=24.15.0`。
- R2-B2 — 快速开始把浏览器地址直接写成 5173，现有 `.env` 可能使用自定义端口；**low / patch P12**。新手照抄会访问错误端口；标清 5173 是默认值并给配置地址即可。
- R2-B3 — README 没给 Docker 安装入口；**low / patch P13**。这是快速开始的前置条件，补官方 Windows 安装指南链接是直接修正。
- R2-B4 — README 第一次提到 `SearchTask` 时未解释；**low / patch P14**。用“每个来源的搜索任务状态”作简短说明即可。
- R2-B5 — 页面区域表写“Provider 状态”，界面导航实际叫“数据源状态”；**low / patch P15**。两者指同一区域，改用界面文字即可。
- R2-B6 — README 未告知首次引导及顶栏“使用说明”可重开；**low / patch P16**。这是新增可见功能入口，补充一句说明即可。
- R2-B7 — 入门按钮强制 `scrollIntoView({ behavior: 'smooth' })`，忽略减少动态效果偏好；**medium / patch P17**。显式 JS 平滑滚动不会被现有 CSS 媒体规则覆盖。
- R2-B8 — 新增 HomeView 测试只覆盖存储失败时的会话回退，未覆盖 localStorage 正常写入与新实例读取；**medium / patch P18**。现有测试不能检出持久写入回归。
- R2-E1 — App 测试在 `renderApp()` 完成前尚未进入 `try/finally`；**low / patch P19**。若挂载提前抛错，测试替换的原生 dialog 方法不会恢复。
- R2-E2 — Node 版本范围问题与 R2-B1 同一原因，**medium / patch P11**。已核对 engine 声明，按同一修正处理。
- R2-V1 — 正常 localStorage 持久化路径缺少测试，与 R2-B8 相同，**medium / patch P18**。该路径目前没有断言成功写入和重新挂载后读取。
- R2-V2 — 375px 横向溢出缺少自动浏览器用例；**low / reject**。在本地窄屏预览中检查了引导卡与打开的说明对话框，未见横向滚动；增加浏览器自动化需引入本项目当前没有的端到端测试栈，低风险视觉覆盖缺口不值得扩展项目范围。
## Verification

- 静态检查 README、组件和样式改动是否符合规格。
- 只运行覆盖本次新增交互的 HomeView 与 App 定向前端测试；不运行更广泛的测试套件。





- R3-B1 — README 的 API 文档地址固定为 `5173/docs`，但同段允许自定义 `WEB_PORT`；改端口后链接失效。证据：README 默认链接与自定义端口说明并列；**low / patch P20**。
- R3-B2 — README “首次加载”过于笼统，直接打开历史 run 页面时不会出现引导卡。证据：HomeView 只在 `route.name === 'home' && !research.currentRun` 时渲染；**low / patch P21**。
- R3-B3 — 顶栏使用说明仍单独写 `SearchTask`，新手无法从本窗口理解术语。证据：对话框步骤仅写“来源任务”，区域说明仍写“SearchTask 状态”；**low / patch P22**。
- R3-B4 — 使用说明未提示任意主题可能没有匹配 Fixture 证据。证据：对话框只声明固定 Mock 与报告未验证，缺少无匹配结果预期；README FAQ 虽有说明，但不会出现在只打开对话框的路径；**low / patch P23**。
- R3-B5 — 首页引导按钮的 `focusTopic()` 固定使用平滑滚动，未尊重减少动态效果偏好。证据：HomeView 使用 `scrollIntoView({ behavior: 'smooth' })`；**medium / patch P24**。
- R3-B6 — 对 triage log “未记录 disposition” 的主张不成立。证据：既有每行明确记录 verdict 与路由（例如 `medium / patch P1`）；BMad Step 4 要求 verdict、证据和路由，没有另设“已解决”标记；建议会改当前 build spec，按审查规则拒绝；**false**。
- R3-B7 — README 本机开发检查命令之后，缺少基线中关于自动测试覆盖范围、PostgreSQL 并发锁集成验收尚未完成的说明。证据：基线 README 有该段，当前版本删除；**low / patch P25**。
- R3-E1 — 同 R3-B1：自定义 `WEB_PORT` 时固定 `/docs` 链接仍指向错误端口；沿用 **low / patch P20**。
- R3-E2 — 同 R3-B5：HomeView 的引导滚动忽略 `prefers-reduced-motion`；沿用 **medium / patch P24**。
- R3-E3 — README 删除 REST 契约变更后运行 `generate:api-types` 的步骤。证据：`frontend/package.json` 仍声明 `generate:api-types` 和 `check:api-types`，README 只保留 check 命令；**low / patch P25**，与 R3-B7 同属重写 README 时遗漏开发维护说明。
- R3-V1 — HomeView 测试未覆盖引导卡“开始填写主题”是否将焦点移到 `#topic`。证据：验证层搜索相关按钮、函数和 id 后未发现交互用例；当前测试只有关闭与持久化；**low / patch P26**。
- R3-V2 — App 测试覆盖 Esc 关闭，但未覆盖可见“关闭”按钮的点击与焦点恢复。证据：验证层搜索 `.usage-dialog-close` 和 `closeUsageGuide` 后未发现点击路径用例；**low / patch P27**。
