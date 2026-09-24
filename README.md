# DeepResearch · 阶段 A Mock 演示

这是一个可本机运行的 DeepResearch 工作台原型。它演示研究任务创建、计划确认、有界 LangGraph 流程、持久事件回放、证据池和可跳转的引用报告。阶段 A **只使用固定 Mock Fixture**：不会访问 Web、模型服务或本地真实语料，也不要求 API Key；报告不能视为经过真实来源验证的研究结论。

技术方向先按公开 GitHub 项目做过对比，再确定沿用 Vue 3、FastAPI、LangGraph、SQLAlchemy 与 PostgreSQL。完整来源、版本复核及为何不直接 fork 候选仓库见 [`outputs/phase-a-technical-research.md`](outputs/phase-a-technical-research.md)；方案经历三轮 BMad Review，见 [`outputs/phase-a-technical-proposal.md`](outputs/phase-a-technical-proposal.md)。

## 启动演示

需要 Docker Desktop/Engine 和 Docker Compose。仅本机开发时需要 Node.js 24.15+ 与 Python 3.12+；Node 24.15+ 来自当前锁定的测试工具依赖声明。首轮会下载 PostgreSQL 和应用依赖镜像。

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)。前端、API 文档和 PostgreSQL 都只通过本机回环地址可访问；API 不单独发布宿主机端口。容器网络中的 API 仅供前端代理和数据库访问。

演示步骤：

1. 输入主题并选择至少一个来源，创建计划。
2. 查看 fixture-backed 步骤，确认后启动。
3. 观察有序事件和 SearchTask 状态，必要时取消运行。
4. 从报告里的蓝色引用号跳转到证据池对应条目。
5. 在左侧“最近研究”切换历史 run。列表按稳定快照 cursor 分页。

关闭服务：

```powershell
docker compose down
```

这会停止容器并保留 PostgreSQL 命名卷，下次启动时历史记录仍在。开发场景开关默认关闭；要从 API 验收 `no_results`、部分 Scout 失败、Writer 错误和取消 scenario，可在 `.env` 设置 `MOCK_SCENARIOS_ENABLED=true` 后重建 API：

```powershell
docker compose up --build -d api frontend
```

普通工作台不提供 scenario 选择器；这些场景仅供本地 API 验收使用。

## 本机开发

先启动 PostgreSQL，再分别运行 API 和前端开发服务器：

```powershell
docker compose up -d db
$env:DATABASE_URL = "postgresql+asyncpg://deepresearch:deepresearch-local-only@127.0.0.1:54329/deepresearch"
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn deepresearch_api.main:app --host 127.0.0.1 --port 8000
```

另开终端：

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

Vite 会把 `/api`、`/docs` 和 `/openapi.json` 代理到本机 API。API 的 `DATABASE_URL` 默认连接 Compose PostgreSQL；开发场景可用 `MOCK_SCENARIOS_ENABLED=true` 开启验收 fixture。

## 验证

```powershell
uv run --directory backend pytest
npm --prefix frontend run check:api-types
npm --prefix frontend run type-check
npm --prefix frontend run test:unit -- --run
npm --prefix frontend run build
docker compose config --quiet
```

当 REST 契约变更时，运行 `npm --prefix frontend run generate:api-types` 从 FastAPI OpenAPI 更新前端 schema；`check:api-types` 用于确认提交的生成文件与当前契约一致。

当前阶段的自动覆盖包括输入契约、错误 envelope、计划/启动/取消、Fixture 场景、报告引用归属、SSE 回放/非法游标和历史快照分页。PostgreSQL 并发锁行为还需在 Docker Engine 可运行时做集成验收；API 单测使用 SQLite 临时库验证事务路径，正式运行仍只使用 PostgreSQL。

## 主要目录

- `backend/src/deepresearch_api/`：API、Pydantic 契约、LangGraph Mock 流程与持久化模型。
- `backend/migrations/`：Alembic 数据库迁移。
- `frontend/src/`：Vue 工作台、REST/SSE client、Pinia 状态。
- `docs/api-and-events.md`：REST 路由和 SSE 恢复语义。
- `design-system/deepresearch/`：UI 规则与工作台页面覆盖。
- `_bmad-output/`：BMad 产物、故事状态与实现 review 记录。

阶段边界、OpenAPI 语义和硬预算以 [`outputs/phase-a-technical-proposal.md`](outputs/phase-a-technical-proposal.md) 为准。此工作台仅监听本机；如要部署到局域网或公网，必须另行设计认证、跨站请求保护和部署安全边界。
