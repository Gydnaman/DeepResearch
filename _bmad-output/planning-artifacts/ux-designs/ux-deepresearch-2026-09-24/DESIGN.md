---
title: DeepResearch 视觉设计
status: final
created: 2026-09-24
updated: 2026-09-24
sources:
  - ../../../briefs/brief-deepresearch-2026-09-24/brief.md
  - outputs/phase-a-technical-proposal.md
  - design-system/deepresearch/MASTER.md
---

# DeepResearch — Design Spine

## Brand & Style

DeepResearch 是研究工作台，不是营销落地页。它呈现克制、可信、易审查的研究过程：紧凑的数据布局支撑观察，报告正文保留阅读舒适度。采用 Swiss Modernism 2.0 的网格秩序与 Data-Dense Dashboard 的信息效率。品牌语言强调证据、来源与边界；不使用虚构背书、装饰性渐变或庆祝动画。

## Colors

使用 UI/UX Pro Max 对 Research Lab 和 Analytics Dashboard 的检索结果；颜色用于语义层，不靠颜色单独表达状态。

| Token | Value | Use |
|---|---|---|
| colors.primary | #1E3A5F | 主导航、主要动作 |
| colors.on-primary | #FFFFFF | 主色文字 |
| colors.secondary | #2563EB | 次级链接、Web 来源 |
| colors.accent | #A16207 | 研究范围重点、提示 |
| colors.background | #F8FAFC | 页面背景 |
| colors.surface | #FFFFFF | 卡片与面板 |
| colors.foreground | #0F172A | 正文 |
| colors.muted | #E9EEF5 | 次级面板 |
| colors.muted-foreground | #475569 | 次要信息 |
| colors.border | #CBD5E1 | 线框 |
| colors.success | #15803D | 完成状态 |
| colors.warning | #A16207 | 部分结果 |
| colors.destructive | #B91C1C | 错误/取消 |
| colors.focus | #1E3A5F | 键盘焦点 |

Mock 徽标使用与正文足够对比的中性蓝底；Web、Local、fixture 另有文字标签和图标/形状，不仅依赖色彩。

## Typography

正文采用系统无衬线栈：Inter、Segoe UI、Microsoft YaHei、sans-serif，基准 16px、行高 1.5。研究结论标题使用同一无衬线字族，避免平台字形不齐。Evidence ID、事件序号、预算数字可用 Fira Code 或系统等宽字体。阶段 A 不下载远程字体，确保本地演示不依赖外部字体服务。

## Layout & Spacing

宽屏使用左侧导航加主要工作区，工作台内容以 12 栏网格组合；桌面信息密度较高，段落行宽控制在 80 字符左右。基础间距 4px，常用 8/12/16/24px。窄屏将侧栏折叠为顶栏导航，面板改为单列。运行时间线在窄屏垂直显示，不使用固定宽度表格。

## Elevation & Depth

通过白色 surface、浅灰分组底色和 1px border 分层。卡片无重阴影；仅对话框使用轻阴影。不要用动效替代层级。

## Shapes

输入、徽标和卡片使用 6–10px 圆角；状态徽标可用椭圆。主视图保持方正整齐，不使用大胶囊装饰。

## Components

- Primary action：海军蓝实心按钮，清晰 hover、active、disabled 和 focus 状态。
- Mock badge：固定显示“Mock fixture”，不允许在成功后消失。
- State badge：图标/文本/色彩同时表达 planned、running、completed、failed、cancelled、skipped。
- Evidence row：来源标签、日期、摘录、相关性和关联状态分开布局。
- Citation marker：报告中可键盘聚焦的编号；打开对应 Evidence 的详情。
- Timeline row：节点名、时间、状态、摘要；失败摘要保留恢复建议。

## Do's and Don'ts

| Do | Don't |
|---|---|
| 用 SVG 图标并提供 accessible name | 用 emoji 替代图标 |
| 使用表格或列表展示可比较信息 | 用卡片堆叠隐藏事件顺序 |
| 显示真实 fixture 限制与 token 不适用 | 暗示外部 API 已连接 |
| 在正文和摘要中保持对比度 | 只用红/绿区分错误/成功 |
| 在 375px 下堆叠信息面板 | 固定列宽造成水平滚动 |
| 动效遵循 prefers-reduced-motion | 常驻闪烁或庆祝动画 |
