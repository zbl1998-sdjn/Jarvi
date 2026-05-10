# Release UX Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复公开首发仓的高/中优先级问题，并把模型/提供商/音色/知识库路径做成可配置的、可恢复的控制台体验。

**Architecture:** 保持 Electron + React + FastAPI 结构不变，先用 TDD 锁住默认值、安全边界、实时错误恢复和交互语义，再重构主页状态条、诊断条和内联设置区。后端以“统一配置源 + 非阻塞实时通道 + 强化审批边界”为主，前端以“控制台型首页 + 明确文本/语音分流 + 清晰错误恢复”为主。

**Tech Stack:** TypeScript, React, Vitest, Electron, FastAPI, pytest, SQLAlchemy, httpx, asyncio

---

## File Structure

- Modify: `jarvis-server/app/models.py`
  - 统一首发仓偏好默认值，确保默认音色与当前语音提供商一致。
- Modify: `jarvis-server/app/services/memory_service.py`
  - 如有需要，确保偏好读取/创建逻辑与新默认值一致。
- Modify: `jarvis-server/app/services/permission_service.py`
  - 基于“已解析真实路径”重做风险分类。
- Modify: `jarvis-server/app/services/action_service.py`
  - 先解析真实路径、再判权限，再执行动作，并把解析后的目标写进审计结果。
- Modify: `jarvis-server/app/routers/chat.py`
  - 把阻塞型模型调用移出事件循环。
- Modify: `jarvis-server/app/routers/realtime.py`
  - 增加音频缓冲上限、结构化错误事件、非阻塞语音处理。
- Modify: `jarvis-server/app/services/speech_service.py`
  - 统一默认音色/异常行为。
- Modify: `jarvis-server/app/services/summary_service.py`
  - 用真实总结替换占位输出。
- Modify: `jarvis-server/app/services/runtime_config_service.py`
  - 暴露并持久化用户可设置的 LLM / speech provider / model / voice / knowledge root。
- Modify: `jarvis-server/app/routers/assistant.py`
  - 让首页快照与设置读写返回统一运行时信息。
- Modify: `jarvis-server/tests/test_health.py`
  - 追加默认值与公开仓运行时配置测试。
- Modify: `jarvis-server/tests/test_assistant_api.py`
  - 追加配置回显与语义一致性测试。
- Create/Modify: `jarvis-server/tests/test_action_service.py`
  - 覆盖路径越界、审批和审计。
- Create/Modify: `jarvis-server/tests/test_realtime_ws.py`
  - 覆盖错误事件、缓冲上限、实时状态。
- Create/Modify: `jarvis-server/tests/test_chat_sse.py`
  - 覆盖聊天路径不阻塞的行为边界。
- Create/Modify: `jarvis-server/tests/test_summary_service.py`
  - 覆盖总结输出不再是占位预览。
- Modify: `jarvis-ui/src/features/console/MainConsole.tsx`
  - 分离文本发送与语音启动；增加诊断条、状态机和错误恢复。
- Modify: `jarvis-ui/src/features/console/TopStatusBar.tsx`
  - 展示当前 provider/model/voice/session 状态。
- Create: `jarvis-ui/src/features/console/DiagnosticsStrip.tsx`
  - 可折叠诊断条，正常时简洁、异常时展开。
- Create: `jarvis-ui/src/features/config/RuntimeSettingsSummary.tsx`
  - 紧凑摘要行，显示当前 provider/model/voice。
- Modify: `jarvis-ui/src/features/config/RuntimeConfigPanel.tsx`
  - 改为内联展开式设置表单，支持 provider/model/voice/knowledge root。
- Modify: `jarvis-ui/src/features/panels/RightDrawer.tsx`
  - 显示解析后的目标路径和更强风险说明。
- Modify: `jarvis-ui/src/features/workspace/WorkspaceRouter.tsx`
  - 总结区和记录区显示结构化结果与错误。
- Modify: `jarvis-ui/src/types/desktop.d.ts`
  - 同步 preload 暴露接口。
- Modify: `jarvis-ui/src/features/console/MainConsole.test.tsx`
  - 覆盖文本/语音分流、诊断条行为、错误恢复。
- Modify: `jarvis-ui/src/styles/app.css`
  - 增加诊断条、设置摘要、错误状态样式。
