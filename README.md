# AI Gateway Proxy

企业级 OpenAI API 代理网关，支持 Microsoft OAuth2 认证、API Key 管理、Token 用量统计分析。

## 功能特性

- 🔐 **Microsoft OAuth2 登录** — 企业用户直接使用 Microsoft 账号登录
- 🛡️ **本地账号** — 超级管理员使用用户名/密码登录
- 🔑 **API Key 管理** — 生成、查看、撤销 API Keys，支持速率限制和每日 Token 配额
- 📊 **用量统计** — 实时 Token 用量、趋势图表、模型分布分析
- 🚀 **OpenAI 代理** — 全透明代理 OpenAI API，支持 Streaming
- 👥 **用户管理** — 管理员可管理所有用户、Key 和查看全局统计

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.11 |
| 数据库 | PostgreSQL 15 |
| 缓存/限流 | Redis 7 |
| 前端 | Vue3 + TypeScript + Element Plus |
| 部署 | Docker Compose + Nginx |

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

必填配置：
- `SECRET_KEY` — 随机密钥，可用 `openssl rand -hex 32` 生成
- `POSTGRES_PASSWORD` — 数据库密码
- `AZURE_CLIENT_ID/SECRET/TENANT_ID` — Azure AD 应用注册信息
- `AZURE_REDIRECT_URI` — 回调地址（需与 Azure 注册一致）
- `FRONTEND_URL` — 前端访问地址（用于 OAuth 回调重定向）

### 2. 启动服务

```bash
docker-compose up -d --build
```

### 3. 访问

- **前端控制台**: http://your-domain
- **API 文档**: http://your-domain:8000/api/docs
- **首次登录**:
  - 用户名: `openai`
  - 密码: `openai`
  - ⚠️ 请立即修改密码！

## Azure AD 配置

在 [Azure Portal](https://portal.azure.com) 注册应用时需要：

1. **平台**: Web
2. **重定向 URI**: `https://your-domain/api/v1/auth/oauth/callback`
3. **权限**: `User.Read`（Microsoft Graph）

## API Key 使用方式

创建 Key 后，在请求 OpenAI 兼容接口时使用：

```bash
curl http://your-domain/v1/chat/completions \
  -H "Authorization: Bearer sk-your-gateway-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 项目结构

```
ai-getway-proxy/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/       # API 路由
│   │   ├── core/         # 配置、数据库、安全
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   ├── schemas/      # Pydantic 验证模型
│   │   └── services/     # 业务逻辑
│   └── Dockerfile
├── frontend/             # Vue3 前端
│   ├── src/
│   │   ├── api/          # Axios API 客户端
│   │   ├── views/        # 页面组件
│   │   ├── stores/       # Pinia 状态管理
│   │   └── router/       # 路由配置
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 开发指南 (Development Guide)

为了方便其他开发者共享代码和二次开发，本项目提供了专门的开发环境配置，支持**代码热重载 (Hot Reload)**。无需在本地安装 Node.js 或 Python 环境，所有依赖都在 Docker 容器内解决。

### 1. 准备配置文件
复制并修改开发环境变量：
```bash
cp .env.example .env
```

### 2. 启动开发环境
使用专用于开发的 Compose 文件启动项目：
```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### 3. 开发特性说明
启动成功后：
- **后端热重载**: 源码挂载在 `./backend:/app`，任何 `backend/**/*.py` 的修改都会触发 uvicorn 自动重启。
- **前端热重载**: 源码挂载在 `./frontend:/app`，Vite 监听修改并进行 HMR (Hot Module Replacement) 热更新。
- **日志查看**: 所有的后端日志均会实时输出到终端，也可以查看自动挂载到本机的 `backend/logs/app.log` 文件。
- **本地访问端口**:
  - 前端界面: `http://localhost:3000`
  - 后端 API: `http://localhost:8000`
  - Swagger 接口文档: `http://localhost:8000/api/docs`

### 4. 停止与清理
停止开发容器并保留数据库数据：
```bash
docker compose -f docker-compose.dev.yml down
```
*(如果需要彻底清理包括数据库在内的所有数据，请加上 `-v` 参数)*

## 🗄️ 数据库管理与迁移指南 (Database Migration Guide)

本项目使用 **Alembic** 配合 SQLAlchemy 进行数据库的版本迭代与迁移管理。这允许开发人员无需手动操作 SQL 即可安全地同步数据库表结构。

### 1. 迁移设计与最佳实践
所有的数据库定义均存放在 `backend/app/models/` 目录下。
> [!IMPORTANT]
> **请勿在数据库中直接执行 `CREATE TABLE` 或 `ALTER TABLE`！** 
> 任何数据库表结构的改动（新增表、删除表、修改字段名/类型等），均**必须**通过 Alembic 迁移脚本来完成。

---

### 2. 数据库变更操作步骤 (开发流)

当您在 `backend/app/models/` 中新增、修改或删除了 SQLAlchemy 模型后，请按照以下三个步骤生成并运行迁移：

#### 第一步：自动生成迁移脚本 (Autogenerate)
在开发容器后台，让 Alembic 自动对比最新的 Python 模型与当前数据库状态，自动生成带版本号的迁移脚本：
```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "描述您的变更_例如_add_provider_name_to_logs"
```
* 执行完毕后，会在 `backend/alembic/versions/` 下生成一个 `.py` 脚本（例如 `1a2b3c4d5e6f_add_provider_name_to_logs.py`）。
* **强烈建议**：打开这个新生成的版本文件，人工检查 `upgrade()` 和 `downgrade()` 内的数据库变更是否完全符合您的预期。

#### 第二步：应用迁移到开发数据库 (Upgrade)
将自动生成的最新脚本应用到您的开发 PostgreSQL 中：
```bash
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

#### 第三步：提交迁移脚本
* 确认迁移在本地运行成功后，将生成的 `backend/alembic/versions/*.py` 脚本文件一同 `git add` 并 `git commit` 提交到代码仓库中。
* 这样，其他开发人员或生产环境通过拉取最新代码，只需运行 `alembic upgrade head` 即可同步升级他们的数据库，保证全平台表结构绝对一致。

---

### 3. 其他常用迁移管理命令

* **查看当前数据库版本状态**：
  ```bash
  docker compose -f docker-compose.dev.yml exec backend alembic current
  ```
* **查看完整迁移历史记录**：
  ```bash
  docker compose -f docker-compose.dev.yml exec backend alembic history --verbose
  ```
* **版本回滚（降级到上一版本）**：
  ```bash
  docker compose -f docker-compose.dev.yml exec backend alembic downgrade -1
  ```
* **直接将数据库标记为最新（常用于导入存量旧数据后的初始化）**：
  ```bash
  docker compose -f docker-compose.dev.yml exec backend alembic stamp head
  ```

