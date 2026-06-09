# AI自动化测试平台 V3.0

企业级 AI 全栈自动化测试平台。

## 特性

- **模块化独立页面**：项目管理 + 版本/测试点/功能/用例/计划/执行/报告，人工关联项目
- **AI 预置**：6 个常用大模型 + 4 个完整 Agent 文件结构，Key 可单独配置
- **RBAC 权限**：6 种角色精细化管控
- **执行器插件化**：API、E2E、性能、Agent 测试等
- **统一配置**：根目录 `.env`（参考 `.env.example`）

## 快速启动

```bash
# 1. 复制配置
copy .env.example .env    # Windows
# 编辑 .env，至少填写 AI API Key

# 1.5 若 Docker 拉镜像报 401（daocloud），见 docs/DEPLOYMENT.md「镜像加速器」

# 2. Docker 一键部署
docker compose up -d --build

# 3. 访问
# 前端: http://localhost:5173
# API:  http://localhost:8000/docs
# 账号: admin / admin123
```

## 推荐测试流程

```
项目管理 → 版本 → 测试点(需求+AI) → 功能(自动) → 用例(关联计划) → 计划 → 执行 → 报告
```

各页面通过顶部 **关联项目** 选择器绑定项目。

## 文档

- [部署指南](docs/DEPLOYMENT.md)
- [使用手册](docs/USAGE.md)

## SQL 补丁（已有库升级）

按顺序执行 `sql/patches/002` ~ `006`；新库由后端启动时自动建表、种子数据与枚举。

## 技术栈

- 后端：Python 3.12 + FastAPI + SQLAlchemy + PostgreSQL
- 前端：Vue 3 + TypeScript + Element Plus + Vite
- AI：OpenAI / Qwen / DeepSeek
- 部署：Docker Compose