- Modify: `README.md`
  - 同步新的默认值、运行时设置和用户配置方式。

## Task 1: 锁住公开仓默认值与运行时配置

**Files:**
- Modify: `jarvis-server/app/models.py`
- Modify: `jarvis-server/app/services/runtime_config_service.py`
- Modify: `jarvis-server/app/routers/assistant.py`
- Modify: `jarvis-server/tests/test_health.py`
- Modify: `jarvis-server/tests/test_assistant_api.py`

- [ ] **Step 1: 写失败测试，锁住默认音色与运行时配置回显**

```python
def test_preference_defaults_match_public_speech_provider() -> None:
    preference = PreferenceState()
    assert preference.voice_name == "longxiaochun"


def test_home_snapshot_reports_active_provider_model_and_voice(client: TestClient) -> None:
    response = client.get("/api/home")
    payload = response.json()
    assert payload["runtime"]["llm_provider"] == "kimi"
    assert payload["runtime"]["llm_model"]
    assert payload["runtime"]["speech_provider"] == "aliyun"
    assert payload["runtime"]["voice_name"] == "longxiaochun"
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest tests\test_health.py -q
python -m pytest tests\test_assistant_api.py -q
```

Expected:
- `PreferenceState.voice_name` 仍是 `zh-CN-XiaoxiaoNeural`
- `/api/home` 还没有统一 `runtime` 摘要字段或值不一致

- [ ] **Step 3: 写最小实现，统一默认值与首页运行时摘要**

```python
# jarvis-server/app/models.py
class PreferenceState(Base):
    __tablename__ = "preference_states"
    # ...
    teacher_style: Mapped[str] = mapped_column(String(64), default="幽默风趣型")
    voice_name: Mapped[str] = mapped_column(String(128), default="longxiaochun")
```

```python
# jarvis-server/app/routers/assistant.py
runtime = get_runtime_summary()
return {
    "tasks": tasks,
    "memories": memories,
    "reminders": reminders,
    "recent_actions": recent_actions,
    "timeline": timeline,
    "preferences": {
        "teacher_style": preference.teacher_style,
        "voice_name": preference.voice_name,
    },
    "runtime": {
        "llm_provider": runtime.llm_provider,
        "llm_model": runtime.llm_model,
        "speech_provider": runtime.speech_provider,
        "voice_name": runtime.voice_name,
        "knowledge_root": runtime.knowledge_root,
        "knowledge_root_exists": runtime.knowledge_root_exists,
    },
}
```

- [ ] **Step 4: 重跑测试确认转绿**

Run:

```powershell
python -m pytest tests\test_health.py tests\test_assistant_api.py -q
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add jarvis-server/app/models.py jarvis-server/app/services/runtime_config_service.py jarvis-server/app/routers/assistant.py jarvis-server/tests/test_health.py jarvis-server/tests/test_assistant_api.py
git commit -m "fix: align public runtime defaults"
```

## Task 2: 修复文件动作越界与审批可信度

**Files:**
- Modify: `jarvis-server/app/services/permission_service.py`
- Modify: `jarvis-server/app/services/action_service.py`
- Create/Modify: `jarvis-server/tests/test_action_service.py`

- [ ] **Step 1: 写失败测试，复现相对路径越界**

```python
def test_write_file_outside_workspace_requires_confirmation(tmp_path) -> None:
    permission = PermissionService()
    target = str((ROOT_DIR / ".." / ".." / ".env").resolve())
    risk, requires_confirmation = permission.classify(
        action_type="write_file",
        target=target,
        resolved_path=Path(target),
    )
    assert risk == "dangerous"
    assert requires_confirmation is True


def test_relative_path_traversal_is_audited_with_resolved_target(db_session) -> None:
    service = ActionService(PermissionService())
    result = service.execute(
        db_session,
        action_type="write_file",
        target="..\\..\\.env",
        content="BAD=1",
        approved=False,
    )
    assert result.status == "confirmation_required"
    assert ".env" in result.detail
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
python -m pytest tests\test_action_service.py -q
```

Expected:
- 现有 `classify()` 不接受 `resolved_path`
- 相对路径越界未触发强确认

- [ ] **Step 3: 写最小实现，统一“先解析路径，再分风险”**

