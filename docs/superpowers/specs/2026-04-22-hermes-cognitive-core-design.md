# Hermes-Style Cognitive Core Design

## 1. Goal

为 Jarvis 设计一套参考 Hermes Agent 的“认知内核”，让系统从当前以桌面入口驱动的助手，升级为 **服务端常驻 Agent Core**。第一阶段聚焦四项核心能力：

1. 跨会话检索过去任务、对话与工具轨迹
2. 持续维护用户画像与环境/项目记忆
3. 在任务完成后自动沉淀、更新、版本化技能
4. 让后续相似任务优先复用既有技能与经验，而不是重新从零执行

本阶段优先建设“脑子”，不优先建设 Telegram / Discord / Slack 网关与 cron 调度执行层，但所有接口都要为这些未来入口预留。

## 2. Scope

### In Scope

- 在 `jarvis-server` 中引入常驻的 Agent Core 服务层
- 抽离认知内核四个子系统：Memory Manager、Session Recall、Skill Registry、Learning Loop
- 统一接收桌面端请求，并为未来多平台入口预留相同的会话入口协议
- 支持任务结束后的自动复盘、记忆提炼、技能生成/技能更新
- 支持可见的技能元数据、技能版本、技能来源任务追踪
- 支持检索过去会话 / 工具轨迹 / 学习记录
- 为高风险技能生成增加自动保守策略

### Out of Scope

- Telegram / Discord / Slack / WhatsApp 等多平台网关实现
- cron 调度、自然语言定时任务执行
- 终端 / 浏览器 / 容器后端的大规模重构
- 向量数据库或 embedding 检索作为第一阶段必选项
- 完整复刻 Hermes CLI / TUI 交互界面

## 3. Current-State Assessment

当前 Jarvis 已有若干认知内核前置能力，但仍是分散状态：

- 有基础的 `MemoryEntry`、`PreferenceState`、`WorkspaceState`、`UploadedContext` 等持久化模型
- 有桌面端主控台、结构化 trace/proposal/error 事件、工具调用轨迹展示
- 有会话恢复、偏好记忆、上传资料回忆、统一 orchestrator 主线
- 仍缺少稳定的跨会话检索层、技能仓库、任务后学习闭环、自动技能沉淀策略
- 当前“记忆”和“经验复用”仍偏数据存储，不是一个真正的常驻认知服务

因此，本设计不是推翻 Jarvis，而是在已有 FastAPI + Electron + orchestrator 基础上，把“记忆 / 检索 / 技能 / 学习”抽成统一服务内核。

## 4. Recommended Approach

采用 **方案 A：认知内核服务化**。

Jarvis 将被拆成三层：

1. **接入层**：桌面端作为当前入口；未来网关、cron、远程客户端都复用同一个后端 Agent Core
2. **Agent Core**：常驻服务，统一持有会话状态、上下文装配、技能命中、工具执行编排、学习闭环触发
3. **认知子系统**：Memory Manager、Session Recall、Skill Registry、Learning Loop

该方案的关键价值：

- 未来增加平台入口时，不需要复制一套认知逻辑
- 技能与记忆的沉淀发生在统一后端，而不是散落在桌面逻辑里
- 便于后续引入自动化调度、多平台连续会话、长期运行

## 5. Architecture

### 5.1 High-Level Topology

```text
Desktop UI / Future Gateway / Future Cron
                |
                v
          Agent Core Service
                |
     +----------+----------+----------+----------+
     |                     |                     |
     v                     v                     v
Memory Manager       Session Recall        Skill Registry
                \         |         /
                 \        v        /
                    Learning Loop
                           |
                           v
                   Existing Tool / Orchestrator Layer
```

### 5.2 Agent Core Responsibilities

Agent Core 是未来所有入口共享的“脑中枢”，职责如下：

- 接收用户请求与会话上下文
- 装配短期上下文、长期记忆、检索回忆、候选技能
- 选择是否命中已有技能
- 驱动现有 orchestrator / tool runtime 完成任务
- 统一输出结构化执行事件
- 在任务结束后触发 Learning Loop

Agent Core 不负责具体 UI 呈现，不直接绑死在 Electron，也不把技能和记忆逻辑散落到路由层。

## 6. Cognitive Subsystems

### 6.1 Memory Manager

Memory Manager 负责长期事实管理，而不是全文检索。

它维护两类核心内容：

- **Agent Memory**：环境事实、项目约束、技术约定、已验证经验
- **User Profile**：你的表达风格、回复偏好、工具偏好、项目习惯、风险偏好

它必须具备：

- 去重与合并
- 容量控制
- 冲突更新
- 低价值信息过滤

