---
title: DeepResearch 阶段 A 产品需求文档
status: final
created: 2026-09-24
updated: 2026-09-24
sources:
  - ../briefs/brief-deepresearch-2026-09-24/brief.md
  - ../ux-designs/ux-deepresearch-2026-09-24/DESIGN.md
  - ../ux-designs/ux-deepresearch-2026-09-24/EXPERIENCE.md
  - ../architecture/architecture-deepresearch-2026-09-24/ARCHITECTURE-SPINE.md
---

# PRD: DeepResearch 阶段 A
*阶段 A：无密钥、可观察的 Mock 研究闭环。*

## 0. 文档目的

面向实现与验收，定义可演示能力、用户成功条件和边界。技术接口细节由 ARCHITECTURE-SPINE.md 和已批准方案负责，视觉与行为分别由 DESIGN.md 和 EXPERIENCE.md 负责。

## 1. 愿景

独立研究者能够看见一次研究任务从输入到引用报告的状态变化，并核验每条引用回到哪条 Evidence。阶段 A 以确定性 fixture 建立用户可观察的产品契约，不声称能联网研究。

## 2. 目标用户

### 2.1 Jobs To Be Done

- 当我探索多 Agent 研究架构时，希望跑一条受控流程并看见任务、证据和引用之间的关系。
- 当演示遇到搜索部分失败、无结果或取消时，希望系统保留清楚的原因和可恢复的终态。
- 当我检查报告时，希望直接定位来源 Evidence，并辨别 Mock 数据。

### 2.2 非用户

阶段 A 不面向需要实时事实核查或生产研究结论的组织，不提供账号、多用户协作或对外部署。

### 2.3 Key User Journey

- **UJ-1 林然完成一次可追溯演示。** 林然是一位研究型工程学习者，在本机打开工作台；填写主题、时间和来源，预览 Mock 计划后启动；观察 Web/Local Scout 的 SearchTask 和有序事件；运行完成后打开一条报告引用并跳转到 Evidence。**高潮：**林然确认引用属于本次 run，且页面标记 fixture，因此能准确说明演示能力的边界。若一个来源失败，他能在报告与任务状态中识别部分结果。

## 3. Glossary

- **ResearchRun**：一次用户发起的研究运行，有唯一状态与预算。
- **Plan**：运行前供用户确认的 Mock 问题和步骤。
- **SearchTask**：一次 Web 或 Local 检索任务，包括状态和 Evidence ID。
- **Evidence**：一个有稳定 ID 的 fixture 证据条目。
- **Citation**：报告中指向同 run Evidence 的引用记录。
- **Report**：按章节保存、具有引用 marker 的运行结果。
- **ResearchEvent**：持久化的运行事件，有 run 内递增序号。
- **Mock Provider**：不访问外部模型或搜索 API 的确定性实现。

## 4. Features

### 4.1 创建与预览

**Description：**林然输入研究范围并在执行前核对计划（UJ-1）。

- **FR-1 输入校验：**系统拒绝空或超限主题、非法日期、未知输出格式、无来源及超预算输入，并返回可操作的 422 错误。
- **FR-2 计划预览：**系统创建 planned ResearchRun、Mock Plan 与每个来源的 SearchTask；关闭的来源标记 skipped。Scenario 仅在服务端显式开启时可设置。
- **FR-3 启动与幂等：**用户确认计划后启动；重复 start 不注册第二个 runtime task，终态操作返回稳定状态。

### 4.2 受限 Mock 运行

- **FR-4 执行图：**Intent Router、Planner、并行 Web/Local Scout、Evidence Judge、Analyst、至多一次 Reflect、Writer 和 Citation Validator 按固定流程执行。
- **FR-5 预算：**每 run 默认最多一次 Reflect、3 次 Scout call、2 并发、120 秒、100 条持久事件；请求只能收紧。单次最多 5 条 Evidence，每条 excerpt 最多 1000 字符。tokens_used 为 null。
- **FR-6 状态与故障：**支持 success、no-results、partial-scout-failure、writer-error、citation-error、cancel fixture。所有启用 Scout 均失败时 run failed、无报告；部分失败可完成但标记 warning。
- **FR-7 取消和重启：**取消 planned/queued/running 有明确语义；终态只写一次且取消成功时不保存成功报告。启动时遗留 queued/running 收敛为 process_restarted 失败。

### 4.3 证据、报告与历史

- **FR-8 引用校验：**只接受本 run Evidence；每章正文 marker 集合必须等于 citation_ids，失败时不暴露草稿。
- **FR-9 事件流：**每 run 有持久递增序号；SSE 按 Last-Event-ID 重放，UI 依 (run_id,id) 幂等 upsert；非法游标使用无 ID 控制消息，不改数据库状态。
- **FR-10 可查记录：**用户可读取 run、计划、SearchTask、Evidence、Report、Provider 状态和游标分页历史。
- **FR-11 安全标签：**所有成功响应明确 mode=mock、fixture=true；Provider 状态不伪装外部连通；事件不泄漏 secret 或私有推理。

### 4.4 工作台

- **FR-12 主流程：**用户可创建任务、预览、开始/取消、观察运行、查看证据与报告。
- **FR-13 辅助页面：**提供历史列表及 Provider 状态，显示 run 模式和终态。
- **FR-14 状态反馈：**每个页面具备空、加载、失败、禁用/取消状态，并提供下一步操作。

## 5. Non-Goals

不接真实 Provider/来源，不提供无限自主搜索、登录、外部操作、长期记忆、Milvus、后台多 worker 或公开部署。

## 6. MVP Scope

包含固定 schema、持久事件和产品记录、确定性 Mock graph、REST/SSE、响应式 Vue 工作台、PostgreSQL Compose 和启动文档。真实内容和评测需另行研究并评审。

## 7. Success Metrics

- **SM-1：**自动验收可走通每种预置终态且只产生一个终态事件。验证 FR-3–FR-7。
- **SM-2：**有效报告所有 citation 可解析到同 run Evidence，负面引用用例全部拒绝。验证 FR-8。
- **SM-3：**SSE replay、重连和分页快照测试通过，无漏发/重复行。验证 FR-9–FR-10。
- **SM-4：**README 清洁启动路径可运行，四个关键视口无横向溢出。验证 FR-12–FR-14。
- **SM-C1：**Mock token 消耗保持 null；不得以“成功率”包装 fixture 为研究准确度。反制 SM-1 的过度宣传。

## 8. Cross-Cutting NFRs & Guardrails

- 服务绑定 localhost，数据库映射到 127.0.0.1；无浏览器 secret，无真实外部请求。
- OpenAPI/Pydantic 契约稳定；错误 envelope 不含堆栈。DB 事务原子提交状态与事件。
- 事件最多 100 条并为唯一终态保留空间；预算与并发上限不可由调用方放宽。
- WCAG AA 对比、键盘可达、可见焦点、reduced-motion、窄屏无横向滚动。

## 9. Assumptions Index

- 本机开发以 Docker Compose PostgreSQL 为前置；已在获批技术方案中确认，Docker 引擎启动由运行者完成。
- 此阶段无登录且仅用于单人本机演示；来源为原始方案，不外推到网络部署。