```python
# jarvis-server/app/services/permission_service.py
class PermissionService:
    def classify(
        self,
        action_type: str,
        target: str,
        resolved_path: Path | None = None,
    ) -> tuple[str, bool]:
        dangerous_actions = {"delete_file", "run_command", "open_web_page"}
        cautious_actions = {"fetch_web", "read_file", "write_file"}
        outside_workspace = (
            resolved_path is not None
            and ROOT_DIR != resolved_path
            and ROOT_DIR not in resolved_path.parents
        )
        if action_type in dangerous_actions or outside_workspace:
            return ("dangerous", True)
        if action_type in cautious_actions:
            return ("cautious", True)
        return ("normal", False)
```

```python
# jarvis-server/app/services/action_service.py
resolved_target = (
    (ROOT_DIR / target).resolve()
    if not Path(target).is_absolute()
    else Path(target).resolve()
)
risk_level, requires_confirmation = self.permission_service.classify(
    action_type,
    target,
    resolved_path=resolved_target,
)
detail_target = str(resolved_target)
```

- [ ] **Step 4: 审批卡与审计结果带上真实路径**

```python
return ActionExecutionResult(
    action_type=action_type,
    target=detail_target,
    risk_level=risk_level,
    requires_confirmation=requires_confirmation,
    status="confirmation_required",
    detail=f"Action requires confirmation for {detail_target}.",
)
```

- [ ] **Step 5: 重跑测试确认转绿**

Run:

```powershell
python -m pytest tests\test_action_service.py -q
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add jarvis-server/app/services/permission_service.py jarvis-server/app/services/action_service.py jarvis-server/tests/test_action_service.py
git commit -m "fix: harden action path approvals"
```

## Task 3: 修复 realtime/chat 阻塞、静默断线与音频缓冲无上限

**Files:**
- Modify: `jarvis-server/app/routers/realtime.py`
- Modify: `jarvis-server/app/routers/chat.py`
- Modify: `jarvis-server/app/services/speech_service.py`
- Modify: `jarvis-server/tests/test_realtime_ws.py`
- Modify: `jarvis-server/tests/test_chat_sse.py`

- [ ] **Step 1: 写失败测试，锁住 realtime 错误事件和缓冲上限**

```python
def test_realtime_emits_error_event_when_speech_turn_fails(monkeypatch, client: TestClient) -> None:
    monkeypatch.setattr(
        "app.routers.realtime.run_audio_turn",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("tts failed")),
    )
    with client.websocket_connect("/ws/realtime") as ws:
        ws.send_json({"type": "start"})
        ws.send_json({"type": "audio_chunk", "audio_base64": "AAAA"})
        ws.send_json({"type": "audio_commit", "sample_rate_hz": 16000})
        event = ws.receive_json()
    assert event["type"] == "error"
    assert event["message"] == "tts failed"


def test_realtime_rejects_oversized_audio_buffer(client: TestClient) -> None:
    oversized = "A" * (2 * 1024 * 1024)
    with client.websocket_connect("/ws/realtime") as ws:
        ws.send_json({"type": "start"})
        ws.send_json({"type": "audio_chunk", "audio_base64": oversized})
        event = ws.receive_json()
    assert event["type"] == "error"
    assert "audio buffer" in event["message"]
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
python -m pytest tests\test_realtime_ws.py tests\test_chat_sse.py -q
```

Expected:
- 现有 realtime 不发送 error event
- 现有 audio buffer 无上限

- [ ] **Step 3: 写最小实现，把阻塞工作移出事件循环**

```python
# jarvis-server/app/routers/realtime.py
async def run_audio_turn(speech: SpeechService, audio: bytes, sample_rate_hz: int, teacher_style: str, voice_name: str):
    return await asyncio.to_thread(
        speech.handle_audio_turn,
        audio,
        sample_rate_hz,
        teacher_style,
        voice_name,
    )


async def run_text_turn(speech: SpeechService, text: str, teacher_style: str):
    return await asyncio.to_thread(
        speech.handle_text_turn,
        text,
        teacher_style,
    )
```

```python
# jarvis-server/app/routers/chat.py
reply = await asyncio.to_thread(
    service.prepare_chat,
    query,
    session_id,
)
```

- [ ] **Step 4: realtime 增加错误事件和缓冲上限**

