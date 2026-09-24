---
title: DeepResearch 阶段 A Epic 与 Story
status: ready
created: 2026-09-24
updated: 2026-09-24
sources:
  - ../prds/prd-deepresearch-2026-09-24/prd.md
  - ../architecture/architecture-deepresearch-2026-09-24/ARCHITECTURE-SPINE.md
  - ../ux-designs/ux-deepresearch-2026-09-24/EXPERIENCE.md
---

# Epic 1: 从研究输入到可追溯的 Mock 报告

独立研究者能够本机完成一条受限、可观察、引用可追溯的 Mock 研究演示。

### Story 1.1: 创建并预览研究计划

作为研究者，我可以输入主题与约束并检查计划，以便启动前确认研究范围。

验收：
- Given 主题或日期无效，When 创建 run，Then API 返回安全的 422 且不持久化 run。
- Given 至少一个来源开启，When 创建 run，Then 返回 planned run、fixture plan 与对应的 SearchTask。
- Given 用户两次启动同一 planned run，When 请求并发到达，Then 只注册一个 runtime task。

### Story 1.2: 运行有界 Mock 研究并取消

作为研究者，我可以观察 Scout、分析和 Writer 节点，以便理解运行状态和资源边界。

验收：
- Given success fixture，When 启动 run，Then Web/Local 并行、最多一轮 Reflect，且预算不会超过硬上限。
- Given 部分 scout 失败，When 另一来源成功，Then run 完成并标记覆盖警告。
- Given 所有已启用 Scout 失败，When 收敛，Then run failed 且没有报告。
- Given run 在 planned/queued/running 被取消，When 任务抵达状态边界，Then cancelled 只提交一次且没有成功报告。

### Story 1.3: 追溯 Evidence、Citation 和 Report

作为研究者，我可以从报告引用打开同 run Evidence，以便核验结论来源。

验收：
- Given writer 生成章节，When Citation Validator 检查，Then 每个 marker 解析到同 run Evidence 且集合与 citation_ids 相等。
- Given 引用缺失或跨 run，When 报告保存，Then 保存失败且 report endpoint 不暴露草稿。
- Given 无证据 fixture，When Writer 完成，Then 报告明确说明无证据且引用为空。

### Story 1.4: 观察可重放事件和运行历史

作为研究者，我可以重连流并翻页历史，以便恢复运行上下文。

验收：
- Given 客户端提交 Last-Event-ID，When SSE 重连，Then 后续持久事件按 ID 顺序补发且前端幂等合并。
- Given 非法游标，When 订阅 SSE，Then 收到无 ID 的安全控制消息且 persistent event sequence 不变。
- Given 分页期间新建 run，When 继续旧 cursor，Then 页面保持同一快照且刷新首屏能看到新 run。
- Given API 重启留下 queued/running run，When 服务恢复，Then 以 process_restarted 失败终态收敛。

### Story 1.5: 完成本机工作台和演示包

作为演示者，我可以按 README 在本机启动工作台，以便完整说明 Mock 能力和限制。

验收：
- Given PostgreSQL 可用且无 Provider key，When 按 README 启动，Then 可完成创建、预览、运行、证据和报告主流程。
- Given desktop、tablet 与 375px 屏幕，When 键盘或鼠标操作，Then 核心路径可达且无横向溢出。
- Given 任一页面处于加载、空、失败、取消或 Mock 状态，When 屏幕阅读器访问，Then 内容和下一步动作可被辨识。
- Given Provider 状态页，When 查看连接，Then 文案明确 connectivity_tested=false。

## Epic 1 Definition of Done

FR-1–FR-14 均有实现与验收证据；无真实 Provider 调用；自动测试、类型检查、生产构建通过；用户能依 README 演示成功、失败、无证据和取消。