不是所有任务结果都写入长期记忆；只有稳定事实、偏好、约束、长期有用的经验才升级进入这一层。

### 6.2 Session Recall

Session Recall 负责“回忆以前发生过什么”。

它保存并可检索：

- 历史对话
- 任务执行摘要
- 工具调用轨迹
- learning record
- 技能命中与技能生成来源

第一阶段检索策略：

- PostgreSQL 文本检索
- 时间范围过滤
- 类型过滤（会话 / 任务 / 工具 / 学习记录）
- 命中后摘要回放

这层解决的是“过去做过什么、怎么做的、结果如何”，不是长期人格记忆。

### 6.3 Skill Registry

Skill Registry 是认知内核里的技能仓库。

每个技能至少有两部分：

1. **数据库元数据**：名称、类别、版本、触发条件、启用状态、来源任务、命中次数、风险等级
2. **文件正文**：`SKILL.md` 以及引用资料、模板、补充资产

建议路径：

```text
runtime/skills/<category>/<skill-name>/SKILL.md
runtime/skills/<category>/<skill-name>/references/*
runtime/skills/<category>/<skill-name>/templates/*
runtime/skills/<category>/<skill-name>/artifacts/*
```

第一阶段不只把技能当文档，而是把它当成 **结构化可治理资产**：

- 可启用 / 停用
- 可更新版本
- 可追踪来源任务
- 可统计命中率
- 可区分自动生成与人工编辑

### 6.4 Learning Loop

Learning Loop 是第一阶段最关键的 Hermes 借鉴点。

每个任务结束后，Learning Loop 自动运行一次 post-run review，输出 `learning record`，再做三类判定：

1. 这次任务是否沉淀为长期记忆？
2. 这次任务是否生成 / 更新技能？
3. 这次任务是否只保留为可检索历史，不做升级？

Learning Loop 的输入来自：

- 最终用户请求
- 执行过程中的结构化事件
- 工具调用列表
- 结果摘要
- 错误 / 重试 / 澄清信息

Learning Loop 的输出必须是结构化记录，而不是仅一段自由文本总结。

## 7. Task Lifecycle

一次任务的完整生命周期如下：

1. 用户请求进入 Agent Core
2. Agent Core 读取：
   - 当前会话上下文
   - 用户画像
   - 长期记忆
   - 相关历史会话摘要
   - 候选技能
3. Agent Core 决定：
   - 是否命中已有技能
   - 是否直接裸跑 orchestrator
4. 执行过程中产出结构化事件：
   - `thought_step`
   - `tool_call`
   - `observation`
   - `proposal`
   - `result`
5. 任务结束后触发 Learning Loop
6. Learning Loop 产出 `learning record`
7. 系统自动执行以下一种或多种沉淀动作：
   - 写入长期记忆
   - 创建 / 更新技能
   - 仅保存为 Session Recall 轨迹
8. 下一次相似请求优先命中技能与历史经验

设计约束：**技能生成只发生在任务后，不在每轮中间回复时即时生成。**

## 8. Data Model Strategy

第一阶段采用 **PostgreSQL + 文件技能仓库** 的混合架构。

### 8.1 PostgreSQL Tables

建议新增或扩展的逻辑模型：

- `memory_facts`
  - `fact_type`
  - `subject`
  - `value`
  - `source`
  - `confidence`
  - `last_confirmed_at`
- `user_profile_facts`
  - `profile_type`
  - `value`
  - `source`
  - `last_confirmed_at`
- `session_artifacts`
  - `artifact_type`
  - `session_id`
  - `summary`
  - `payload`
  - `created_at`
- `learning_records`
  - `session_id`
  - `task_summary`
  - `outcome`
  - `memory_candidates`
  - `skill_candidates`
  - `decision`
  - `created_at`
- `skill_index`
  - `skill_name`
  - `category`
  - `version`
  - `status`
  - `risk_level`
  - `source_session_id`
  - `source_learning_record_id`
  - `hit_count`
  - `updated_at`

### 8.2 Skill Files

技能正文继续落文件，而不是塞进数据库大字段。这么做有三个原因：

- 更像 Hermes 的技能生态
- 更便于 Agent 自动维护具体技能目录
- 更适合未来导出、版本管理、人工审阅

### 8.3 Retrieval Strategy

第一阶段检索不强制引入向量库，先用：

- PostgreSQL 文本检索
- 时间 / 类型过滤
- LLM 摘要压缩

等后续实际出现召回瓶颈，再决定是否增加向量召回层。

## 9. Guardrails

由于第一阶段要求“全自动沉淀”，必须加硬闸门。

### 9.1 Completion Gate

