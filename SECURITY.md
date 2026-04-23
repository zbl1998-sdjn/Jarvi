# 安全政策

## 支持版本

本项目目前处于原型阶段，仅维护 `main` 分支的最新版本。

## 漏洞报告

**请不要通过 GitHub 公开 Issue 报告安全漏洞。** 公开披露可能在修复前被恶意利用。

### 负责任披露流程

1. 通过以下任一方式私下联系维护者：
   - 使用 GitHub **[Private Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)**（推荐）
   - 在仓库 Security 标签页点击 "Report a vulnerability"
2. 提供以下信息（尽可能详细）：
   - 漏洞类型（如：命令注入、路径遍历、信息泄露等）
   - 复现步骤
   - 影响范围及潜在危害评估
   - 如有，附上概念验证（PoC）代码或截图
3. 维护者会在 **72 小时内**确认收到报告，并在 **14 个工作日内**提供初步评估结果
4. 修复发布后，我们会在 Release Notes 中注明致谢（如你希望保持匿名请说明）

## 密钥与数据处理预期

- 所有 API Key（Kimi、阿里云 DashScope 等）须存放于**本地 `.env` 文件**，绝不提交至版本控制
- `.env.example` 只包含占位符，不包含任何真实密钥或账号信息
- 本项目**没有**厂商托管的 Jarvis 云后端；对话请求与所有本地操作均由本机 `jarvis-server` 进程处理，不经过任何外部 Jarvis 服务器
- 对话内容（系统 Prompt、用户消息及上下文）会作为请求负载发送至 **Kimi API**（Moonshot），受其隐私政策约束
- 语音音频（ASR 录音输入、TTS 合成请求）会发送至**阿里云 DashScope**，受其隐私政策约束
- 搜索查询（包括手动触发的网页搜索及自动搜索回退）会发送至外部网页搜索服务商（目前为 **DuckDuckGo**），受其隐私政策约束
- 本地数据由 `jarvis-server` 进程写入，分为三类独立存储：
  1. **数据库记录**（对话历史、知识条目元数据等）：写入 `DATABASE_URL` 所指向的 PostgreSQL 实例（默认为本机）
  2. **上传附件**：原始文件存储于本地文件系统 `jarvis-data/attachments/` 目录，不经过任何外部服务
  3. **本地知识源文件**：原始文件保留在本机（`JARVIS_KNOWLEDGE_ROOT` 目录），不会被上传；但在对话中用作上下文时，相关文本片段会随请求发送至 **Kimi API**，受其隐私政策约束
- `runtime/` 目录包含本地运行时数据，不应被提交或共享

## 已知限制与注意事项

- 系统动作（文件操作、命令执行）在用户确认后执行，建议**仅在本地可信环境**运行
- 本项目不包含用户认证机制，不适合暴露在公网
- 建议定期轮换 API Key，尤其是怀疑泄露时

## 安全联系

如有任何安全相关问题，欢迎通过 GitHub Security Advisory 渠道联系我们。
