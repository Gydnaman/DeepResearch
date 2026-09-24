# DeepResearch 阶段 A 实施计划

> 依据：三轮 BMAD review 通过的 outputs/phase-a-technical-proposal.md 与开源调研记录。目标是从空仓库交付可运行的 Mock-first 研究演示。所有依赖版本在首次安装前核对官方发布信息并锁定；不接真实 Provider。

## 结构与模块

- backend/：Python 包、配置、Pydantic DTO、SQLAlchemy 模型/迁移、repository/application service、FastAPI 路由、SSE adapter、LangGraph Mock runtime/fixtures。
- frontend/：Vue 3 + TypeScript + Vite；输入表单、计划、运行台、证据、报告、历史、Provider 状态；消费 OpenAPI 生成或严格对齐的类型。
- design-system/deepresearch/：UI/UX Pro Max Master 规则；必要时加页面 overrides。
- _bmad-output/planning-artifacts/、_bmad-output/implementation-artifacts/：官方 BMM brief、PRD、DESIGN/EXPERIENCE、架构、epic/story、readiness 与实现状态。
- 根目录：docker-compose.yml、.env.example、统一启动/演示脚本、README、API/event 契约、.gitignore。

## 执行顺序

1. 完成阶段 A 产品上下文：brief、PRD、用户旅程/状态设计、架构边界、epics/stories 和 readiness；确保只表达已批准范围。将可见视觉选择依据 UI/UX Pro Max 检索结果落实到 DESIGN.md。
2. 复核当天官方稳定版本、许可和最低运行环境；用 pyproject.toml/锁文件及 package.json/lockfile 固定依赖。搭建 API/UI 空壳、配置、健康端点和仅 localhost 的 Compose PostgreSQL。先验证 Compose 配置与数据库可连接。
3. 先写领域 DTO/validator 测试，再实现 Run、Plan、SearchTask、Evidence、Citation、Report、RunEvent 与受限输入校验。以 OpenAPI 作为 REST 契约，落实安全错误 envelope 与状态枚举。
4. 先写 repository/事务测试，再实现 PostgreSQL 模型、迁移与原子事件序号分配、稳定历史 cursor/snapshot、进程重启收敛和每个 run 的事件上限。
5. 先写 runtime 行为测试，再实现 Mock Provider protocols/fixtures、LangGraph 有界路径、最多一轮 Reflect、Scout 并发/时长/调用预算、状态更新、取消与唯一终态提交。
6. 先写 API/SSE 集成测试，再实现创建/读取/开始/取消/证据/搜索任务/报告/Provider 路由；验证断线恢复、终态重放、非法游标控制消息及不泄露私有信息。
7. 先写前端组件/流程测试，再完成 Vue 页面与 API/SSE store。实现表单校验、计划确认、实时进度、取消反馈、证据引用回跳、历史分页和明确的 Mock/空/加载/错误状态。
8. 完成 README、OpenAPI/event 文档、演示 fixtures 与脚本；运行后端测试、前端测试/typecheck/build、Compose 配置/DB 集成测试。按 UI/UX Pro Max checklist 走查无障碍、焦点、reduced-motion、对比度和 375/768/1024/1440px 无横向溢出。

## 测试与完成条件

- 每项功能按 TDD：先增加能复现验收的测试，确认失败，再实现使其通过；最后跑相关和全量验证。
- 必测拒绝条件：空/过长主题，未知输出格式，非法/倒置日期，无来源，未开启 scenario，跨 run citation，未知 run，超限预算，非法事件游标。
- 必测运行终态：success、no_results、partial_scout_failure、writer_error、citation_validation_error、cancel、所有 Scout 失败、Reflect 目标 fixture 缺失、event budget 预留终态槽。
- 必测并发/恢复：重复 start、cancel 与 complete 竞争、重启遗留 queued/running、重复 SSE replay upsert、keyset 分页期间新建 run。
- 实现中若要变更批准方案中的数据库、API、SSE 语义、安全边界或运行拓扑，先修订技术方案并重新评审；不以本计划替代重新批准。
