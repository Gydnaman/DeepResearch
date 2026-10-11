# DeepResearch 阶段 A 演示

DeepResearch 是一个本机研究工作台原型，用来演示如何从研究主题生成计划、查看运行过程，并沿着报告引用检查对应证据。

## 这阶段可以做什么

你可以创建研究任务、检查计划、启动或取消演示运行、查看事件和证据，并在报告中点击引用跳到对应证据。侧栏还能查看最近的任务和数据源状态。

**所有运行只使用项目内的固定 Mock Fixture。** Web 资料和本地知识库选项都指向预设样本；工作台不会访问真实 Web、模型服务或你的本地语料，也不需要 API Key。报告用于演示流程，不能当作经过真实来源验证的研究结论。首次构建 Docker 镜像时，Docker 仍需下载镜像和安装依赖。

## 快速开始

需要安装并启动 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)，或可用的 Docker Engine 与 Docker Compose。第一次启动会构建镜像并安装依赖，耗时会更长。

在项目根目录运行：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose ps
```

查看 `docker compose ps` 的状态：等待 `db` 和 `api` 显示 `healthy`，并确认 `frontend` 正在运行，再打开默认地址 [http://localhost:5173](http://localhost:5173)。如果保留的 `.env` 设置了自定义 `WEB_PORT`，浏览器地址使用 `http://localhost:<WEB_PORT>`，API 文档地址相应为 `http://localhost:<WEB_PORT>/docs`，其中 `<WEB_PORT>` 替换为该端口值。默认 API 文档地址为 [http://localhost:5173/docs](http://localhost:5173/docs)。首次进入没有当前运行的新建研究首页时会显示使用引导；直接打开历史运行页面时不会显示卡片。之后可从顶部栏的“使用说明”重新打开。API 不单独发布宿主机端口，PostgreSQL 只绑定本机回环地址。

当前配置仅供本机访问。若要部署到局域网或公网，必须先另行设计认证、跨站请求保护和部署安全边界。

## 完成一次演示

1. 在“研究主题”中写一个具体问题，例如“长时储能如何影响高比例可再生能源电网的可靠性？”。按需调整关注维度、报告结构和时间范围。
2. 保持至少一个来源选中，然后选择“生成研究计划”。来源显示的是固定 Fixture 样本，不会发起 Web 搜索或读取你的本地文件。
3. 检查研究计划和待回答的问题；确认后选择“确认并开始”。运行期间可查看每个来源搜索任务（SearchTask）的执行状态和按顺序排列的事件，也可以取消运行。
4. 完成后查看证据池和报告。点击报告中的引用编号，会跳到本次运行对应的证据条目。Fixture 证据与报告都只是流程演示数据。
5. 侧栏“最近研究”可切换历史任务；“数据源状态”显示当前 Mock 配置。

## 页面区域

| 区域 | 用途 |
|---|---|
| 新建研究 | 填写主题、来源、关注维度、报告结构和可选时间范围，生成计划 |
| 研究计划 | 启动前检查系统拆分的问题和流程步骤 |
| 运行进度与来源搜索任务（SearchTask） | 查看当前阶段、每个来源搜索任务的执行状态和进度 |
| 事件时间线 | 按顺序查看本次运行记录；连接恢复时会继续读取保存的事件 |
| 证据池 | 检查当前运行使用的固定样本和摘录 |
| 研究报告 | 查看演示报告，并通过引用编号定位证据 |
| 最近研究 | 查看或切换已保存的历史运行 |
| 数据源状态 | 确认当前是 Mock 配置；它不表示真实服务已连接 |

## 架构概览

```mermaid
flowchart LR
  Browser[本机浏览器：Vue 工作台] --> Frontend[前端服务与本机代理]
  Frontend -->|REST 与 SSE| API[FastAPI：任务、计划、事件]
  API --> Graph[有界 LangGraph：固定 Mock Fixture]
  API --> ORM[SQLAlchemy 持久化]
  ORM --> DB[(PostgreSQL：历史与事件)]
```

工作台通过 REST 创建任务和读取详情，通过 SSE 接收保存后的运行事件。LangGraph 流程使用固定 Mock Fixture；PostgreSQL 保存任务、证据、报告和事件。前端以 Vue 3、TypeScript、Vite 和 Pinia 构建。

## 停止服务与历史数据

停止容器：

```powershell
docker compose down
```

