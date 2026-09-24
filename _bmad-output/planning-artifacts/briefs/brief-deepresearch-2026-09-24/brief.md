---
title: DeepResearch 阶段 A 产品简报
status: final
created: 2026-09-24
updated: 2026-09-24
sources:
  - outputs/BMAD-DeepResearch项目方案.md
  - outputs/phase-a-technical-proposal.md
  - outputs/phase-a-technical-research.md
---

# Product Brief: DeepResearch

## Executive Summary

DeepResearch 是一个面向独立研究者与工程学习者的多 Agent 研究工作台。阶段 A 用固定 fixture 演示从研究主题、计划、受限运行到证据与引用报告的完整链路。任何页面都明确说明这是 Mock 流程，不代表真实网络研究或事实准确度。

阶段 A 的价值是让用户能观察状态如何流转、证据如何关联到结论、失败与取消如何收敛。它为后续替换 Provider 留出稳定接口，但当前不消耗模型或搜索 API。

## The Problem

用户只有概念和技术方案时，无法验证复杂 Agent 流程的接口、停止条件、引用绑定和用户体验。仅展示一份静态报告会掩盖运行进度、部分失败和引用来源。

## The Solution

提供一个本机可运行的 Vue 工作台和 FastAPI 服务。用户可填写主题和来源约束、检查 Mock 计划、启动/取消运行，并查看事件、SearchTask、Evidence、Citation、Report、历史和 Provider 状态。

## What Makes This Different

- 报告引用可回溯到当前 run 的 fixture Evidence。
- SSE 事件有持久顺序，可断线恢复；取消、失败和重复请求都有明确语义。
- Mock Provider 与领域契约分离，后续可替换而不改前端 API。
- 不把演示流程宣传成真实研究能力。

## Who This Serves

主要用户是单人分析者或工程学习者：希望理解一个受限研究图如何被观察、复现和审查。成功意味着他能完成一次演示，检查引用及运行状态，并知道哪些结论仅由 fixture 提供。

## Success Criteria

- 按 README 可从本机无第三方凭据启动。
- success、no-results、partial-failure、cancel 等演示覆盖可观察且有测试。
- 报告中每个 citation 都解析到同一 run 的 Evidence。
- 核心流程支持键盘操作和窄屏。

## Scope

阶段 A 包含前端、API、PostgreSQL 元数据、LangGraph 骨架、Mock Providers、事件恢复、受限预算和本机启动说明。真实 LLM、Web Search、本地语料、Milvus、线上部署和真实研究评测留待新调研和新方案评审。

## Vision

后续阶段可在保留公开契约和证据追溯的前提下接入真实来源，让系统从可观察的教学演示发展为可评测的研究工作台。