```python
MAX_AUDIO_BUFFER_BYTES = 512 * 1024

if message_type == "audio_chunk":
    chunk = base64.b64decode(audio_base64)
    if len(audio_buffer) + len(chunk) > MAX_AUDIO_BUFFER_BYTES:
        audio_buffer.clear()
        await websocket.send_json({
            "type": "error",
            "message": "audio buffer exceeded limit",
            "recoverable": True,
        })
        continue
    audio_buffer.extend(chunk)
```

```python
except RuntimeError as error:
    await websocket.send_json({
        "type": "error",
        "message": str(error),
        "recoverable": True,
    })
    await websocket.send_json({"type": "voice_state", "state": "error"})
    audio_buffer.clear()
    continue
```

- [ ] **Step 5: 重跑测试确认转绿**

Run:

```powershell
python -m pytest tests\test_realtime_ws.py tests\test_chat_sse.py -q
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add jarvis-server/app/routers/realtime.py jarvis-server/app/routers/chat.py jarvis-server/app/services/speech_service.py jarvis-server/tests/test_realtime_ws.py jarvis-server/tests/test_chat_sse.py
git commit -m "fix: stabilize realtime and chat execution"
```

## Task 4: 用真实总结替换占位实现

**Files:**
- Modify: `jarvis-server/app/services/summary_service.py`
- Modify: `jarvis-server/tests/test_summary_service.py`

- [ ] **Step 1: 写失败测试，禁止继续输出 placeholder bullets**

```python
def test_summary_service_returns_reader_facing_summary(monkeypatch) -> None:
    service = SummaryService(chat_client=FakeChatClient("总结结论", ["重点一", "重点二"]))
    result = service.summarize("workspace", "第一行\\n第二行\\n第三行")
    assert result["summary"] == "总结结论"
    assert result["bullets"] == ["重点一", "重点二"]
    assert "source=workspace" not in result["bullets"]
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
python -m pytest tests\test_summary_service.py -q
```

Expected: 仍返回 `source=...` / `preview=...` 这类占位输出

- [ ] **Step 3: 写最小实现，复用现有 LLM 客户端**

```python
class SummaryService:
    def __init__(self, chat_client: KimiChatClient | None = None) -> None:
        self.chat_client = chat_client or build_summary_chat_client()

    def summarize(self, source_type: str, content: str) -> dict[str, object]:
        prompt = build_summary_prompt(source_type, content)
        response = self.chat_client.complete(
            query=prompt,
            history=[],
            knowledge_context="",
        )
        return parse_summary_response(response)
```

- [ ] **Step 4: 重跑测试确认转绿**

Run:

```powershell
python -m pytest tests\test_summary_service.py -q
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add jarvis-server/app/services/summary_service.py jarvis-server/tests/test_summary_service.py
git commit -m "feat: replace placeholder summaries"
```

## Task 5: 重构主控台交互语义与诊断条

**Files:**
- Create: `jarvis-ui/src/features/console/DiagnosticsStrip.tsx`
- Modify: `jarvis-ui/src/features/console/MainConsole.tsx`
- Modify: `jarvis-ui/src/features/console/TopStatusBar.tsx`
- Modify: `jarvis-ui/src/features/workspace/WorkspaceRouter.tsx`
- Modify: `jarvis-ui/src/features/console/MainConsole.test.tsx`
- Modify: `jarvis-ui/src/styles/app.css`

- [ ] **Step 1: 写失败测试，锁住“文本发送”和“开始语音”分流**

```tsx
it('uses send button for text chat and voice button for realtime capture', async () => {
  render(<MainConsole />);

  await userEvent.type(screen.getByPlaceholderText('向 Jarvis 发送文本指令…'), '总结今天进展');
  await userEvent.click(screen.getByRole('button', { name: '发送' }));

  expect(streamChatMock).toHaveBeenCalledWith(
    '总结今天进展',
    expect.any(Function),
    undefined,
  );
  expect(sendTextMock).not.toHaveBeenCalled();
});

it('shows diagnostics strip when runtime is degraded', async () => {
  loadHealthMock.mockResolvedValue({
    degraded: true,
    dependencies: { database: 'offline', llm: 'missing', speech: 'missing', config: 'ready' },
  });
  render(<MainConsole />);
  expect(await screen.findByText('数据库未连接')).toBeInTheDocument();
});
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run src/features/console/MainConsole.test.tsx
```

Expected:
- 当前按钮语义和诊断条行为与测试不符

