# Jarvis

## 严格版 M1-M6 运行说明

1. 启动本机 PostgreSQL，并创建 `jarvis` 数据库。
2. 复制 `.env.example` 为 `.env`，填入 Kimi 与 Azure Speech 配置。
3. 在 `D:\Jarvis\jarvis-server` 执行 `pip install -r requirements.txt`。
4. 在 `D:\Jarvis` 执行 `npm install`。
5. 启动桌面端：`npm run dev:desktop`。
6. 如果 PostgreSQL 暂时不可用，桌面端仍可打开，但会以“服务未就绪受限态”启动，`/api/health` 会返回 `degraded: true`。

## 当前覆盖能力

| 里程碑 | 已完成能力 |
| --- | --- |
| M1 | PostgreSQL 基线、`contracts/` 契约骨架、健康检查、受限态启动、托盘常驻、中文主控台 |
| M2 | 麦克风音频分片、WebSocket 语音链路、Azure Speech ASR/TTS、语音打断、语音事件入库 |
| M3 | `Jarvis` 唤醒词容错、技术词/路径词纠偏、低风险澄清、高风险强确认、老师风格切换 |
| M4 | 本地/知识库/网页/自动搜索、统一总结、资料上传、搜索/上传工作台 |
| M5 | 文件读写、命令执行、`fetch_web` / `open_web_page` 受控网页动作、风险分级、动作审计 |
| M6 | 偏好记忆、会话恢复、工作台恢复、学习阶段进度、提醒与最近上下文 |

## 中文 Smoke Checklist

1. 点击“启动语音”，在无文本输入时点击“开始收音”，确认语音球状态会经过“聆听中 -> 思考中 -> 播报中 -> 待命”。
2. 说或输入 `Jarvis open search README`，确认主工作台切到“搜索中心”，并出现本地/知识/网页结果。
3. 切换“老师风格与音色”，确认顶部状态条、左侧偏好区和后端 `/api/home` 一致。
4. 在“资料上传”中粘贴代码或上传截图，确认“搜索中心”会显示最近资料上下文。
5. 输入 `Jarvis delete danger.txt`，确认动作进入“确认队列”；批准后，在“执行记录”里看到状态、风险、目标与结果。
6. 创建任务后确认左侧出现学习进度、提醒、最近会话与最近工作台。
7. 关闭窗口后确认应用隐藏到托盘；再次唤起后，最近会话和工作台可恢复。
