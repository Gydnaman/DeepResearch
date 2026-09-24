---
title: DeepResearch 交互体验
status: final
created: 2026-09-24
updated: 2026-09-24
sources:
  - ../../../briefs/brief-deepresearch-2026-09-24/brief.md
  - ../../../prds/prd-deepresearch-2026-09-24/prd.md
  - ./DESIGN.md
---

# DeepResearch — Experience Spine

## Foundation

响应式 Web 工作台，面向桌面分析流程并支持窄屏查看。UI 使用 Vue 3 + TypeScript + Vite 与自建语义组件；视觉 token 由 DESIGN.md 控制。本阶段为单用户 localhost，无登录。Mock 标志始终可见。

## Information Architecture

| Surface | Entry | Purpose |
|---|---|---|
| 新建任务 | 导航主动作 | 主题、时间、维度、输出和来源设置 |
| 计划预览 | 新建成功后 | 核对问题和步骤，启动或取消 |
| 运行工作台 | 开始运行/历史详情 | 时间线、SearchTask、预算和失败 |
| 证据池 | 工作台/报告引用 | 检查 fixture 元数据和证据关系 |
| 研究报告 | 工作台完成后 | 章节、引用跳转、无证据/部分来源说明 |
| 历史与 Provider | 侧栏导航 | 分页 run 历史与 Mock 配置状态 |

## Voice and Tone

文字准确、平静、直说状态；突出来源和下一步。使用“运行中”“来源不可用”“本报告基于 Mock fixture”。避免“研究已验证”“来源已连接”等不实描述。

## Component Patterns

- 输入表单：可见标签、字段级校验、来源开关；错误紧邻字段。
- 计划预览：显示运行模式、问题和来源 SearchTask；运行前允许取消。
- 事件时间线：按稳定序号升序；连接断开说明自动恢复中；终态关闭订阅。
- Evidence 与 Citation：点引用后可定位证据详情；无效映射时报告不可显示。
- 错误提示：说明稳定错误码的可读含义及可恢复动作；没有自动重试就明确说明需新建 run。

## State Patterns

| State | Behavior |
|---|---|
| 首屏加载 | skeleton 或状态提示；超过 300ms 有反馈 |
| 历史为空 | 说明暂无任务，并提供“新建研究”动作 |
| 正常运行 | 显示阶段、事件、Scout 用量及取消操作 |
| 部分失败 | 保留失败来源状态，说明报告覆盖有限 |
| 无证据 | 显示“没有 fixture 证据”并仍可读报告 |
| 取消中/已取消 | 说明运行已停止且无成功报告 |
| SSE 断连 | 显示恢复中；用 Last-Event-ID 恢复，事件按 ID 幂等合并 |
| 服务错误 | role=alert / aria-live；提供刷新或新建任务动作 |
| Provider 状态 | 标明 Mock、已配置与 connectivity_tested=false |

## Interaction Primitives

- 键盘顺序与视觉顺序一致；Tab 可到达导航、输入、时间线操作、citation 和分页。
- Escape 关闭对话框并将焦点还给触发控件。
- 新建 run 后聚焦计划标题；开始后聚焦运行状态摘要；终态标题可被屏幕阅读器发现。
- 运行取消使用按钮并即时反馈；完成/取消竞态以后端最终状态为准。

## Accessibility Floor

遵循 WCAG 2.2 AA。输入有 label；错误使用 aria-describedby 和 role=alert；异步进度使用 aria-live=polite；状态同时使用文本和图标；焦点清楚可见；缩放不受限。减少动效偏好下移除非必要过渡，不用颜色单独表达状态。

## Key Flows

### Flow 1 — 林然检查一次 Mock 研究

1. 林然打开工作台，首页说明本次运行是 Mock fixture，并填写主题、日期、输出结构和来源。
2. 系统近字段提示错误，或创建 planned run 并展示计划。
3. 林然核对 Web/Local SearchTask 后启动；工作台显示阶段和可取消状态。
4. Scout 事件和 Evidence 逐步出现；如一个来源失败，失败被标出但另一来源继续。
5. **高潮：**报告完成后林然按键盘聚焦 citation，打开来源 Evidence，确认 ID 与本 run 一致且报告保留 fixture 标记。
6. 若没有证据，报告明确显示缺口；林然可回到历史或调整主题新建 run。

## Responsive & Platform

| Width | Behavior |
|---|---|
| 1440px / 1024px | 导航和主面板同屏；证据和时间线可并列 |
| 768px | 次要面板改为分段/上下布局 |
| 375px | 单列内容；导航折叠；时间线垂直；无横向溢出 |

DESIGN.md 与 EXPERIENCE.md 是并列契约；若与 mock 或实现冲突，以两份 spine 为准。