- [ ] **Step 3: 写最小实现，分离文本发送与语音启动**

```tsx
async function handleSendText() {
  const trimmedQuery = query.trim();
  if (!trimmedQuery || isStreaming) return;
  setReply('');
  setReplyPhase('thinking');
  await streamChat(trimmedQuery, onStreamEvent, sessionId ?? undefined);
}

async function handleStartVoice() {
  if (!voiceReady) {
    await realtimeClientRef.current.connect();
    setVoiceState('connecting');
  }
  await realtimeClientRef.current.startMicrophoneCapture();
  setReplyPhase('listening');
}
```

- [ ] **Step 4: 加入诊断条与结构化回复状态**

```tsx
<TopStatusBar
  modeLabel={modeLabel}
  providerLabel={`${runtimeSummary.llmProvider} / ${runtimeSummary.llmModel}`}
  voiceLabel={`${runtimeSummary.speechProvider} / ${runtimeSummary.voiceName}`}
  sessionLabel={sessionId ? `会话 ${sessionId}` : '无活跃会话'}
  statusItems={statusItems}
/>
<DiagnosticsStrip
  degraded={Boolean(healthStatus?.degraded)}
  diagnostics={diagnostics}
  onReconnectVoice={() => void handleVoiceConnect()}
  onReloadRuntime={() => void handleReloadRuntimeConfig()}
  onResumeSession={handleResumeSession}
/>
```

- [ ] **Step 5: 重跑测试确认转绿**

Run:

```powershell
npx vitest run src/features/console/MainConsole.test.tsx
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add jarvis-ui/src/features/console/DiagnosticsStrip.tsx jarvis-ui/src/features/console/MainConsole.tsx jarvis-ui/src/features/console/TopStatusBar.tsx jarvis-ui/src/features/workspace/WorkspaceRouter.tsx jarvis-ui/src/features/console/MainConsole.test.tsx jarvis-ui/src/styles/app.css
git commit -m "feat: clarify cockpit interaction flow"
```

## Task 6: 完成用户可配置模型/提供商/音色/知识库路径

**Files:**
- Modify: `jarvis-ui/src/features/config/RuntimeConfigPanel.tsx`
- Create: `jarvis-ui/src/features/config/RuntimeSettingsSummary.tsx`
- Modify: `jarvis-ui/src/features/console/MainConsole.tsx`
- Modify: `jarvis-server/app/services/runtime_config_service.py`
- Modify: `jarvis-server/app/routers/assistant.py`
- Modify: `jarvis-server/tests/test_assistant_api.py`
- Modify: `README.md`

- [ ] **Step 1: 写失败测试，锁住运行时设置表单**

```tsx
it('shows compact runtime summary and expands editable provider controls', async () => {
  render(<MainConsole />);
  expect(await screen.findByText('Kimi / kimi-k2.5 / DashScope / longxiaochun')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: '展开运行时设置' }));
  expect(screen.getByLabelText('LLM 提供商')).toBeInTheDocument();
  expect(screen.getByLabelText('LLM 模型')).toBeInTheDocument();
  expect(screen.getByLabelText('语音提供商')).toBeInTheDocument();
  expect(screen.getByLabelText('知识库路径')).toBeInTheDocument();
});
```

```python
def test_save_runtime_config_persists_provider_model_voice(client: TestClient) -> None:
    response = client.post(
        "/api/runtime-config",
        json={
            "llm": {"provider": "kimi", "model": "kimi-k2.5"},
            "speech": {"provider": "aliyun", "voice_name": "longxiaobai"},
            "knowledge_root": "D:/Knowledge",
        },
    )
    payload = response.json()
    assert payload["llm"]["model"] == "kimi-k2.5"
    assert payload["speech"]["voice_name"] == "longxiaobai"
    assert payload["knowledge_root"] == "D:/Knowledge"
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
npx vitest run src/features/console/MainConsole.test.tsx
Set-Location '..\\jarvis-server'
python -m pytest tests\test_assistant_api.py -q
```

Expected:
- 当前没有紧凑摘要行和完整可编辑字段
- 后端回显字段不全或名称不一致

- [ ] **Step 3: 写最小实现，增加摘要行和可展开设置区**

