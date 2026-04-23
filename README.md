# Jarvis

> 基于 Moonshot Kimi + 阿里云语音的桌面 AI 助手原型

Jarvis 是一款本地优先的桌面 AI 助手，使用 **Electron + React** 作为前端，**FastAPI（Python）** 作为本地后端，通过 Kimi 大语言模型提供对话与推理能力，通过阿里云 DashScope（Paraformer ASR / CosyVoice TTS）实现语音交互。

## ✨ 主要功能

| 功能模块 | 说明 |
|---|---|
| 语音对话 | 麦克风实时采集 → ASR → LLM → TTS 全链路语音交互，支持语音打断 |
| 唤醒词 & 澄清 | "Jarvis" 唤醒词容错、技术词纠偏、低风险澄清 / 高风险强确认 |
| 知识库搜索 | 本地文件、知识库索引、网页搜索、自动搜索策略、资料上传 |
| 系统动作 | 文件读写、命令执行、受控网页动作（`fetch_web` / `open_web_page`），含风险分级与动作审计 |
| 记忆与偏好 | 偏好持久化、会话恢复、工作台恢复、学习进度追踪 |
| 托盘常驻 | 关闭窗口后缩到系统托盘，保持后台可用 |
| 受限启动 | 数据库不可用时仍可启动前端，`/api/health` 返回 `degraded: true` |

## 🏗️ 项目结构

```
jarvis/
├── electron/          # Electron 主进程（TypeScript）
├── jarvis-ui/         # React 前端（Vite 构建，独立 package.json）
├── jarvis-server/     # FastAPI 后端
│   ├── app/
│   │   ├── config.py  # 统一环境变量读取（pydantic-settings）
│   │   ├── routers/   # API 路由
│   │   └── services/  # LLM / ASR / TTS / 知识库 / 动作等服务
│   └── requirements.txt
├── contracts/         # 前后端接口契约（JSON Schema）
├── scripts/           # 开发辅助脚本
├── docs/              # 设计文档
├── package.json       # 根包（管理 Electron 构建及开发脚本，非 npm workspaces）
└── .env.example       # 环境变量示例（无真实密钥）
```

## 📦 公开仓库边界

本仓库为公开发布的源代码快照，以下内容**包含在内**：

- 所有源代码（`electron/`、`jarvis-ui/src/`、`jarvis-server/app/`）
- 接口契约（`contracts/`）
- 设计文档（`docs/`）
- 构建与开发脚本（`scripts/`）
- 依赖声明（`package.json`、`jarvis-ui/package.json`、`jarvis-server/requirements.txt`）
- 配置模板（`.env.example`）

以下内容**有意排除**，不会出现在仓库中：

| 排除项 | 原因 |
|---|---|
| `.env` | 含真实 API Key 等敏感信息 |
| `jarvis-server/jarvis-data/` | 运行时数据（知识库索引、上传文件等） |
| `runtime/` | 本地运行时产物（日志、临时文件等） |
| `.worktrees/` | 本地 git worktree 工作目录，非源码 |
| `node_modules/`、`jarvis-ui/node_modules/` | 依赖安装产物 |
| `dist/`、`dist-electron/` | 构建产物 |
| `.venv/` | Python 虚拟环境 |
| `jarvis.db` | 本地 SQLite 数据（如有） |

## 🚀 快速开始

