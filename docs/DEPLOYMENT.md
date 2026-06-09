# AI自动化测试平台 V3.0 - 部署指南

## 一、环境要求

| 组件 | 最低版本 |
|------|----------|
| Python | 3.12+ |
| Node.js | 20+ |
| PostgreSQL | 16+ |
| Redis | 7+ |
| Docker（可选） | 24+ |
| Docker Compose（可选） | 2.20+ |

## 二、配置说明

**所有配置统一在项目根目录 `.env` 文件中管理**，包括：

- 应用端口、密钥、CORS
- PostgreSQL / Redis / MinIO 连接
- JWT 认证参数
- AI 大模型 API Key（OpenAI、Qwen、DeepSeek 等）
- 知识库分块参数
- Celery、执行引擎、Webhook、通知等

修改 `.env` 后需重启对应服务。

### 生产环境必改项

```env
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<随机强密钥>
JWT_SECRET_KEY=<随机强密钥>
SUPER_ADMIN_PASSWORD=<强密码>
OPENAI_API_KEY=<你的密钥>
POSTGRES_PASSWORD=<强密码>
```

## 三、Docker Compose 一键部署（推荐）

### 1. 准备配置

```bash
cd e:\AIautomationnew
copy .env.example .env
# 编辑 .env，至少配置 AI API Key 和数据库密码
notepad .env
```

### 2. 启动全部服务

```bash
docker compose up -d --build
```

将启动：

| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 5432 | 数据库 |
| redis | 6379 | 缓存/队列 |
| minio | 9000/9001 | 对象存储 |
| backend | 8000 | FastAPI 后端 |
| frontend | 5173 | Nginx 静态前端 |

### 3. 验证

- 后端健康检查：http://localhost:8000/health
- API 文档：http://localhost:8000/docs
- 前端页面：http://localhost:5173

### 4. 停止与清理

```bash
docker compose down          # 停止
docker compose down -v       # 停止并删除数据卷
```

## 四、本地开发部署

### 1. 启动基础设施

可使用 Docker 仅启动中间件：

```bash
docker compose up -d postgres redis minio
```

### 2. 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 初始化数据库（自动建表 + 种子数据）
python -m app.init_db

# 启动 API
set PYTHONPATH=%CD%
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173（`npm run dev` 默认也是 5173，勿与 Docker 前端同时占用）

### 4. 手动执行 SQL 补丁（已有库升级时）

新库无需手动执行，后端 `init_db` 会自动建表并补充枚举。

| 补丁 | 说明 |
|------|------|
| `001_init.sql` | 参考建表（可选） |
| `002_requirement_docs_agents.sql` | 需求文档表 |
| `003_execution_center.sql` | 执行中心扩展 |
| `004_project_status.sql` | 项目状态 PAUSED/SUSPENDED |
| `005_version_suspended.sql` | 版本状态 SUSPENDED |

```bash
docker exec -i aitest-postgres psql -U aitest -d ai_test_platform < sql/patches/004_project_status.sql
```

## 五、Kubernetes 部署（生产）

1. 将 `.env` 中敏感项转为 K8s Secret
2. 为 backend/frontend 分别构建镜像并推送仓库
3. 部署 PostgreSQL（建议使用云 RDS）、Redis、MinIO
4. 配置 Ingress 指向 frontend，frontend nginx 反向代理 `/api` 到 backend Service
5. 执行高峰期可对执行器 Worker 进行 HPA 弹性伸缩

## 六、CI/CD Webhook 集成

在 GitLab CI / Jenkins / GitHub Actions 流水线末尾添加：

```bash
curl -X POST "http://<平台地址>/api/v1/executions/webhook/ci" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <WEBHOOK_SECRET>" \
  -d '{"plan_id": "<测试计划UUID>"}'
```

在 `.env` 中配置 `WEBHOOK_SECRET`，请求头需携带 `X-Webhook-Secret`。

## 七、监控与运维

| 监控项 | 配置项 |
|--------|--------|
| Prometheus | `PROMETHEUS_PORT` |
| Grafana | `GRAFANA_URL` |
| 日志 | 后端 stdout + Loki（扩展） |

建议告警规则：执行失败率 > 10%、AI 调用超时 > 60s、任务队列积压 > 100。

## 八、常见问题

**Q: `docker.m.daocloud.io` 返回 401 Unauthorized？**  
DaoCloud 公共镜像站已限制访问。请修改 Docker 镜像加速器（Windows：`%USERPROFILE%\.docker\daemon.json`；Docker Desktop：Settings → Docker Engine）：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run"
  ]
}
```

保存后**完全重启 Docker Desktop**（右键托盘图标 → Restart），再执行 `docker compose up -d --build`。

若仍失败，可手动从镜像站拉取并打标签：

```powershell
docker pull docker.1ms.run/library/python:3.12-slim
docker tag docker.1ms.run/library/python:3.12-slim python:3.12-slim
# 同理：nginx:alpine、postgres:16-alpine、redis:7-alpine
```

长期稳定方案：在[阿里云容器镜像服务](https://cr.console.aliyun.com)开通个人版，使用账号专属加速地址。

**Q: 数据库连接失败？**  
检查 `DATABASE_URL` 与 PostgreSQL 是否启动，Docker 环境下 host 应为 `postgres` 而非 `localhost`。

**Q: AI 生成返回演示数据？**  
在 `.env` 中配置对应供应商的 `OPENAI_API_KEY` / `QWEN_API_KEY` / `DEEPSEEK_API_KEY`。

**Q: 前端无法调用 API？**  
确认 `VITE_API_BASE_URL` 与 `APP_CORS_ORIGINS` 配置正确。
