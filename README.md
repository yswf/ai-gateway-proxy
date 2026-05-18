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