只有任务成功、或至少形成稳定可复用步骤时，才允许进入技能候选。

### 9.2 Repeatability Gate

同类套路应满足下列之一才升格技能：

- 被重复命中至少两次
- 或单次任务中已经表现出非常清晰、稳定、可复用的固定步骤

否则仅保存为 Session Recall 经验轨迹。

### 9.3 Risk Gate

涉及以下能力的技能默认只生成草稿，不自动启用：

- 删除 / 覆写
- 命令执行
- 系统控制
- 外网写操作
- 高风险桌面动作

### 9.4 Quality Gate

自动生成技能后，必须经过一次技能自检，至少验证：

- 触发条件是否明确
- 步骤是否可执行
- 依赖是否完整
- 失败回退是否存在

### 9.5 Memory Capacity Gate

长期记忆必须有容量上限与合并策略，禁止无限累积低价值事实。

## 10. API / Integration Direction

第一阶段不强制改掉全部现有 API，但新能力应以 Agent Core 接口优先。

建议新增的服务能力方向：

- `POST /api/agent/run`
  - 单次任务执行入口
- `POST /api/agent/learn`
  - 手动/异步触发学习闭环
- `GET /api/agent/recall`
  - 查询历史会话 / 任务 / 工具轨迹
- `GET /api/agent/skills`
  - 查询技能索引
- `POST /api/agent/skills/:name/enable`
  - 启用技能
- `POST /api/agent/skills/:name/disable`
  - 停用技能
- `GET /api/agent/profile`
  - 用户画像视图

桌面端第一阶段只需要接这些能力，不必知道认知子系统内部细节。

## 11. Failure Handling

### 11.1 Failed Tasks

- 失败任务默认不自动升级为启用技能
- 失败任务仍可保留为 Session Recall 轨迹
- 失败任务可以产出“负经验”，用于避免重复犯错

### 11.2 Low-Confidence Learning

当 Learning Loop 置信度不足时：

- 不写长期记忆
- 不生成启用技能
- 只保留 learning record，等待后续复核或重复命中

### 11.3 Skill Pollution Control

- 自动生成技能默认分为 `draft` 和 `active`
- 高风险 / 低置信技能只能进入 `draft`
- `active` 只能来自通过质量闸门的技能

## 12. User-Visible Outcomes

第一阶段必须让“技能沉淀可见”，不能只做后端黑盒。

用户至少应能看到：

- 哪个任务产出了 learning record
- 是否写入长期记忆
- 是否生成/更新了技能
- 技能版本和来源
- 下次任务是否命中了某个既有技能

可见性可以体现在桌面端日志、状态面板或技能列表视图，不要求第一阶段就做完整 Hermes 风格技能中心 UI，但必须能被观察和验证。

## 13. Acceptance Criteria

本设计的第一阶段验收标准如下：

1. **跨会话检索可用**  
   能查到过去任务、过去对话、过去工具轨迹，并返回摘要。

2. **用户画像可见**  
   Jarvis 能稳定记住风格、偏好、项目环境，并在下一会话生效。

3. **技能沉淀可见**  
   完成复杂任务后，系统会自动生成或更新技能文件，并能看到来源与版本。

4. **技能复用可见**  
   第二次遇到相似任务时，Agent Core 会命中已有技能，而不是重新裸跑。

5. **失败不污染**  
   失败任务默认不会写成启用技能，高风险技能不会自动启用。

## 14. Testing Strategy

### 14.1 Unit Tests

- 记忆筛选逻辑
- 画像提炼逻辑
- 学习记录生成逻辑
- 技能升级判定逻辑
- 风险闸门与质量闸门逻辑

### 14.2 Integration Tests

- 一次完整任务结束后，是否真的写入：
  - `session_artifacts`
  - `learning_records`
  - `memory_facts` / `user_profile_facts`
  - skill file + skill index

### 14.3 Behavioral Regression

- 第二次类似任务是否会命中已沉淀技能
- 高风险技能是否默认保持 draft
- 失败任务是否不会污染 active skills

## 15. Decomposition Boundary

这个 spec 只覆盖 **Hermes 风格认知内核第一阶段**，适合单独形成一个 implementation plan。

后续应作为独立后续 spec 再做的内容：

- 多平台消息网关
- cron / 自动化调度
- 远程执行环境与 serverless 常驻
- 大规模子代理与分布式执行拓扑

## 16. Recommended Next Step

下一步应基于本 spec 写 implementation plan，拆成至少四个实施任务：

1. Agent Core 服务边界与 API
2. Memory / Recall 数据模型与检索层
3. Skill Registry 与技能文件运行时
4. Learning Loop 自动沉淀与可见性