这会停止并移除容器，但保留名为 `postgres_data` 的数据库卷。下次运行 `docker compose up -d` 时，历史记录仍可读取。

如果确定要清空演示历史和数据库数据，运行：

```powershell
docker compose down -v
```

`-v` 会删除 `postgres_data`，其中的历史记录无法恢复；`.env` 文件不会随之删除。

## 常见问题

- **页面打不开：**确认 Docker 正在运行，再执行 `docker compose ps` 查看容器状态；首次启动等待镜像构建和服务健康检查完成。
- **服务未就绪或页面显示请求错误：**查看服务日志：

  ```powershell
  docker compose logs --tail=100 frontend api db
  ```

- **本机端口已被占用：**编辑 `.env` 中的 `WEB_PORT` 或 `POSTGRES_PORT`，改为可用端口后重新启动。默认访问地址为 `http://localhost:5173`；如果 `.env` 中保留了自定义 `WEB_PORT`，访问 `http://localhost:<WEB_PORT>`，并将 `<WEB_PORT>` 替换为实际端口。
- **报告没有引用或显示证据缺口：**这是固定 Fixture 的演示结果；并非每个主题都会匹配到样本证据。
- **数据源状态显示 Mock：**这是阶段 A 的预期状态。项目不需要 API Key，也没有接入真实搜索或模型服务。

## 本机开发

需要 Docker Compose、Python 3.12+、`uv`，以及 Node.js `^22.22.2 || >=24.15.0`（22.x 中从 22.22.2 起，或 24.15.0 及以上）。如尚未安装 `uv`，请按[官方安装指南](https://docs.astral.sh/uv/getting-started/installation/)安装。先复制环境文件并启动 PostgreSQL：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d db
```

在一个终端启动 API：

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://deepresearch:deepresearch-local-only@127.0.0.1:54329/deepresearch"
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn deepresearch_api.main:app --host 127.0.0.1 --port 8000
```

示例 `DATABASE_URL` 使用 `.env.example` 的默认账号、密码、数据库名和 `POSTGRES_PORT=54329`。若你改过 `.env`，请同步修改连接 URL 中的主机端口、用户名、密码和数据库名，使其分别匹配 `POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD` 和 `POSTGRES_DB`。

另开终端安装前端依赖并启动 Vite：

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

开发前端默认在 `http://localhost:5173` 提供页面，并将 `/api`、`/docs` 和 `/openapi.json` 代理到 `http://127.0.0.1:8000`。API 和开发前端仅监听本机地址。Compose 默认配置和端口见 `.env.example` 与 `docker-compose.yml`。

开发场景开关默认关闭。仅本地 API 验收需要特殊 Fixture 时，可在 `.env` 设置 `MOCK_SCENARIOS_ENABLED=true`，再运行 `docker compose up --build -d api frontend`。普通工作台没有 scenario 选择器。

开发检查命令：

```powershell
uv run --directory backend pytest
npm --prefix frontend run check:api-types
npm --prefix frontend run type-check
npm --prefix frontend run test:unit -- --run
npm --prefix frontend run build
docker compose config --quiet
```

REST 契约变更后，运行 `npm --prefix frontend run generate:api-types`，根据 FastAPI OpenAPI 更新前端 schema；`npm --prefix frontend run check:api-types` 会核对已生成文件。自动化测试覆盖输入和错误契约、计划与运行控制、Fixture 场景、报告引用、SSE 回放及历史分页。PostgreSQL 并发锁的集成验收尚未验证；API 自动测试使用 SQLite 临时库覆盖事务路径，正式运行仍使用 PostgreSQL。

## 目录职责

- `frontend/src/`：Vue 工作台、REST/SSE 客户端与 Pinia 状态。
- `backend/src/deepresearch_api/`：FastAPI、请求契约、固定 Mock 流程和持久化模型。
- `backend/migrations/`：Alembic 数据库迁移。
- `docs/api-and-events.md`：REST 路由和 SSE 恢复语义。
- `design-system/deepresearch/`：界面规则与工作台页面约束。
- `_bmad-output/`：需求、设计和实现记录。
- `outputs/`：阶段 A 技术研究和方案。

技术选型与阶段边界见 [`outputs/phase-a-technical-research.md`](outputs/phase-a-technical-research.md) 和 [`outputs/phase-a-technical-proposal.md`](outputs/phase-a-technical-proposal.md)。