### 前置条件

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **PostgreSQL** ≥ 14（本地运行，创建数据库 `jarvis`）
- Moonshot [Kimi API Key](https://platform.moonshot.cn/)
- 阿里云 [DashScope API Key](https://dashscope.console.aliyun.com/)（语音功能）

### 安装

```bash
# 1. 克隆仓库（将下方 URL 替换为本仓库在 GitHub 上的实际地址，可在仓库主页"Code"按钮处复制）
git clone <本仓库 URL>
cd jarvis

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key 和本地路径

# 3. 安装 Python 依赖
cd jarvis-server && pip install -r requirements.txt && cd ..

# 4. 安装根包 Node 依赖（Electron 构建工具链）
npm install

# 5. 安装前端 Node 依赖（jarvis-ui 拥有独立的 package.json）
cd jarvis-ui && npm install && cd ..
```

> **注意**：根目录的 `npm install` 和 `jarvis-ui` 目录下的 `npm install` 均需执行，
> 因为本项目未使用 npm workspaces，两个 `package.json` 相互独立。

### 运行（开发模式）

```bash
npm run dev:desktop
```

此命令先执行 `build:ui` 将 React 前端构建到 `dist/`，然后并行启动：TypeScript 监听编译（`watch:electron`）、FastAPI 后端（`dev:server`）、Electron 主进程（`dev:electron`）。**前端不启动 Vite 开发服务器**——Electron 直接加载 `dist/` 中的静态产物；修改 UI 代码后需重新运行 `npm run build:ui`（或重启 `dev:desktop`）才能生效。

### 仅启动后端

```bash
npm run dev:server
```

## ⚙️ 环境变量说明

将 `.env.example` 复制为 `.env` 并填写以下变量：

| 变量名 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `DATABASE_URL` | | `postgresql+psycopg://postgres:postgres@127.0.0.1:5432/jarvis` | PostgreSQL 连接串，格式：`postgresql+psycopg://user:pass@host:port/dbname` |
| `JARVIS_SERVER_HOST` | | `127.0.0.1` | 后端监听地址 |
| `JARVIS_SERVER_PORT` | | `8001` | 后端监听端口 |
| `JARVIS_KNOWLEDGE_ROOT` | | （代码内置开发环境专用默认路径，**外部用户须覆盖此项**） | 本地知识库根目录路径 |
| `KIMI_API_KEY` | | `""` | Moonshot Kimi API Key；**AI 对话功能必填** |
| `KIMI_BASE_URL` | | `https://api.moonshot.ai/v1` | Kimi API 基础 URL |
| `KIMI_MODEL` | | `kimi-k2.5` | 使用的模型名称 |
| `KIMI_TIMEOUT_SECONDS` | | `60` | 请求超时（秒） |
| `KIMI_SYSTEM_PROMPT` | | 内置默认 | 系统 Prompt（可选覆盖） |
| `ALIYUN_DASHSCOPE_API_KEY` | | `""` | 阿里云 DashScope API Key；**语音功能必填** |
| `ALIYUN_ASR_MODEL` | | `paraformer-realtime-v2` | ASR 模型 |
| `ALIYUN_TTS_MODEL` | | `cosyvoice-v1` | TTS 模型 |
| `ALIYUN_TTS_VOICE` | | `longxiaochun` | TTS 音色（可选：longxiaochun / longxiaobai / longwan / longcheng / longhua） |
| `ALIYUN_SPEECH_LANGUAGE` | | `zh-CN` | 语音识别语言 |

## 🔧 运行时配置（无需重启，应用内调整）

以下常用设置可直接在应用界面中修改，**无需编辑 `.env` 或重启服务**：

| 设置项 | 说明 |
|---|---|
| LLM 提供商 | 切换当前使用的 LLM Provider（从已配置的提供商中选择） |
| LLM 模型 | 修改当前提供商使用的模型名称（如 `kimi-k2.5`、`gpt-4.1` 等） |
| 语音提供商 | 语音服务提供商（当前支持 `aliyun`） |
| 音色（Voice） | TTS 音色（如 `longxiaochun` / `longxiaobai` 等） |
| 知识库路径 | 本地知识库根目录，修改后**立即生效**，知识库搜索将使用新路径，无需重启 |

**操作方式**：在应用首页找到"当前配置："摘要行 → 点击**展开配置** → 修改对应字段 → 点击**保存配置**。

> 上述设置保存后会持久化到 `runtime-config.json`，优先级高于 `.env` 环境变量中的对应项。
> 若需重置为环境变量默认值，点击**重新加载配置**即可。



```bash
# 前端测试
cd jarvis-ui && npx vitest run

# 后端测试
cd jarvis-server && pytest

# Electron 测试
npm run test:electron
```

## ⚠️ 当前限制

- 本项目为桌面端原型，目前**仅支持 Windows**（路径处理与 Electron 构建配置以 Windows 为基准）
- 系统动作（文件操作、命令执行）需用户手动审批，风险分级规则见 `docs/`
- 不包含用户认证系统，建议仅在本地可信环境运行
- 语音链路依赖阿里云外部服务，离线环境下不可用
- **网页搜索**：知识库搜索模块支持网页搜索及自动搜索回退策略；触发时，搜索查询会发送至外部搜索服务商（目前为 DuckDuckGo）

## 📄 许可证

[Apache License 2.0](./LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request，详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 🔒 安全

如发现安全漏洞，请参阅 [SECURITY.md](./SECURITY.md) 中的负责任披露流程，**不要**直接在公开 Issue 中描述漏洞细节。