```tsx
<RuntimeSettingsSummary
  llmProvider={runtimeConfig.llm.provider}
  llmModel={runtimeConfig.llm.model}
  speechProvider={runtimeConfig.speech.provider}
  voiceName={runtimeConfig.speech.voice_name}
  expanded={runtimeExpanded}
  onToggle={() => setRuntimeExpanded((current) => !current)}
/>
```

```tsx
{runtimeExpanded ? (
  <RuntimeConfigPanel
    runtimeConfig={runtimeConfig}
    onSave={handleSaveRuntimeConfig}
    onReload={handleReloadRuntimeConfig}
    onCheck={handleCheckRuntimeConfig}
  />
) : null}
```

- [ ] **Step 4: README 同步新的设置方式**

```md
### 运行时设置

Jarvis 启动后可在主控台直接修改：

- LLM 提供商
- LLM 模型
- 语音提供商
- 音色
- 知识库路径

保存后会立即刷新状态条与诊断条，不需要手动编辑 `.env` 才能切换常用运行时参数。
```

- [ ] **Step 5: 重跑测试确认转绿**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run src/features/console/MainConsole.test.tsx
Set-Location '..\\jarvis-server'
python -m pytest tests\test_assistant_api.py -q
```

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add jarvis-ui/src/features/config/RuntimeConfigPanel.tsx jarvis-ui/src/features/config/RuntimeSettingsSummary.tsx jarvis-ui/src/features/console/MainConsole.tsx jarvis-server/app/services/runtime_config_service.py jarvis-server/app/routers/assistant.py jarvis-server/tests/test_assistant_api.py README.md
git commit -m "feat: add configurable runtime controls"
```

## Task 7: 审批结果面、类型声明与总体验证

**Files:**
- Modify: `jarvis-ui/src/features/panels/RightDrawer.tsx`
- Modify: `jarvis-ui/src/types/desktop.d.ts`
- Modify: `README.md`
- Review: `jarvis-server`
- Review: `jarvis-ui`
- Review: `electron`

- [ ] **Step 1: 写失败测试，锁住审批卡显示解析后目标与风险原因**

```tsx
it('renders resolved action target and risk explanation', () => {
  render(
    <RightDrawer
      pendingConfirmations={[
        {
          action_type: 'write_file',
          risk_level: 'dangerous',
          target: 'C:\\\\Users\\\\Administrator\\\\.env',
          reason: '目标路径超出工作区',
        },
      ]}
      recentActions={[]}
      onApproveAction={() => undefined}
    />,
  );
  expect(screen.getByText('C:\\Users\\Administrator\\.env')).toBeInTheDocument();
  expect(screen.getByText('目标路径超出工作区')).toBeInTheDocument();
});
```

- [ ] **Step 2: 跑测试确认先红**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-ui'
npx vitest run src/features/console/MainConsole.test.tsx
```

Expected: 当前审批卡没有展示风险原因或解析后路径

- [ ] **Step 3: 写最小实现，并补齐 preload 类型**

```ts
// jarvis-ui/src/types/desktop.d.ts
jarvisDesktop?: {
  getShellInfo: () => { app: string; mode: string; resident?: boolean };
  getServerBaseUrl: () => string;
  onHotkeyTriggered?: (callback: () => void) => (() => void) | void;
  setAmbientMode?: (enabled: boolean) => void;
  setClickThrough?: (enabled: boolean) => void;
  setOrbMode?: (enabled: boolean) => void;
  setOrbClickThrough?: (enabled: boolean) => void;
};
```

```tsx
// jarvis-ui/src/features/panels/RightDrawer.tsx
<p>目标：{proposal.target}</p>
<p>原因：{proposal.reason ?? '需要确认后才会执行。'}</p>
```

- [ ] **Step 4: 完整验证**

Run:

```powershell
Set-Location 'C:\Users\Administrator\.copilot\session-state\762875a1-88ea-4923-b3ce-4d2c085eac07\jarvis-public-release\jarvis-server'
python -m pytest -q

Set-Location '..\\jarvis-ui'
npx vitest run
npm run build

Set-Location '..'
npm run test:electron
npm run build:electron
```

Expected:
- backend 全绿
- frontend 测试 + build 全绿
- electron 测试 + build 全绿

- [ ] **Step 5: 提交**

```bash
git add jarvis-ui/src/features/panels/RightDrawer.tsx jarvis-ui/src/types/desktop.d.ts README.md
git commit -m "fix: polish release diagnostics and approvals"
```
