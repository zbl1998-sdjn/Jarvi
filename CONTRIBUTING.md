# 贡献指南

感谢你有兴趣为 Jarvis 做贡献！提交前请阅读本文档。

## 开发环境准备

参阅 [README.md](./README.md) 完成环境配置，确保以下命令可以正常运行：

```bash
# 安装依赖
npm install
cd jarvis-server && pip install -r requirements.txt && cd ..

# 验证后端
cd jarvis-server && pytest && cd ..

# 验证前端
cd jarvis-ui && npx vitest run && cd ..

# 验证 Electron
npm run test:electron
```

## 分支规范

| 分支前缀 | 用途 | 示例 |
|---|---|---|
| `feat/` | 新功能 | `feat/voice-interrupt` |
| `fix/` | 缺陷修复 | `fix/asr-timeout` |
| `docs/` | 仅文档变更 | `docs/update-readme` |
| `chore/` | 构建/工具/依赖 | `chore/upgrade-electron` |
| `refactor/` | 代码重构（不改行为） | `refactor/config-loading` |

- 基于最新 `main` 拉取新分支，不直接向 `main` 推送
- 每个 PR 只做一件事，保持 diff 可读
- PR 标题使用中文或英文均可，但需简洁明确

## Commit 格式

遵循约定式提交（Conventional Commits）：

```
<type>: <描述>

[可选正文]
```

`type` 取值：`feat` | `fix` | `docs` | `style` | `refactor` | `perf` | `test` | `chore`

## 代码审查

- 所有 PR 需至少一名 Reviewer 批准后合并
- CI 测试（后端 pytest、前端 test、Electron test）必须全部通过
- 如果 PR 仅修改文档，可豁免 CI 但仍需 Review

## 禁止提交的内容

以下内容**绝对不能**出现在提交记录或文件中：

- **API Key / 密钥 / 密码**（包括 `.env`、hardcode 值、日志截图）
- **`runtime/` 目录**（运行时生成的数据库、缓存、日志等）
- **`.worktrees/` 目录**（本地 git worktree，属于开发者私有工作区）
- **`node_modules/`、`__pycache__/`、`dist/`、`build/`** 等构建产物
- 包含真实个人信息的测试数据

如果不小心提交了密钥，请立即联系维护者，参考 [SECURITY.md](./SECURITY.md)。

## 问题反馈

- 功能请求 / 缺陷报告 → GitHub Issues
- 安全漏洞 → 请**不要**公开 Issue，参阅 [SECURITY.md](./SECURITY.md)

## 许可证

提交代码即视为同意以 [Apache License 2.0](./LICENSE) 授权你的贡献。
